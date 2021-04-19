#!/bin/bash
echo $1 $2 $3

PY=python3

if [ $1 = 'n' ]; then
  $PY net.py
elif [ $1 = 'c' ]; then
  [ -z "$2" ] && { echo "Which client [0, *] ?"; exit 1; }
  $PY client.py --i=$2
elif [ $1 = 's' ]; then
  [ -z "$2" ] && { echo "Which server [0, *] ?"; exit 1; }
  $PY server.py --i=$2
elif [ $1 = 'r' ]; then
  $PY rvs.py
else
  echo "Arg did not match!"
fi
