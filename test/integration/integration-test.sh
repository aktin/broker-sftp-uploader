#! /bin/bash

set -euo pipefail

readonly WHI='\033[0m'
readonly RED='\e[1;31m'
readonly ORA='\e[0;33m'
readonly YEL='\e[1;33m'
readonly GRE='\e[0;32m'

readonly API_KEY_1="xxxApiKey123"
readonly API_KEY_2="xxxApiKey567"

readonly PROJECT_NAME="broker-sftp-interface"
current_dir=$(pwd)
readonly PROJECT_DIR=${current_dir%$PROJECT_NAME*}$PROJECT_NAME

echo -e "${YEL} Build the docker-compose stack ${WHI}"
docker-compose -f docker/docker-compose.yml up -d --force-recreate --build

echo -e "${YEL} Copy python scripts from repository to python container and run unittest ${WHI}"
docker cp $PROJECT_DIR/src/sftp_export.py python:/opt/
docker cp $PROJECT_DIR/src/my_error_notifier.py python:/opt/
docker exec python pytest test_xml_manager.py

echo -e "${YEL} Broker creates 3 requests with tag default and 3 with tag rki ${WHI}"
for i in {0..2}; do
  docker exec broker-connection ./broker_publish_new_request.sh rki
  docker exec broker-connection ./broker_publish_new_request.sh default
done

echo -e "${YEL} Client 1 checks number of available requests (must be 6) ${WHI}"
NUMBER_REQUESTS=$(docker exec broker-connection ./client_count_available_requests.sh $API_KEY_1)
if [[ ! $NUMBER_REQUESTS == "6" ]]; then
  echo -e "${RED} invalid number of requests found ($NUMBER_REQUESTS)${WHI}"
fi

echo -e "${YEL} Broker checks number of connected nodes (must be 1) ${WHI}"
NUMBER_NODES=$(docker exec broker-connection ./broker_count_connected_nodes.sh)
if [[ ! $NUMBER_NODES == "1" ]]; then
  echo -e "${RED} invalid number of nodes found ($NUMBER_NODES)${WHI}"
fi

echo -e "${YEL} Client 1 accepts all requests and submit result ${WHI}"
for i in {0..5}; do
  docker exec broker-connection ./client_submit_results.sh $API_KEY_1 $i
done

echo -e "${YEL} Execute the sftp python script ${WHI}"
docker exec python python sftp_export.py /opt/settings.toml

echo -e "${YEL} Container python must have 3 entries in his status.xml ${WHI}"
NUMBER_ENTRIES=$(docker exec python ./count_tag_in_status_xml.sh request-status)
if [[ ! $NUMBER_ENTRIES == "3" ]]; then
  echo -e "${RED} invalid number of entries in status.xml found ($NUMBER_ENTRIES)${WHI}"
fi

echo -e "${YEL} Container sftp must have 3 uploaded files ${WHI}"
NUMBER_FILES=$(docker exec sftp ./count_uploaded_zip_files.sh)
if [[ ! $NUMBER_FILES == "3" ]]; then
  echo -e "${RED} invalid number of files found ($NUMBER_FILES)${WHI}"
fi

echo -e "${YEL} Container sftp must have 3 entries in his status.xml ${WHI}"
NUMBER_ENTRIES=$(docker exec sftp ./count_tag_in_status_xml.sh request-status)
if [[ ! $NUMBER_ENTRIES == "3" ]]; then
  echo -e "${RED} invalid number of entries in status.xml found ($NUMBER_ENTRIES)${WHI}"
fi

echo -e "${YEL} Broker creates one additional default and one additional rki request ${WHI}"
docker exec broker-connection ./broker_publish_new_request.sh rki
docker exec broker-connection ./broker_publish_new_request.sh default

echo -e "${YEL} Broker deletes very first request ${WHI}"
docker exec broker-connection ./broker_delete_request.sh 0

echo -e "${YEL} Client 2 checks number of available requests (must be 7) ${WHI}"
NUMBER_REQUESTS=$(docker exec broker-connection ./client_count_available_requests.sh $API_KEY_2)
if [[ ! $NUMBER_REQUESTS == "7" ]]; then
  echo -e "${RED} invalid number of requests found ($NUMBER_REQUESTS)${WHI}"
