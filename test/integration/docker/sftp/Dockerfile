FROM ubuntu:20.04

WORKDIR /opt

RUN apt-get update && apt-get install -y openssh-server ssh

ADD scripts/* ./
RUN chmod +x *

RUN ./create_sftp_user.sh
RUN ./create_sftp_rki_folder.sh
RUN ./configure_sftp_service.sh

ENTRYPOINT service ssh restart && bash
