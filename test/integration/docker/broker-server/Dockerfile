FROM ghcr.io/aktin/aktin-broker:latest

USER root

RUN apt-get update && apt-get install -y curl

ENV AKTIN_ADMIN_PW=changeme
ENV AKTIN_BROKER_PORT=127.0.0.1:8080
