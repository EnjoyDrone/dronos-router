FROM debian:11 as builder

ENV DEBIAN_FRONTEND=noninteractive

ENV WORKSPACE_DIR /root
ENV FIRMWARE_DIR ${WORKSPACE_DIR}/mavlink-router

# Install dependencies
RUN apt-get update \
    && apt-get -y --quiet --no-install-recommends install \
        git \
        ca-certificates \
        meson \
        ninja-build \
        pkg-config \
        gcc \
        g++ \
        systemd \
    && apt-get -y autoremove \
    && apt-get clean autoclean \
    && rm -rf /var/lib/apt/lists/{apt,dpkg,cache,log} /tmp/* /var/tmp/*

# # Build and install mavlink router
RUN cd ${WORKSPACE_DIR} && git clone https://github.com/mavlink-router/mavlink-router.git \
    && cd ${FIRMWARE_DIR} \
    && git checkout 0e05bff9a906914b1c0b94d1169a4269a2629737 \
    && git submodule update --init --recursive \
    && meson setup build . \
    && ninja -C build && ninja -C build install

COPY main.conf /etc/mavlink-router/main.conf

CMD mavlink-routerd

COPY entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh

# Run the mavlink-routerd
ENTRYPOINT ["/root/entrypoint.sh"]