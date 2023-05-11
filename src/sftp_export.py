# -*- coding: utf-8 -*-
# Created on Thu Jul 15 16:11:47 2021
# @VERSION=1.2

#
#      Copyright (c) 2022  Alexander Kombeiz
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
from datetime import datetime

import lxml.etree as ET
import paramiko
import requests
import toml
from cryptography.fernet import Fernet


# TODO outsource encryption to openssl
# TODO set encryption to be asymmetrical

class BrokerRequestResultManager:

    def __init__(self):
        self.__BROKER_URL = os.environ['BROKER.URL']
        self.__ADMIN_API_KEY = os.environ['BROKER.API_KEY']
        self.__TAG_REQUESTS = os.environ['REQUESTS.TAG']
        self.__check_broker_server_availability()

    def __check_broker_server_availability(self) -> None:
        url = self.__append_to_broker_url('broker', 'status')
        response = requests.head(url)
        if response.status_code != 200:
            raise ConnectionError('Could not connect to AKTIN Broker')

    def __append_to_broker_url(self, *items: str) -> str:
        url = self.__BROKER_URL
        for item in items:
            url = '{}/{}'.format(url, item)
        return url

    def __create_basic_header_with_result_type(self, mediatype: str) -> dict:
        """
        HTTP header for requests to AKTIN Broker
        """
        return {'Authorization': ' '.join(['Bearer', self.__ADMIN_API_KEY]), 'Connection': 'keep-alive', 'Accept': mediatype}

    def get_request_result(self, id_request: str) -> requests.models.Response:
        """
        To download request results from AKTIN broker, they have to be exported first as a temporarily downloadable file with an uuid
        """
        logging.info('Downloading results of %s', id_request)
        id_export = self.__export_request_result(id_request)
        response = self.__download_exported_result(id_export)
        return response

    def __export_request_result(self, id_request: str) -> str:
        url = self.__append_to_broker_url('broker', 'export', 'request-bundle', id_request)
        response = requests.post(url, headers=self.__create_basic_header_with_result_type('text/plain'))
        response.raise_for_status()
        return response.text

    def __download_exported_result(self, id_export: str) -> requests.models.Response:
        url = self.__append_to_broker_url('broker', 'download', id_export)
        response = requests.get(url, headers=self.__create_basic_header_with_result_type('application/xml'))
        response.raise_for_status()
        return response

    def get_tagged_requests_completion_as_dict(self) -> dict:
        list_requests = self.__get_request_ids_with_tag(self.__TAG_REQUESTS)
        dict_broker = {}
        for id_request in list_requests:
            completion = self.__get_request_result_completion(id_request)
            dict_broker[id_request] = str(completion)
        return dict_broker

    def __get_request_ids_with_tag(self, tag: str) -> list:
        logging.info('Checking for requests with tag %s', tag)
        url = self.__append_to_broker_url('broker', 'request', 'filtered')
        url = '?'.join([url, urllib.parse.urlencode({'type': 'application/vnd.aktin.query.request+xml', 'predicate': "//tag='%s'" % tag})])
        response = requests.get(url, headers=self.__create_basic_header_with_result_type('application/xml'))
        response.raise_for_status()
        list_request_id = [element.get('id') for element in ET.fromstring(response.content)]
        logging.info('%d requests found', len(list_request_id))
        return list_request_id

    def __get_request_result_completion(self, id_request: str) -> int:
        """
        Get the status of given broker request and compute result completion by counting connected nodes and number of nodes which completed request.
        As each tag/element gets a default namespace through lxml, the namespace is removed prior counting to allow a search with xpath.
        """
        url = self.__append_to_broker_url('broker', 'request', id_request, 'status')
        response = requests.get(url, headers=self.__create_basic_header_with_result_type('application/xml'))
        tree = ET.fromstring(response.content)
        tree = self.__remove_namespace_from_tree(tree)
        num_nodes = tree.xpath('count(//node)')
        num_completed = tree.xpath('count(//completed)')
        return round(num_completed / num_nodes, 2) if num_nodes else 0.0

    @staticmethod
    def __remove_namespace_from_tree(tree: ET._ElementTree) -> ET._ElementTree:
        for elem in tree.getiterator():
            if not hasattr(elem.tag, 'find'):
                continue
            i = elem.tag.find('}')
            if i >= 0:
                elem.tag = elem.tag[i + 1:]
        return tree


