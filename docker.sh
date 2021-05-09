#!/bin/bash
echo $1 $2 $3

DOCKER=docker
IMG_NAME=edge-flow
CONT_NAME=edge-app
NET_NAME=edge-net

if [ $1 = 'b' ]; then
  $DOCKER image rm $IMG_NAME
  rm *.png *.log
  $DOCKER build -t $IMG_NAME .
elif [ $1 = 'ri' ]; then
  $DOCKER run --name $CONT_NAME -it --rm -d $IMG_NAME /bin/bash
elif [ $1 = 'rsd' ]; then
  [ -z "$2" ] && { echo "Which server [0, *] ?"; exit 1; }
  # $DOCKER run --name $CONT_NAME -it --rm $IMG_NAME ping localhost # Test that should work
  $DOCKER run --name $CONT_NAME -d -it --rm $IMG_NAME python3 -u /home/app/server.py --i=$2
elif [ $1 = 'rs' ]; then
  [ -z "$2" ] && { echo "Which server [0, *] ?"; exit 1; }
  # --net $NET_NAME --ip 192.168.1.0
  # -p 5000:5000/tcp -p 5000:5000/udp \
  $DOCKER run --name es -it --rm \
          --net bridge \
          $IMG_NAME python3 -u /home/app/server.py --i=$2
elif [ $1 = 'rc' ]; then
  [ -z "$2" ] && { echo "Which client [0, *] ?"; exit 1; }
  # -p 5000:5000/tcp -p 5000:5000/udp \
  $DOCKER run --name ec -it --rm \
          --net bridge \
          $IMG_NAME python3 -u /home/app/client.py --i=$2 --sid_ip_m='{"s0": "172.17.0.2"}'
elif [ $1 = 'stop' ]; then
  $DOCKER stop $CONT_NAME
elif [ $1 = 'kill' ]; then
  $DOCKER kill $CONT_NAME
elif [ $1 = 'bash' ]; then
  $DOCKER exec -it $CONT_NAME bash
elif [ $1 = 'lsc' ]; then
  $DOCKER ps --all
elif [ $1 = 'lsi' ]; then
  $DOCKER images
elif [ $1  = 't' ]; then
  $DOCKER tag $IMG_NAME mfatihaktas/$IMG_NAME:trial
elif [ $1  = 'rm' ]; then
  $DOCKER rm $2
elif [ $1 = 'rmi' ]; then
  $DOCKER image rm $2
elif [ $1 = 'pull' ]; then
  $DOCKER pull $2
elif [ $1 = 'cn' ]; then
  $DOCKER network create --subnet=192.168.0.0/16 $NET_NAME
elif [ $1 = 'rn' ]; then
  $DOCKER network rm $NET_NAME
elif [ $1 = 'lsn' ]; then
  $DOCKER network ls
else
  echo "Arg did not match!"
fi
