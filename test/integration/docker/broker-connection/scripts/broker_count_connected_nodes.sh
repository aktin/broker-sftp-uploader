#! /bin/bash

# get xml with all connected client nodes
RESPONSE=$(curl -s --request GET "http://localhost:8080/broker/node" --header "Authorization: Bearer xxxAdmin1234")

# each two tags named "id" in response stand for one connected node (open and close tag)
expr $(echo $RESPONSE | grep -o "id" | wc -l) / 2
