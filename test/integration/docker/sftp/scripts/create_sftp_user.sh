#! /bin/bash

if [[ $EUID -ne 0 ]]; then
  echo "script must be run as root" && exit 1
fi

# create user for sftp service
addgroup sftp
useradd -m sftpuser -g sftp
echo "sftpuser:sftppassword" | chpasswd
