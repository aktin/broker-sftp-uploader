#! /bin/bash

# abort script if no input arguments are given
if [ -z "$1" ]; then
    echo "No api key supplied" && exit 1
else
    API_KEY=$1
fi

if [ -z "$2" ]; then
    echo "No request number supplied" && exit 1
else
    REQUEST_NUMBER=$2
fi

# set request status on given request for this api key on "retrieved"
curl -s --request POST "http://localhost:8080/broker/my/request/$REQUEST_NUMBER/status/retrieved" --header "Authorization: Bearer $API_KEY"
