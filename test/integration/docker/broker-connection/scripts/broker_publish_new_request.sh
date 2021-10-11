#! /bin/bash

# abort script if no input argument is given
if [ -z "$1" ]; then
    echo "No tag for request supplied" && exit 1
else
    REQUEST_TAG=$1
fi

# create default broker request with given tag in local folder
echo '<queryRequest xmlns="http://aktin.org/ns/exchange" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><id>1337</id><reference>2020-01-01T00:00:00.000Z</reference><scheduled>2020-01-01T12:00:00.000Z</scheduled><query><title>Title of request</title><description>Description of request</description><principal><name>Name of creator</name><organisation>Organisation of creator</organisation><email>Email of createor</email><phone/><tags><tag>'$REQUEST_TAG'</tag></tags></principal><schedule xsi:type="repeatedExecution"><duration>-P6M</duration><interval/><intervalHours/><id>1</id></schedule><sql xmlns="http://aktin.org/ns/i2b2/sql"><source type="application/sql">SELECT * FROM fhir_observation</source></sql></query></queryRequest>' >> XML

# submit the new broker request
RESPONSE=$(curl -is --request POST -d @XML "http://localhost:8080/broker/request" --header "Authorization: Bearer xxxAdmin1234" --header "Content-Type: application/vnd.aktin.query.request+xml")

# extract from submitting response the newly created id of request
REQUEST_ID=$(echo $RESPONSE | grep -Eo 'broker/request/[0-9]{1,2}' | grep -Eo '[0-9]*')

# publish newly created request to all broker clients
curl -s --request POST "http://localhost:8080/broker/request/$REQUEST_ID/publish" --header "Authorization: Bearer xxxAdmin1234"

# clean up request in local folder
rm -f XML
