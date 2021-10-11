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

# submit a dummy file content as a result for given api key
curl -s --header "Authorization: Bearer $API_KEY" --header "Content-Type: text/csv" --request PUT -d "a;b\n1;2\n3;4\n" "http://localhost:8080/aggregator/my/request/$REQUEST_NUMBER/result"

# update status of given request of client to completed
curl -s --header "Authorization: Bearer $API_KEY" --request POST "http://localhost:8080/broker/my/request/$REQUEST_NUMBER/status/completed"
