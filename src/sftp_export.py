# -*- coding: utf-8 -*-
"""
Created on 15.07.2021
@AUTHOR=Alexander Kombeiz (akombeiz@ukaachen.de)
@VERSION=1.3
"""

#
#      Copyright (c) 2021 AKTIN
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as
#      published by the Free Software Foundation, either version 3 of the
#      License, or (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#

import logging
import os
import re
import sys
import urllib
import xml.etree.ElementTree as et
from datetime import datetime

import paramiko
import requests
import toml
from cryptography.fernet import Fernet


# TODO outsource encryption to openssl
# TODO set encryption to be asymmetrical

class BrokerRequestResultManager:
    """
    A class for managing request results from the AKTIN Broker.
    """
    __timeout = 10

    def __init__(self):
        self.__broker_url = os.environ['BROKER.URL']
        self.__admin_api_key = os.environ['BROKER.API_KEY']
        self.__tag_requests = os.environ['REQUESTS.TAG']
        self.__check_broker_server_availability()

    def __check_broker_server_availability(self):
        url = self.__append_to_broker_url('broker', 'status')
        try:
            response = requests.head(url, timeout=self.__timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise SystemExit('Connection to AKTIN Broker timed out')
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'HTTP error occurred: {err}')
        except requests.exceptions.RequestException as err:
            raise SystemExit(f'An ambiguous error occurred: {err}')
            
    def __append_to_broker_url(self, *items: str) -> str:
        url = self.__broker_url
        for item in items:
            url = f'{url}/{item}'
        return url

    def __create_basic_header(self, mediatype: str = 'application/xml') -> dict:
        """
        HTTP header for requests to AKTIN Broker. Includes the authorization, connection, and accepted media type.
        """
        return {'Authorization': ' '.join(['Bearer', self.__admin_api_key]), 'Connection': 'keep-alive', 'Accept': mediatype}

    def get_request_result(self, id_request: str) -> requests.models.Response:
        """
        Retrieve the request results from the AKTIN Broker for a specific request ID.
        To download request results from AKTIN broker, they have to be exported first as a temporarily downloadable file with an uuid.
        """
        logging.info('Downloading results of %s', id_request)
        id_export = self.__export_request_result(id_request)
        response = self.__download_exported_result(id_export)
        return response

    def __export_request_result(self, id_request: str) -> str:
        """
        Export the request results as a temporarily downloadable file with a unique ID.
        """
        url = self.__append_to_broker_url('broker', 'export', 'request-bundle', id_request)
        response = requests.post(url, headers=self.__create_basic_header('text/plain'), timeout=self.__timeout)
        response.raise_for_status()
        return response.text

    def __download_exported_result(self, id_export: str) -> requests.models.Response:
        url = self.__append_to_broker_url('broker', 'download', id_export)
        response = requests.get(url, headers=self.__create_basic_header(), timeout=self.__timeout)
        response.raise_for_status()
        return response

    def get_tagged_requests_completion_as_dict(self) -> dict:
        """
        Get the completion status of requests tagged with a specific tag.
        """
        list_requests = self.__get_request_ids_with_tag(self.__tag_requests)
        dict_broker = {}
        for id_request in list_requests:
            completion = self.__get_request_result_completion(id_request)
            dict_broker[id_request] = str(completion)
        return dict_broker

    def __get_request_ids_with_tag(self, tag: str) -> list:
        logging.info('Checking for requests with tag %s', tag)
        url = self.__append_to_broker_url('broker', 'request', 'filtered')
        url = '?'.join([url, urllib.parse.urlencode({'type': 'application/vnd.aktin.query.request+xml', 'predicate': "//tag='%s'" % tag})])
        response = requests.get(url, headers=self.__create_basic_header(), timeout=self.__timeout)
        response.raise_for_status()
        list_request_id = [element.get('id') for element in et.fromstring(response.content)]
        logging.info('%d requests found', len(list_request_id))
        return list_request_id

    def __get_request_result_completion(self, id_request: str) -> float:
        """
        Get the completion status of a given broker request.
        Computes the result completion by counting connected nodes and the number of nodes that completed the request.
        Returns the completion percentage (rounded to 2 decimal places) or 0.0 if no nodes found.
        """
        url = self.__append_to_broker_url('broker', 'request', id_request, 'status')
        response = requests.get(url, headers=self.__create_basic_header(), timeout=self.__timeout)
        root = et.fromstring(response.content)
        num_nodes = len(root.findall('.//{http://aktin.org/ns/exchange}node'))
        num_completed = len(root.findall('.//{http://aktin.org/ns/exchange}completed'))
        return round(num_completed / num_nodes, 2) if num_nodes else 0.0