class SftpFileManager:

    def __init__(self):
        self.__SFTP_HOST = os.environ['SFTP.HOST']
        self.__SFTP_USERNAME = os.environ['SFTP.USERNAME']
        self.__SFTP_PASSWORD = os.environ['SFTP.PASSWORD']
        self.__SFTP_TIMEOUT = int(os.environ['SFTP.TIMEOUT'])
        self.__SFTP_FOLDERNAME = os.environ['SFTP.FOLDERNAME']
        self.__PATH_KEY_ENCRYPTION = os.environ['SECURITY.PATH_ENCRYPTION_KEY']
        self.__WORKING_DIR = os.environ['MISC.WORKING_DIR']
        self.ENCRYPTOR = self.__init_encryptor()
        self.__CONNECTION = self.__connect_to_sftp()

    def __init_encryptor(self) -> Fernet:
        with open(self.__PATH_KEY_ENCRYPTION, 'rb') as key:
            return Fernet(key.read())

    def __connect_to_sftp(self) -> paramiko.sftp_client.SFTPClient:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.__SFTP_HOST, username=self.__SFTP_USERNAME, password=self.__SFTP_PASSWORD, timeout=self.__SFTP_TIMEOUT)
        return ssh.open_sftp()

    def upload_request_result(self, response: requests.models.Response) -> None:
        """
        Uploads response content from BrokerConnection.get_request_result() to sftp server.
        Extracts name of file from response header.
        Prior uploading, stores file temporarily in current local folder and encrypts it via Fernet.
        """
        filename = self.__extract_filename_from_broker_response(response)
        tmp_path_file = os.path.join(self.__WORKING_DIR, filename)
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
        return self.ENCRYPTOR.encrypt(file)

    def upload_file(self, path_file: str) -> None:
        """
        Overwrites file if it already exists on server
        """
        logging.info('Sending %s to sftp server', path_file)
        filename = os.path.basename(path_file)
        self.__CONNECTION.put(path_file, '%s/%s' % (self.__SFTP_FOLDERNAME, filename))

    def delete_request_result(self, id_request: str) -> None:
        name_zip = self.__create_results_file_name(id_request)
        self.__delete_file(name_zip)

    @staticmethod
    def __create_results_file_name(id_request: str) -> str:
        """
        Naming convention of AKTIN Broker for downloaded results
        """
        return ''.join(['export_', id_request, '.zip'])

    def __delete_file(self, filename: str) -> None:
        logging.info('Deleting %s from sftp server', filename)
        try:
            self.__CONNECTION.remove('%s/%s' % (self.__SFTP_FOLDERNAME, filename))
        except FileNotFoundError:
            logging.info('%s could not be found', filename)


class StatusXmlManager:

    def __init__(self):
        self.PATH_STATUS_XML = os.path.join(os.environ['MISC.WORKING_DIR'], 'status.xml')
        if not os.path.isfile(self.PATH_STATUS_XML):
            self.__init_status_xml()
        self.__FORMAT_DATE = '%Y-%m-%d %H:%M:%S'
        self.__ELEMENT_TREE = ET.parse(self.PATH_STATUS_XML)

    def __init_status_xml(self) -> None:
        """
        Creates a new file 'status.xml' in working directory with an empty <status> tag
        """
        root = ET.Element('status')
        self.__ELEMENT_TREE = ET.ElementTree(root)
        self.__save_status_xml_as_file()

    def __save_status_xml_as_file(self) -> None:
        self.__ELEMENT_TREE.write(self.PATH_STATUS_XML, encoding='utf-8')

    def add_new_element_to_status_xml(self, id_request: str, completion: str) -> None:
        if self.__is_element_in_statux_xml(id_request):
            raise ValueError('Element with id %s already exists in xml' % id_request)
        element = self.__create_new_status_element(id_request, completion)
        self.__ELEMENT_TREE.getroot().append(element)
        self.__save_status_xml_as_file()

    def __is_element_in_statux_xml(self, id_request: str) -> bool:
        element = self.__ELEMENT_TREE.xpath("//*[local-name()='request-status']/id[text()='%s']/./.." % id_request)
        if element:
            return True
        return False

    def __create_new_status_element(self, id_request: str, completion: str) -> ET._Element:
        element = ET.Element('request-status')
        ET.SubElement(element, 'id').text = id_request
        ET.SubElement(element, 'completion').text = str(completion)
        ET.SubElement(element, 'uploaded').text = datetime.utcnow().strftime(self.__FORMAT_DATE)
        return element

    def update_request_completion_of_status_element(self, id_request: str, completion: str) -> None:
        parent = self.__get_element_from_status_xml(id_request)
        parent.find('.//completion').text = completion
        self.__add_or_update_date_tag_in_element(parent, 'last-update')
        self.__save_status_xml_as_file()

    def add_delete_tag_to_status_element(self, id_request: str) -> None:
        parent = self.__get_element_from_status_xml(id_request)
        self.__add_or_update_date_tag_in_element(parent, 'deleted')
        self.__save_status_xml_as_file()

    def __get_element_from_status_xml(self, id_request: str) -> ET._Element:
        if not self.__is_element_in_statux_xml(id_request):
            raise ValueError('Element with id %s could not be found' % id_request)
        return self.__ELEMENT_TREE.xpath("//*[local-name()='request-status']/id[text()='%s']/./.." % id_request)[0]

    def __add_or_update_date_tag_in_element(self, parent: ET._Element, name_tag: str) -> None:
        child = parent.find('.//%s' % name_tag)
        if child is None:
            ET.SubElement(parent, name_tag).text = datetime.utcnow().strftime(self.__FORMAT_DATE)
        else:
            child.text = datetime.utcnow().strftime(self.__FORMAT_DATE)

    def get_request_completion_as_dict(self) -> dict:
        """
        Extracts from each element in status xml the request id and the corresponding result completion and returns them as a dict
        """
        root = self.__ELEMENT_TREE.getroot()
        list_ids = [element.text for element in root.findall('.//id')]
        list_completion = [element.text for element in root.findall('.//completion')]
        return dict(zip(list_ids, list_completion))

    def compare_request_completion_between_broker_and_sftp(self, dict_broker: dict, dict_xml: dict) -> (set, set, set):
        set_new = set(dict_broker.keys()).difference(set(dict_xml.keys()))
        set_update = self.__get_requests_to_update(dict_broker, dict_xml)
        set_delete = self.__get_requests_to_delete(dict_broker, dict_xml)
        logging.info('%d new requests, %d requests to update, %d requests to delete' % (len(set_new), len(set_update), len(set_delete)))
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
        parent = self.__get_element_from_status_xml(id_request)
        child = parent.find('.//deleted')
        return False if child is None else True


