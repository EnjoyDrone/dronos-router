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

RUN pip install pymavlink pyserial

COPY . ${FIRMWARE_DIR}

COPY entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh

# Run the stream script
ENTRYPOINT ["/root/entrypoint.sh"]