#!/bin/bash
echo $1 $2 $3

KUBECTL=kubectl

IMG_NAME=edge-flow
CONT_NAME=edge-app
NET_NAME=edge-net

if [ $1 = 'b' ]; then
  $DOCKER image rm $IMG_NAME
  rm *.png *.log
  $DOCKER build -t $IMG_NAME .
elif [ $1 = 'ri' ]; then
  echo
else
  echo "Arg did not match!"
fi
