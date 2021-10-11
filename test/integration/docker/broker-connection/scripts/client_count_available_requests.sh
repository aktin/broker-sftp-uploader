#! /bin/bash

# abort script if no input argument is given
if [ -z "$1" ]; then
    echo "No api key supplied" && exit 1
else
    API_KEY=$1
fi

# get xml with all published requests for this api key
RESPONSE=$(curl -s --request GET "http://localhost:8080/broker/my/request" --header "Authorization: Bearer $API_KEY")

# each tag named "id" in response stands for one request
expr $(echo $RESPONSE | grep -o "id" | wc -l)
