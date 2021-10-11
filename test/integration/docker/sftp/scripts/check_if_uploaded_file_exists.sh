#! /bin/bash

# abort script if no input argument is given
if [ -z "$1" ]; then
    echo "No filename provided" && exit 1
else
    FILENAME=$1
fi

# check, if file uploaded by python script exists
[ -f /var/sftp/rki/$FILENAME ] && echo 1 || echo 0
