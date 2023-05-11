FROM ubuntu:20.04

WORKDIR /opt

RUN apt-get update && apt-get install -y build-essential curl

ADD scripts/* ./
RUN chmod +x *
