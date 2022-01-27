FROM debian:11 as builder

ENV DEBIAN_FRONTEND=noninteractive

ENV WORKSPACE_DIR /root
ENV FIRMWARE_DIR ${WORKSPACE_DIR}/AerOS-gpio
ENV HOME ${WORKSPACE_DIR}

# Install dependencies
RUN apt-get update \
    && apt-get -y --quiet --no-install-recommends install \
        gcc \
        python3.9 \
        python3-dev \
        python3-pip \
        python3-lxml \
    && apt-get -y autoremove \
    && apt-get clean autoclean \
    && rm -rf /var/lib/apt/lists/{apt,dpkg,cache,log} /tmp/* /var/tmp/*

RUN pip install pymavlink

WORKDIR ${FIRMWARE_DIR}
COPY . ${FIRMWARE_DIR}

# Run the stream script
CMD ["python3","./ulog_stream.py"]