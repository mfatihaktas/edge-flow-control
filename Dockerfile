# syntax=docker/dockerfile:1
FROM python:3
WORKDIR /home/app

RUN apt-get update
RUN apt-get install net-tools

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# CMD [ "python3", "-u", "server.py", "--i=0" ]