class SftpFileManager:
    """
    A class for managing file operations with an SFTP server.
    """

    def __init__(self):
        self.__sftp_host = os.environ['SFTP.HOST']
        self.__sftp_username = os.environ['SFTP.USERNAME']
        self.__sftp_password = os.environ['SFTP.PASSWORD']
        self.__sftp_timeout = int(os.environ['SFTP.TIMEOUT'])
        self.__sftp_foldername = os.environ['SFTP.FOLDERNAME']
        self.__path_key_encryption = os.environ['SECURITY.PATH_ENCRYPTION_KEY']
        self.__working_dir = os.environ['MISC.WORKING_DIR']
        self.encryptor = self.__init_encryptor()
        self.__connection = self.__connect_to_sftp()

    def __init_encryptor(self) -> Fernet:
        with open(self.__path_key_encryption, 'rb') as key:
            return Fernet(key.read())

    def __connect_to_sftp(self) -> paramiko.sftp_client.SFTPClient:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.__sftp_host, username=self.__sftp_username, password=self.__sftp_password, timeout=self.__sftp_timeout)
        return ssh.open_sftp()

    def upload_request_result(self, response: requests.models.Response):
        """
        Upload the content of the response from `BrokerRequestResultManager.get_request_result()` to the SFTP server.
        Extracts the filename from the response headers.
        Prior to uploading, stores the file temporarily in the current local folder and encrypts it using Fernet.
        """
        filename = self.__extract_filename_from_broker_response(response)
        tmp_path_file = os.path.join(self.__working_dir, filename)
        try:
            with open(tmp_path_file, 'wb') as file:
                file_encrypted = self.__encrypt_file(response.content)
                file.write(file_encrypted)
            self.upload_file(tmp_path_file)
        finally:
            if os.path.isfile(tmp_path_file):
                os.remove(tmp_path_file)

    @staticmethod
    def __extract_filename_from_broker_response(response: requests.models.Response) -> str:
        return re.search('filename=\"(.*)\"', response.headers['Content-Disposition']).group(1)

    def __encrypt_file(self, file: bytes) -> bytes:
        return self.encryptor.encrypt(file)

    def upload_file(self, path_file: str):
        """
        Upload a file to the SFTP server and overwrite if it already exists on the server.
        """
        logging.info('Sending %s to sftp server', path_file)
        filename = os.path.basename(path_file)
        self.__connection.put(path_file, f"{self.__sftp_foldername}/{filename}")

    def delete_request_result(self, id_request: str):
        name_zip = self.__create_results_file_name(id_request)
        self.__delete_file(name_zip)

    @staticmethod
    def __create_results_file_name(id_request: str) -> str:
        """
        Create the file name for the request result based on the AKTIN Broker naming convention.
        """
        return ''.join(['export_', id_request, '.zip'])

    def __delete_file(self, filename: str):
        logging.info('Deleting %s from sftp server', filename)
        try:
            self.__connection.remove(f"{self.__sftp_foldername}/{filename}")
        except FileNotFoundError:
            logging.info('%s could not be found', filename)


class StatusXmlManager:
    """
    A class for managing operations on an XML status file.
    """

    def __init__(self):
        self.path_status_xml = os.path.join(os.environ['MISC.WORKING_DIR'], 'status.xml')
        if not os.path.isfile(self.path_status_xml):
            self.__init_status_xml()
        self.__format_date = '%Y-%m-%d %H:%M:%S'
        self.__element_tree = et.parse(self.path_status_xml)

    def __init_status_xml(self):
        """
        Creates a new 'status.xml' file in the working directory with an empty <status> tag.
        """
        root = et.Element('status')
        self.__element_tree = et.ElementTree(root)
        self.__save_current_status_xml_as_file()

    def __save_current_status_xml_as_file(self):
        self.__element_tree.write(self.path_status_xml, encoding='utf-8')

    def get_element_by_id(self, id_request: str) -> et.Element:
        root = self.__element_tree.getroot()
        for request_status in root.iter('request-status'):
            id_element = request_status.find('id')
            if id_element is not None and id_element.text == id_request:
                return request_status
        return None

    def update_or_add_element(self, id_request: str, completion: str):
        root = self.__element_tree.getroot()
        for request_status in root.findall('request-status'):
            id_element = request_status.find('id')
            if id_element is not None and id_element.text == id_request:
                request_status.find('completion').text = completion
                self.__add_or_update_date_tag_in_element(request_status, 'last-update')
                break
        else:
            new_request_status = et.SubElement(root, 'request-status')
            et.SubElement(new_request_status, 'id').text = id_request
            et.SubElement(new_request_status, 'completion').text = completion
            et.SubElement(new_request_status, 'uploaded').text = datetime.utcnow().strftime(self.__format_date)
        self.__save_current_status_xml_as_file()

    def __add_or_update_date_tag_in_element(self, parent: et.Element, name_tag: str) -> None:
        child = parent.find(name_tag)
        if child is None:
            et.SubElement(parent, name_tag).text = datetime.utcnow().strftime(self.__format_date)
        else:
            child.text = datetime.utcnow().strftime(self.__format_date)

    def add_delete_tag_to_element(self, id_request: str):
        parent = self.get_element_by_id(id_request)
        self.__add_or_update_date_tag_in_element(parent, 'deleted')
        self.__save_current_status_xml_as_file()

    def get_request_completion_as_dict(self) -> dict:
        """
        Extract the request ID and completion from each element in the status XML.
        Returns them as a dictionary.
        """
        root = self.__element_tree.getroot()
        list_ids = [element.text for element in root.findall('.//id')]
        list_completion = [element.text for element in root.findall('.//completion')]
        return dict(zip(list_ids, list_completion))

    def compare_request_completion_between_broker_and_sftp(self, dict_broker: dict, dict_xml: dict) -> (set, set, set):
        set_new = set(dict_broker.keys()).difference(set(dict_xml.keys()))
        set_update = self.__get_requests_to_update(dict_broker, dict_xml)
        set_delete = self.__get_requests_to_delete(dict_broker, dict_xml)
        logging.info(f"{len(set_new)} new requests, {len(set_update)} requests to update, {len(set_delete)} requests to delete")
        return set_new, set_update, set_delete

    def __get_requests_to_update(self, dict_broker: dict, dict_xml: dict) -> set:
        """
        A request has to be updated on sftp server if its completion rate changed
        """
        set_update = set(dict_broker.keys()).intersection(set(dict_xml.keys()))
        for key in set_update.copy():
            if dict_broker.get(key) == dict_xml.get(key):
                set_update.remove(key)
            if self.__is_request_tagged_as_deleted(key):
                set_update.remove(key)
        return set_update

    def __get_requests_to_delete(self, dict_broker: dict, dict_xml: dict) -> set:
        """
        A request with the tag "deleted" is already deleted on sftp server
        """
        set_delete = set(dict_xml.keys()).difference(set(dict_broker.keys()))
        for key in set_delete.copy():
            if self.__is_request_tagged_as_deleted(key):
                set_delete.remove(key)
        return set_delete

    def __is_request_tagged_as_deleted(self, id_request: str) -> bool:
        parent = self.get_element_by_id(id_request)
        child = parent.find('deleted')
        return child is not None


