@echo off

if not defined in_subprocess (cmd /k set in_subprocess=y ^& %0 %*) & exit )
for /F %%a in ('echo prompt $E ^| cmd') do @set "ESC=%%a"
for %%A in  (%~dp0\..\.) do set RootDirPath=%%~dpA

set ApiKey1=xxxApiKey123
set ApiKey2=xxxApiKey567

echo %ESC%[33m Build the docker-compose stack %ESC%[0m
docker-compose -f docker/docker-compose.yml up -d --force-recreate --build

echo %ESC%[33m Copy python scripts from repository to python container and run unittest %ESC%[0m
docker cp %RootDirPath%/src/sftp_export.py python:/opt/
docker exec python pytest test_xml_manager.py

echo %ESC%[33m Wait a bit to give broker-server time to start %ESC%[0m
timeout /T 10 /nobreak

echo %ESC%[33m Broker creates 3 requests with tag default and 3 with tag rki %ESC%[0m
for /l %%i in (0, 1, 2) do (
docker exec broker-connection ./broker_publish_new_request.sh rki
docker exec broker-connection ./broker_publish_new_request.sh default
)

echo %ESC%[33m Client 1 checks number of available requests (must be 6) %ESC%[0m
for /f %%i in ('docker exec broker-connection ./client_count_available_requests.sh %ApiKey1%') do set NumberRequests=%%i
if %NumberRequests% neq 6 echo %ESC%[41m invalid number of requests found %ESC%[0m

echo %ESC%[33m Broker checks number of connected nodes (must be 1) %ESC%[0m
for /f %%i in ('docker exec broker-connection ./broker_count_connected_nodes.sh') do set NumberNodes=%%i
if %NumberNodes% neq 1 echo %ESC%[41m invalid number of nodes found %ESC%[0m

echo %ESC%[33m Client 1 accepts all requests and submit results %ESC%[0m
for /l %%i in (0, 1, 5) do (
docker exec broker-connection ./client_submit_results.sh %ApiKey1% %%i
)

echo %ESC%[33m Execute the sftp python script %ESC%[0m
docker exec python python sftp_export.py

echo %ESC%[33m Container python must have 3 entries in his status.xml %ESC%[0m
for /f %%i in ('docker exec python ./count_tag_in_status_xml.sh request-status') do set NumberEntries=%%i
if %NumberEntries% neq 3 echo %ESC%[41m invalid number of entries in status.xml found %ESC%[0m

echo %ESC%[33m Container sftp must have 3 uploaded files %ESC%[0m
for /f %%i in ('docker exec sftp ./count_uploaded_zip_files.sh') do set NumberFiles=%%i
if %NumberFiles% neq 3 echo %ESC%[41m invalid number of files found %ESC%[0m

echo %ESC%[33m Container sftp must have 3 entries in his status.xml %ESC%[0m
for /f %%i in ('docker exec sftp ./count_tag_in_status_xml.sh request-status') do set NumberEntries=%%i
if %NumberEntries% neq 3 echo %ESC%[41m invalid number of entries in status.xml found %ESC%[0m

echo %ESC%[33m Broker creates one additional default and one additional rki request %ESC%[0m
docker exec broker-connection ./broker_publish_new_request.sh rki
docker exec broker-connection ./broker_publish_new_request.sh default

echo %ESC%[33m Broker deletes very first request %ESC%[0m
docker exec broker-connection ./broker_delete_request.sh 0

echo %ESC%[33m Client 2 checks number of available requests (must be 7) %ESC%[0m
for /f %%i in ('docker exec broker-connection ./client_count_available_requests.sh %ApiKey2%') do set NumberRequests=%%i
if %NumberRequests% neq 7 echo %ESC%[41m invalid number of requests found %ESC%[0m

echo %ESC%[33m Client 2 retrieve all requests %ESC%[0m
for /l %%i in (1, 1, 5) do (
docker exec broker-connection ./client_change_request_to_retrieved.sh %ApiKey2% %%i
)

echo %ESC%[33m Broker checks number of connected nodes (must be 2) %ESC%[0m
for /f %%i in ('docker exec broker-connection ./broker_count_connected_nodes.sh') do set NumberNodes=%%i
if %NumberNodes% neq 2 echo %ESC%[41m invalid number of nodes found %ESC%[0m

echo %ESC%[33m Execute the sftp python script again %ESC%[0m
docker exec python python sftp_export.py

echo %ESC%[33m Container python must have 4 entries in his status.xml %ESC%[0m
for /f %%i in ('docker exec python ./count_tag_in_status_xml.sh request-status') do set NumberEntries=%%i
if %NumberEntries% neq 4 echo %ESC%[41m invalid number of entries in status.xml found %ESC%[0m

echo %ESC%[33m Container python must have 2 updated entries in his status.xml %ESC%[0m
for /f %%i in ('docker exec python ./count_tag_in_status_xml.sh last-update') do set NumberEntries=%%i
if %NumberEntries% neq 2 echo %ESC%[41m invalid number of entries in status.xml found %ESC%[0m

echo %ESC%[33m Container python must have 1 deleted entries in his status.xml %ESC%[0m
for /f %%i in ('docker exec python ./count_tag_in_status_xml.sh deleted') do set NumberEntries=%%i
if %NumberEntries% neq 1 echo %ESC%[41m invalid number of entries in status.xml found %ESC%[0m

echo %ESC%[33m Container sftp must have 4 entries in his status.xml %ESC%[0m
for /f %%i in ('docker exec sftp ./count_tag_in_status_xml.sh request-status') do set NumberEntries=%%i
if %NumberEntries% neq 4 echo %ESC%[41m invalid number of entries in status.xml found %ESC%[0m

echo %ESC%[33m Container sftp must have 3 uploaded files %ESC%[0m
for /f %%i in ('docker exec sftp ./count_uploaded_zip_files.sh') do set NumberFiles=%%i
if %NumberFiles% neq 3 echo %ESC%[41m invalid number of files found %ESC%[0m

echo %ESC%[33m Container sftp must not have a file name export_0.zip %ESC%[0m
for /f %%i in ('docker exec sftp ./check_if_uploaded_file_exists.sh export_0.zip') do set ExitCode=%%i
if %ExitCode% neq 0 echo %ESC%[41m export_0.zip found on sftp %ESC%[0m

echo %ESC%[33m Container sftp must have a file name export_2.zip %ESC%[0m
for /f %%i in ('docker exec sftp ./check_if_uploaded_file_exists.sh export_2.zip') do set ExitCode=%%i
if %ExitCode% neq 1 echo %ESC%[41m export_2.zip not found on sftp %ESC%[0m

echo %ESC%[33m Copy export_2.zip from container sftp to container python %ESC%[0m
docker cp sftp:/var/sftp/rki/export_2.zip ./
docker cp export_2.zip python:/opt/
del export_2.zip

echo %ESC%[33m Test fernet encryption on python %ESC%[0m
docker exec python pytest test_fernet_decryption.py

set ListContainer=broker-server broker-connection python sftp
echo %ESC%[33m Stop all container %ESC%[0m
(for %%a in (%ListContainer%) do (
    docker stop %%a
))

echo %ESC%[33m Remove all container %ESC%[0m
(for %%a in (%ListContainer%) do (
    docker rm %%a
))

echo %ESC%[33m Remove all images %ESC%[0m
(for %%a in (%ListContainer%) do (
    docker image rm %%a
))

pause
