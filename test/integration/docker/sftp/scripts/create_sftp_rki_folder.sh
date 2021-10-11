#! /bin/bash

if [[ $EUID -ne 0 ]]; then
  echo "script must be run as root" && exit 1
fi

# user sftp must exist
id -u sftpuser >/dev/null

# group sftp must exist
[ -z $(getent group sftp) ] && echo "group sftp does not exist" && exit 1

# create sftp upload folder and set permissions
mkdir -p /var/sftp/rki
chown root:root /var/sftp
chmod 755 /var/sftp
chown sftpuser:sftp /var/sftp/rki