class Manager:

    def __init__(self, path_toml: str):
        self.__verify_and_load_TOML(path_toml)
        self.__BROKER = BrokerRequestResultManager()
        self.__SFTP = SftpFileManager()
        self.__XML = StatusXmlManager()

    def __flatten_dict(self, d, parent_key='', sep='.'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.__flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def __verify_and_load_TOML(self, path_toml: str):
        """
        Configuration is loaded from external config TOML and saved as environment variables
        """

        required_keys = {'BROKER.URL', 'BROKER.API_KEY', 'REQUESTS.TAG', 'SFTP.HOST', 'SFTP.USERNAME',
                         'SFTP.PASSWORD', 'SFTP.TIMEOUT', 'SFTP.FOLDERNAME', 'SECURITY.PATH_ENCRYPTION_KEY',
                         'MISC.WORKING_DIR'}
        if not os.path.isfile(path_toml):
            raise SystemExit('invalid TOML file path')
        with open(path_toml) as file:
            dict_config = toml.load(file)
        flattened_config = self.__flatten_dict(dict_config)
        loaded_keys = set(flattened_config.keys())
        if required_keys.issubset(loaded_keys):
            for key in loaded_keys:
                os.environ[key] = flattened_config.get(key)
        else:
            missing_keys = required_keys - loaded_keys
            raise SystemExit('following keys are missing in config file: {0}'.format(missing_keys))

    def upload_tagged_results_to_sftp(self):
        """
        Stores results of requests with given tag on given sftp server:
        * New/updated results are uploaded and completion rate is stored in a status xml.
        * If an existing request is deleted from broker server, the corresponding result is deleted from sftp server.
        The corresponding element in status xml gets a tag named "deleted"
        * Script will throw exception and discontinue, if upload or connection fails.
        * Status xml is saved after every modification to keep the most actual state in case of failure.
        """

        dict_broker = self.__BROKER.get_tagged_requests_completion_as_dict()
        dict_xml = self.__XML.get_request_completion_as_dict()
        set_new, set_update, set_delete = self.__XML.compare_request_completion_between_broker_and_sftp(dict_broker, dict_xml)

        for id_request in set_delete:
            self.__SFTP.delete_request_result(id_request)
            self.__XML.add_delete_tag_to_status_element(id_request)
        for id_request in set_new.union(set_update):
            response_zip = self.__BROKER.get_request_result(id_request)
            self.__SFTP.upload_request_result(response_zip)
            completion = dict_broker.get(id_request)
            if id_request in set_new:
                self.__XML.add_new_element_to_status_xml(id_request, completion)
            if id_request in set_update:
                self.__XML.update_request_completion_of_status_element(id_request, completion)
        self.__SFTP.upload_file(self.__XML.PATH_STATUS_XML)


def init_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.StreamHandler()])


def stop_logger():
    [logging.root.removeHandler(handler) for handler in logging.root.handlers[:]]
    logging.shutdown()


def main(path_toml: str):
    try:
        init_logger()
        manager = Manager(path_toml)
        manager.upload_tagged_results_to_sftp()
    except Exception as e:
        logging.exception(e)
    finally:
        stop_logger()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('path to config TOML is missing!')
    main(sys.argv[1])
