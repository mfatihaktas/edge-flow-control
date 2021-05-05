#!/bin/bash
echo $1 $2 $3

DOCKER=docker
IMG_NAME=edge-flow
CONT_NAME=edge-server

if [ $1 = 'b' ]; then
  rm *.png *.log
  $DOCKER build -t $CONT_NAME .
elif [ $1 = 'rsd' ]; then
  $DOCKER run --name $CONT_NAME -d $IMG_NAME
elif [ $1 = 'rs' ]; then
  [ -z "$2" ] && { echo "Which server [0, *] ?"; exit 1; }
  $DOCKER run --name $CONT_NAME $IMG_NAME server.py --i=$2
elif [ $1 = 'stop' ]; then
  $DOCKER stop $CONT_NAME
elif [ $1 = 'kill' ]; then
  $DOCKER kill $CONT_NAME
elif [ $1 = 'bash' ]; then
  $DOCKER exec -it $CONT_NAME bash
else
  echo "Arg did not match!"
fi
