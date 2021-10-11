#! /bin/bash

# check existance of sftp upload folder
[ ! -d /var/sftp/rki ] && echo "directory /var/sftp/rki does not exist" && exit 1

# count uploaded zip files by python script
ls /var/sftp/rki | grep -c zip
