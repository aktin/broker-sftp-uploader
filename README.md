# broker-sftp-uploader ![Python 3.8.10](https://img.shields.io/badge/python-3.8.10-blue)

Simple script that filters all [AKTIN Broker](https://github.com/aktin/broker) requests by a given tag and uploads the results of the filtered requests to a specified SFTP server.

Remembers the uploaded results via a created XML file that stores the request ID and the completeness of the uploaded results. Every time a result is uploaded to the SFTP server,
the corresponding file is noted in a seperate
XML file. Each element named `request-status` corresponds to one uploaded result:

```
<request-status>
    <id>2</id>
    <completion>0.5</completion>
    <uploaded>2021-10-11 09:39:50</uploaded>
</request-status>
```

The completeness of broker requests are matched with the ones saved in the XML file prior uploading to the SFTP server. Only new/changed results are uploaded. All uploaded files
are symmetrically encrypted
using [Fernet](https://github.com/fernet/spec/blob/master/Spec.md) (AES with 128-bit CBC). If a broker request is deleted, the corresponding result is also deleted from the SFTP
server.

If a result on the SFTP server is updated or deleted, a tag with the timestamp of the file operation is added to the corresponding XML element, for
example `<last-update>2021-10-11 09:39:56</last-update>`
or `<deleted>2021-10-11 09:39:55</deleted>`. The date format of all timestamps is `UTC`.

## Process

![sequence diagram](./docs/sequence.png)

## Usage

This script is only usable with a **broker-server >= 1.3.3**, as the tagging feature was only added in V1.3.3. You can execute the script from the command prompt via

```
python3 sftp_export.py <PATH_TO_MY_TOML_CONFIGURATION>
```

When the script starts, it first checks the path to the specified TOML file. It then validates the TOML file by checking for the presence of the specified scopes and keys. See also
the example TOML configuration in `test/resources`. If a key is not present, the script exits with an error message. Access to the SFTP server is only possible via a
username-password combination. Authentication via an SSH key is currently not implemented.

| Scope    | Key                 | Description                                                                                                                                                                                         | Example              |
|----------|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| BROKER   | URL                 | URL to your broker server                                                                                                                                                                           | http://localhost:8080 |
| BROKER   | API_KEY             | API key of your broker server administrator                                                                                                                                                         | xxxAdmin1234         |
| REQUESTS | TAG                 | Tag to filter requests on your broker server by                                                                                                                                                     | rki                  |
| SFTP     | HOST                | IP adress of your SFTP server                                                                                                                                                                       | 127.0.0.1            |
| SFTP     | USERNAME            | User on your SFTP server                                                                                                                                                                            | sftpuser             |
| SFTP     | PASSWORD            | User password on your SFTP user                                                                                                                                                                     | sftppassword         |
| SFTP     | TIMEOUT             | Timeout for connections to the SFTP server in seconds                                                                                                                                               | 25                   |
| SFTP     | FOLDERNAME          | Folder in SFTP root directory to upload files in. Corresponding user permissions must be set!                                                                                                       | rki                  |
| SECURITY | PATH_ENCRYPTION_KEY | Path to the fernet key for symmetric file encryption                                                                                                                                                | folder/rki.key       |
| MISC     | WORKING_DIR         | Working directory of the script. XML file to keep track of all uploaded broker request results is initialized in this folder and downloaded broker requests results are cached here for encryption. | /opt/folder          |

## File encryption and decryption

Each file uploaded to the SFTP server is symmetric encrypted using Fernet. A Fernet key is required for encryption and decryption. It is not currently possible to disable encryption in this script (via configuration). A local key can be created in Python using the following command:

```
from cryptography.fernet import Fernet

with open('rki.key', 'wb') as key:
    key.write(Fernet.generate_key())
```

To decrypt a file with your Fernet key, use the following Python command:

```
from cryptography.fernet import Fernet

with open(PATH_ENCRYPTION_KEY, 'rb') as key:
    fernet = Fernet(key.read())

with open(PATH_ENCRYPTED_FILE, 'rb') as file:
    file_encrypted = file.read()

file_decrypted = fernet.decrypt(file_encrypted)
```

## Testing

To test the script, `integration-test.sh` is attached. To run the integration test, a running instance of [Docker](https://www.docker.com/) is required. The test script will create several containers to simulate the [AKTIN Broker Server](https://github.com/aktin/broker/tree/master/broker-server), two [AKTIN Broker Clients](https://github.com/aktin/broker/tree/master/broker-client) as well as a simple SFTP server using [OpenSSH](https://www.openssh.com/).

During integration testing, the AKTIN Broker creates several requests that are picked up and completed by the AKTIN Clients. The `sftp_export.py` script is run in between to detect changes in the completeness of the generated requests. While an integration test script is running, the console displays the currently executed step. If a step fails or does not return the expected result, it is marked in red in the console. The script itself is not aborted and therefore requires a manual check for correctness.
