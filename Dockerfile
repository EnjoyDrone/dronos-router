FROM debian:11 as builder

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

# Build and install mavlink router
RUN git clone https://github.com/mavlink-router/mavlink-router.git && cd mavlink-router \
    && git checkout 0e05bff9a906914b1c0b94d1169a4269a2629737 \
    && git submodule update --init --recursive \
    && meson setup build . \
    && ninja -C build && ninja -C build install

#----------------------------------------------

FROM debian:11 as runtime

# Copy mavlink router software built in previous stage to avoid all the build dependencies
COPY --from=builder /usr/bin/mavlink-routerd \
                    /usr/bin/mavlink-routerd
COPY --from=builder /lib/systemd/system/mavlink-router.service \
                    /lib/systemd/system/mavlink-router.service

# Copy main.conf which give all the parameters for mavlink router (log, connection, url, etc)
COPY main.conf /etc/mavlink-router/main.conf

COPY entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh

# Run the mavlink-routerd
ENTRYPOINT ["/root/entrypoint.sh"]