#!/bin/bash

function show_help {
    echo ""
    echo "Usage: ${0} [-h | CONNECTION_URL | BAUDRATE]"
    echo ""
    echo "CONNECTION_URL format should be :"
    echo " serial: DEVICE:BAUD"
    echo " udp: IP:PORT"
    echo " tcp: tcp:IP:PORT"
    echo "For example /dev/ttyACM0:1500000 or 0.0.0.0:14550";
    echo ""
    echo "By default, the connection is 0.0.0.0:14550."
}

OPTIND=1 # Reset in case getopts has been used previously in the shell.

while getopts "h?" opt; do
    case "$opt" in
    h|\?)
        show_help
        exit 0
        ;;
    esac
done

shift $((OPTIND-1))

if [ "$#" -eq 0 ]; then
    CONNECTION_URL="0.0.0.0:14550"
elif [ "$#" -eq 1 ]; then
    CONNECTION_URL="$1"
elif [ "$#" -eq 2 ]; then
    CONNECTION_URL="$1"
    BAUDRATE="$2"
elif [ "$#" -gt 2 ]; then
    show_help
    exit 1;
fi

echo "mavlink url is ${CONNECTION_URL}"

mavlink-routerd ${CONNECTION_URL}