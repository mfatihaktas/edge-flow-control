#!/bin/bash
echo $1 $2 $3

PY=python3

if [ $1 = 's' ]; then
  $PY sim.py
elif [ $1 = 'r' ]; then
  $PY rvs.py
elif [ $1 = 'e' ]; then
  $PY eval_rr_sching.py
else
  echo "Arg did not match!"
fi
