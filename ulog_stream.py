#!/usr/bin/env python3

"""
Stream ULog data over MAVLink.

@author: Beat Kueng (beat-kueng@gmx.net)

@maintainer: Quentin Collet --> Modified for auto stream for Aero41
"""

#AerOS
from time import sleep
import common as cmn
from pathlib import Path

logger = cmn.setup_logging(Path(__file__).stem)

# PX4 related
import sys, os
import datetime
from timeit import default_timer as timer
os.environ['MAVLINK20'] = '1' # The commands require mavlink 2

try:
    from pymavlink import mavutil
except ImportError as e:
    print("Failed to import pymavlink: " + str(e))
    print("")
    print("You may need to install it with:")
    print("    pip3 install --user pymavlink")
    print("")
    sys.exit(1)


class MavlinkLogStreaming():
    '''Streams log data via MAVLink.
       Assumptions:
       - the sender only sends one acked message at a time
       - the data is in the ULog format '''
    def __init__(self, portname, baudrate, debug=0):
        self.baudrate = 0
        self._debug = debug
        self.buf = ''
        self.debug("Connecting with MAVLink to %s ..." % portname)
        self.mav = mavutil.mavlink_connection(portname, autoreconnect=True, baud=baudrate)
        self.mav.wait_heartbeat()
        self.debug("HEARTBEAT OK\n")
        self.debug("Locked serial device\n")

        self.got_ulog_header = False
        self.got_header_section = False
        self.ulog_message = []
        self.start_time = timer()
        self.last_sequence = -1
        self.logging_started = False
        self.num_dropouts = 0
        self.target_component = 1

    def open_logfile(self, s):
        '''Open a file where to save the log'''
        self.file = open(s,'wb')

    def close_logfile(self):
        '''Close the file where the log is saved'''
        self.file.close()

    def debug(self, s, level=1):
        '''write some debug text'''
        if self._debug >= level:
            print(s)

    def start_log(self):
        self.mav.mav.command_long_send(self.mav.target_system,
                self.target_component,
                mavutil.mavlink.MAV_CMD_LOGGING_START, 0,
                0, 0, 0, 0, 0, 0, 0)
        self.start_time = timer()

    def stop_log(self):
        self.mav.mav.command_long_send(self.mav.target_system,
                self.target_component,
                mavutil.mavlink.MAV_CMD_LOGGING_STOP, 0,
                0, 0, 0, 0, 0, 0, 0)
    
    def send_hearbeat(self):
        self.debug('sending heartbeat')
        self.mav.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,
                mavutil.mavlink.MAV_AUTOPILOT_GENERIC, 0, 0, 0)

    def read_messages(self):
        ''' main loop reading messages '''
        measure_time_start = timer()
        measured_data = 0

        next_heartbeat_time = timer()
        while True:

            # handle heartbeat sending
            heartbeat_time = timer()
            if heartbeat_time > next_heartbeat_time:
                self.debug('sending heartbeat')
                self.mav.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,
                        mavutil.mavlink.MAV_AUTOPILOT_GENERIC, 0, 0, 0)
                next_heartbeat_time = heartbeat_time + 1

            m, first_msg_start, num_drops = self.read_message()
            if m is not None:
                self.process_streamed_ulog_data(m, first_msg_start, num_drops)

                # status output
                if self.logging_started:
                    measured_data += len(m)
                    measure_time_cur = timer()
                    dt = measure_time_cur - measure_time_start
                    if dt > 1:
                        sys.stdout.write('\rData Rate: {:0.1f} KB/s  Drops: {:} \033[K'.format(
                            measured_data / dt / 1024, self.num_dropouts))
                        sys.stdout.flush()
                        measure_time_start = measure_time_cur
                        measured_data = 0

            if not self.logging_started and timer()-self.start_time > 4:
                raise Exception('Start timed out. Is the logger running in MAVLink mode?')


    def read_message(self):
        ''' read a single mavlink message, handle ACK & return a tuple of (data, first
        message start, num dropouts) '''
        m = self.mav.recv_match(type=['LOGGING_DATA_ACKED',
                            'LOGGING_DATA', 'COMMAND_ACK'], blocking=True,
                            timeout=0.05)
        if m is not None:
            self.debug(m, 3)

            if m.get_type() == 'COMMAND_ACK':
                if m.command == mavutil.mavlink.MAV_CMD_LOGGING_START and \
                        not self.got_header_section:
                    if m.result == 0:
                        self.logging_started = True
                        print('Logging started. Waiting for Header...')
                    else:
                        raise Exception('Logging start failed', m.result)
                return None, 0, 0

            # m is either 'LOGGING_DATA_ACKED' or 'LOGGING_DATA':
            is_newer, num_drops = self.check_sequence(m.sequence)

            # return an ack, even we already sent it for the same sequence,
            # because the ack could have been dropped
            if m.get_type() == 'LOGGING_DATA_ACKED':
                self.mav.mav.logging_ack_send(self.mav.target_system,
                        self.target_component, m.sequence)

            if is_newer:
                if num_drops > 0:
                    self.num_dropouts += num_drops

                if m.get_type() == 'LOGGING_DATA':
                    if not self.got_header_section:
                        print('Header received in {:0.2f}s'.format(timer()-self.start_time))
                        self.logging_started = True
                        self.got_header_section = True
                self.last_sequence = m.sequence
                return m.data[:m.length], m.first_message_offset, num_drops

            else:
                self.debug('dup/reordered message '+str(m.sequence))

        return None, 0, 0


    def check_sequence(self, seq):
        ''' check if a sequence is newer than the previously received one & if
        there were dropped messages between the last and this '''
        if self.last_sequence == -1:
            return True, 0
        if seq == self.last_sequence: # duplicate
            return False, 0
        if seq > self.last_sequence:
            # account for wrap-arounds, sequence is 2 bytes
            if seq - self.last_sequence > (1<<15): # assume reordered
                return False, 0
            return True, seq - self.last_sequence - 1
        else:
            if self.last_sequence - seq > (1<<15):
                return True, (1<<16) - self.last_sequence - 1 + seq
            return False, 0


    def process_streamed_ulog_data(self, data, first_msg_start, num_drops):
        ''' write streamed data to a file '''
        if not self.got_ulog_header: # the first 16 bytes need special treatment
            if len(data) < 16: # that's never the case anyway
                raise Exception('first received message too short')
            self.file.write(bytearray(data[0:16]))
            data = data[16:]
            self.got_ulog_header = True

        if self.got_header_section and num_drops > 0:
            if num_drops > 25: num_drops = 25
            # write a dropout message. We don't really know the actual duration,
            # so just use the number of drops * 10 ms
            self.file.write(bytearray([ 2, 0, 79, num_drops*10, 0 ]))

        if num_drops > 0:
            self.write_ulog_messages(self.ulog_message)
            self.ulog_message = []
            if first_msg_start == 255:
                return # no useful information in this message: drop it
            data = data[first_msg_start:]
            first_msg_start = 0

        if first_msg_start == 255 and len(self.ulog_message) > 0:
            self.ulog_message.extend(data)
            return

        if len(self.ulog_message) > 0:
            self.file.write(bytearray(self.ulog_message + data[:first_msg_start]))
            self.ulog_message = []

        data = self.write_ulog_messages(data[first_msg_start:])
        self.ulog_message = data # store the rest for the next message


    def write_ulog_messages(self, data):
        ''' write ulog data w/o integrity checking, assuming data starts with a
        valid ulog message. returns the remaining data at the end. '''
        while len(data) > 2:
            message_length = data[0] + data[1] * 256 + 3 # 3=ULog msg header
            if message_length > len(data):
                break
            self.file.write(bytearray(data[:message_length]))
            data = data[message_length:]
        return data

