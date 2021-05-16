#!/bin/bash
echo $1 $2 $3

DOCKER=docker
NAME=mn # $2

if [ $1 = 'xterm' ]; then
  nohup socat TCP-LISTEN:6000,reuseaddr,fork UNIX-CLIENT:\"$DISPLAY\" &
  # lsof -i TCP:6000
elif [ $1 = 'rd' ]; then
  # $DOCKER run -it --name $NAME ubuntu:xenial bash
  # $DOCKER run -it --name $NAME bash
  $DOCKER run --name $NAME -d -it --rm --privileged --net=host \
              -e DISPLAY=docker.for.mac.host.internal:0 \
              -v /tmp/.X11-unix:/tmp/.X11-unix \
              -v /lib/modules:/lib/modules \
              -v ~/Desktop/edge-flow-control:/root/edge-flow-control \
              mininet
elif [ $1 = 'r' ]; then
  $DOCKER run --name $NAME -it --rm --privileged --net=host \
              -e DISPLAY=docker.for.mac.host.internal:0 \
              -v /tmp/.X11-unix:/tmp/.X11-unix \
              -v /lib/modules:/lib/modules \
              -v ~/Desktop/edge-flow-control:/root/edge-flow-control \
              mininet bash
elif [ $1  = 'start' ]; then
  $DOCKER start $NAME
elif [ $1 = 'stop' ]; then
  $DOCKER stop $NAME
elif [ $1 = 'kill' ]; then
  $DOCKER kill $NAME
elif [ $1 = 'bash' ]; then
  $DOCKER exec -it $NAME bash
elif [ $1 = 'inspect' ]; then
  $DOCKER inspect $NAME
elif [ $1 = 'lsc' ]; then
  $DOCKER ps --all
elif [ $1  = 'commit' ]; then
  # $3 : NEW_NAME
    $DOCKER commit $NAME $3
elif [ $1  = 'save' ]; then
  $DOCKER save $NAME -o ~/Desktop/$NAME.tar
elif [ $1 = 'lsi' ]; then
  $DOCKER images
elif [ $1 = 'commit' ]; then
  NEW_NAME=$3
  $DOCKER commit $NAME $NEW_NAME
elif [ $1  = 'tag' ]; then
  NEW_NAME=$3
  $DOCKER tag $NAME $NEW_NAME
elif [ $1  = 'rm' ]; then
  $DOCKER rm $NAME
elif [ $1 = 'rmi' ]; then
  $DOCKER image rm $NAME
elif [ $1 = 'pull' ]; then
  $DOCKER pull $NAME
else
  echo "Argument did not match !"
fi