fi

echo -e "${YEL} Client 2 retrieves all requests ${WHI}"
for i in {1..5}; do
  docker exec broker-connection ./client_change_request_to_retrieved.sh $API_KEY_2 $i
done

echo -e "${YEL} Broker checks number of connected nodes (must be 2) ${WHI}"
NUMBER_NODES=$(docker exec broker-connection ./broker_count_connected_nodes.sh)
if [[ ! $NUMBER_NODES == "2" ]]; then
  echo -e "${RED} invalid number of nodes found ($NUMBER_NODES)${WHI}"
fi

echo -e "${YEL} Execute the sftp python script again ${WHI}"
docker exec python python sftp_export.py /opt/settings.toml

echo -e "${YEL} Container python must have 4 entries in his status.xml ${WHI}"
NUMBER_ENTRIES=$(docker exec python ./count_tag_in_status_xml.sh request-status)
if [[ ! $NUMBER_ENTRIES == "4" ]]; then
  echo -e "${RED} invalid number of entries in status.xml found ($NUMBER_ENTRIES)${WHI}"
fi

echo -e "${YEL} Container python must have 2 updated entries in his status.xml ${WHI}"
NUMBER_ENTRIES=$(docker exec python ./count_tag_in_status_xml.sh last-update)
if [[ ! $NUMBER_ENTRIES == "2" ]]; then
  echo -e "${RED} invalid number of entries in status.xml found ($NUMBER_ENTRIES)${WHI}"
fi

echo -e "${YEL} Container python must have 1 deleted entries in his status.xml ${WHI}"
NUMBER_ENTRIES=$(docker exec python ./count_tag_in_status_xml.sh deleted)
if [[ ! $NUMBER_ENTRIES == "1" ]]; then
  echo -e "${RED} invalid number of entries in status.xml found ($NUMBER_ENTRIES)${WHI}"
fi

echo -e "${YEL} Container sftp must have 4 entries in his status.xml ${WHI}"
NUMBER_ENTRIES=$(docker exec sftp ./count_tag_in_status_xml.sh request-status)
if [[ ! $NUMBER_ENTRIES == "4" ]]; then
  echo -e "${RED} invalid number of entries in status.xml found ($NUMBER_ENTRIES)${WHI}"
fi

echo -e "${YEL} Container sftp must have 3 uploaded files ${WHI}"
NUMBER_FILES=$(docker exec sftp ./count_uploaded_zip_files.sh)
if [[ ! $NUMBER_FILES == "3" ]]; then
  echo -e "${RED} invalid number of files found ($NUMBER_FILES)${WHI}"
fi

echo -e "${YEL} Container sftp must not have a file name export_0.zip ${WHI}"
FILE_EXISTS=$(docker exec sftp ./check_if_uploaded_file_exists.sh export_0.zip)
if [[ ! $FILE_EXISTS == "0" ]]; then
  echo -e "${RED} export_0.zip found on sftp ${WHI}"
fi

echo -e "${YEL} Container sftp must have a file name export_2.zip ${WHI}"
FILE_EXISTS=$(docker exec sftp ./check_if_uploaded_file_exists.sh export_2.zip)
if [[ ! $FILE_EXISTS == "1" ]]; then
  echo -e "${RED} export_2.zip not found on sftp ${WHI}"
fi

echo -e "${YEL} Copy export_2.zip from container sftp to container python ${WHI}"
docker cp sftp:/var/sftp/rki/export_2.zip ./
docker cp export_2.zip python:/opt/
rm export_2.zip

echo -e "${YEL} Test fernet encryption on python ${WHI}"
docker exec python pytest test_fernet_decryption.py

LIST_CONTAINER=( broker-server broker-connection python sftp )
echo -e "${YEL} Clean up containers ${WHI}"
for container in ${LIST_CONTAINER[*]}; do
  docker stop $container
  docker rm $container
  docker image rm $container
done
