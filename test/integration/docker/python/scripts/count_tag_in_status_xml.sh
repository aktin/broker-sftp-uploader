#! /bin/bash

# abort script if no input argument is given
if [ -z "$1" ]; then
    echo "No tag provided" && exit 1
else
    TAG=$1
fi

# check existance of status.xml
[ ! -f status.xml ] && echo "file status.xml does not exist" && exit 1

# each two tags in status.xml stand for one entry (open and close tag)
expr $(cat status.xml | grep -o $TAG | wc -l) / 2
