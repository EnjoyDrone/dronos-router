-----------------------
 DroneOS-router
-----------------------

Stream MAVLINK data of the connected FCU using [mavlink router](https://github.com/mavlink-router/mavlink-router). Used to stream the data 
to a ulog file. Could also be used to forward the stream to external component

### Working with docker container

Build the docker image with:
```
docker build . -t dronos_router
```

You can then run the docker container with:
```
docker run --mount type=bind,source=~/drone,target=/root/drone -ti dronos_router
```

By deflaut, the connection is done on ``0.0.0.0:14550``. On a Raspberry Pi, if the FCU is connected with USB you can use this command instead:
```
docker run --device /dev/ttyACM0:/dev/ttyACM0 --mount type=bind,source=$HOME/drone,target=/root/drone -ti dronos_router /dev/ttyACM0:921600
```

You can also work with ``docker-compose`` to automatically have the good parameters. On a computer, this is done with the command:
```
docker-compose up
```

On a Raspberry, if the FCU is connected through USB:
```
docker-compose -f docker-compose.yml -f docker-compose.usb.yml up
```