if __name__ == '__main__':

    """
    Start of the script when executed directly (or via watch_aero.py).
    """
    try:
        logger.info("Log streaming initialization.")

        # Creates the directory structure if not already existing.
        os.makedirs(cmn.log_px4_path, exist_ok=True)

        port = "0.0.0.0:14540"
        baudrate = 921600
        is_armed = False

        logger.info(f"Listening PX4 on port {port}, baudrate {baudrate}")
        print("Connecting to MAVLINK...")
        mav_log_streaming = MavlinkLogStreaming(port, baudrate)
        print("Connected")

        # log streaming watcher
        measure_time_start = timer()
        measured_data = 0

        next_heartbeat_time = timer()


        # Main loop
        while True:

            if is_armed:
                
                # handle heartbeat sending
                heartbeat_time = timer()
                if heartbeat_time > next_heartbeat_time:
                    mav_log_streaming.send_hearbeat()
                    next_heartbeat_time = heartbeat_time + 1

                m, first_msg_start, num_drops = mav_log_streaming.read_message()
                if m is not None:
                    mav_log_streaming.process_streamed_ulog_data(m, first_msg_start, num_drops)

                    # status output
                    if mav_log_streaming.logging_started:
                        measured_data += len(m)
                        measure_time_cur = timer()
                        dt = measure_time_cur - measure_time_start
                        if dt > 1:
                            sys.stdout.write('\rData Rate: {:0.1f} KB/s  Drops: {:} \033[K'.format(
                                measured_data / dt / 1024, mav_log_streaming.num_dropouts))
                            sys.stdout.flush()
                            measure_time_start = measure_time_cur
                            measured_data = 0

                if not mav_log_streaming.logging_started and timer()-mav_log_streaming.start_time > 4:
                    mav_log_streaming.stop_log()
                    print('Start failed. FCU might not be connected anymore')

                # stop stream logging when disarmed
                if not mav_log_streaming.mav.motors_armed():
                    is_armed = False
                    print('Stopp logging')
                    mav_log_streaming.stop_log()
                    mav_log_streaming.close_logfile()

            else:

                # slow loop when drone is disarmed
                sleep(0.5)

                # mandatory to wait hearbeat before to ask for arm state
                mav_log_streaming.mav.wait_heartbeat()
                if mav_log_streaming.mav.motors_armed():

                    is_armed = True

                    # create new log file with current time
                    filename = datetime.datetime.now().strftime("log_%Y-%m-%d-%H-%M-%S.ulg")
                    filename = os.path.join(cmn.log_px4_path, filename)
                    print('Output file name: {:}'.format(filename))

                    mav_log_streaming = MavlinkLogStreaming(port, baudrate)
                    mav_log_streaming.open_logfile(filename)

                    print('Start logging...')
                    mav_log_streaming.start_log()

                    measure_time_start = timer()
                    measured_data = 0

                    next_heartbeat_time = timer()

    except  KeyboardInterrupt:  # Ctrl+C
        logger.warning("Program ended by keyboard.")

    except Exception as error:
        print("ERROR: {}".format(error))

    finally:
        logger.info("End of program.")

        if is_armed:
            print('Stopping log')
            mav_log_streaming.stop_log()
            mav_log_streaming.close_logfile()
