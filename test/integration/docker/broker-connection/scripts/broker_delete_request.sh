#! /bin/bash

# abort script if no input argument is given
if [ -z "$1" ]; then
    echo "No request id supplied" && exit 1
else
    REQUEST_ID=$1
fi

# delete request of given id from broker
curl -s --request DELETE "http://localhost:8080/broker/request/$REQUEST_ID" --header "Authorization: Bearer xxxAdmin1234"