class Manager:
    """
    A manager class that coordinates the uploading of tagged results to an SFTP server.
    """

    def __init__(self, path_toml: str):
        self.__verify_and_load_toml(path_toml)
        self.__broker = BrokerRequestResultManager()
        self.__sftp = SftpFileManager()
        self.__xml = StatusXmlManager()

    def __flatten_dict(self, d, parent_key='', sep='.'):
        items = []
        for k, v in d.items():
            new_key = f'{parent_key}{sep}{k}' if parent_key else k
            if isinstance(v, dict):
                items.extend(self.__flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def __verify_and_load_toml(self, path_toml: str):
        """
        This method verifies the TOML file path, loads the configuration, flattens it into a dictionary,
        and sets the environment variables based on the loaded configuration.
        """
        required_keys = {'BROKER.URL', 'BROKER.API_KEY', 'REQUESTS.TAG', 'SFTP.HOST', 'SFTP.USERNAME',
                         'SFTP.PASSWORD', 'SFTP.TIMEOUT', 'SFTP.FOLDERNAME', 'SECURITY.PATH_ENCRYPTION_KEY',
                         'MISC.WORKING_DIR'}
        if not os.path.isfile(path_toml):
            raise SystemExit('invalid TOML file path')
        with open(path_toml, encoding='utf-8') as file:
            dict_config = toml.load(file)
        flattened_config = self.__flatten_dict(dict_config)
        loaded_keys = set(flattened_config.keys())
        if required_keys.issubset(loaded_keys):
            for key in loaded_keys:
                os.environ[key] = flattened_config.get(key)
        else:
            missing_keys = required_keys - loaded_keys
            raise SystemExit(f'following keys are missing in config file: {missing_keys}')

    def upload_tagged_results_to_sftp(self):
        """
        Upload tagged results to the SFTP server.

        This method performs the following actions:
        - Retrieves the completion status of tagged requests from the broker.
        - Compares the completion status between the broker and the SFTP server.
        - Deletes results from the SFTP server for requests that have been deleted from the broker.
        - Uploads new and updated results to the SFTP server.
        - Updates the completion status in the status XML file.
        - Uploads the status XML file to the SFTP server.

        If any upload or connection fails, an exception is raised, and the process is discontinued.
        The status XML file is saved after every modification to ensure the most up-to-date state in case of failure.
        """
        dict_broker = self.__broker.get_tagged_requests_completion_as_dict()
        dict_xml = self.__xml.get_request_completion_as_dict()
        set_new, set_update, set_delete = self.__xml.compare_request_completion_between_broker_and_sftp(dict_broker, dict_xml)

        for id_request in set_delete:
            self.__sftp.delete_request_result(id_request)
            self.__xml.add_delete_tag_to_element(id_request)
        for id_request in set_new.union(set_update):
            response_zip = self.__broker.get_request_result(id_request)
            self.__sftp.upload_request_result(response_zip)
            completion = dict_broker.get(id_request)
            self.__xml.update_or_add_element(id_request, completion)
        self.__sftp.upload_file(self.__xml.path_status_xml)


def main(path_toml: str):
    try:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=[logging.StreamHandler()])
        manager = Manager(path_toml)
        manager.upload_tagged_results_to_sftp()
    except Exception as e:
        logging.exception(e)
    finally:
        [logging.root.removeHandler(handler) for handler in logging.root.handlers[:]]
        logging.shutdown()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('path to config TOML is missing!')
    main(sys.argv[1])
