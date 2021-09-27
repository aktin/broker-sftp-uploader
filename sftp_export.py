# -*- coding: utf-8 -*-
"""
Created on Thu Jul 15 16:11:47 2021
@author: Alexander Kombeiz (akombeiz@ukaachen.de)
"""

import requests
import urllib
import lxml.etree as ET
import os
import re
import logging
import paramiko
from datetime import datetime
from cryptography.fernet import Fernet


class BrokerRequestResultManager:
    # TODO BROKER_URL = 'https://aktin-broker.klinikum.rwth-aachen.de'
    BROKER_URL = 'http://localhost:8080'

    # TODO HARDOCDED?
    # API key of the AKTIN broker
    ADMIN_API_KEY = 'xxxAdmin1234'

    # Tag of broker requests corresponding to the RKI
    RKI_TAG = 'eins'

    def __init__(self):
        self.__check_broker_server_availability()

    def __check_broker_server_availability(self) -> None:
        url = self.__append_to_broker_url('broker', 'status')
        response = requests.head(url)
        if response.status_code != 200:
            raise ConnectionError('Could not connect to AKTIN Broker')

    def __append_to_broker_url(self, *items: str) -> str:
        url = self.BROKER_URL
        for item in items:
            url = '{}/{}'.format(url, item)
        return url

    def __create_basic_header_with_result_type(self, mediatype: str) -> dict:
        """
        HTTP header for requests to AKTIN Broker
        """
        return {'Authorization': ' '.join(['Bearer', self.ADMIN_API_KEY]), 'Connection': 'keep-alive',
                'Accept': mediatype}

    def get_request_result(self, id_request: str) -> requests.models.Response:
        """
        To download request results from AKTIN broker, they have to be exported
        first as a temporarily downloadable file with an uuid
        """
        logging.info('Downloading results of %s', id_request)
        uuid = self.__export_request_result(id_request)
        response = self.__download_exported_result(uuid)
        return response

    def __export_request_result(self, id_request: str) -> str:
        url = self.__append_to_broker_url('broker', 'export', 'request-bundle', id_request)
        response = requests.post(url, headers=self.__create_basic_header_with_result_type('text/plain'))
        response.raise_for_status()
        return response.text

    def __download_exported_result(self, uuid: str) -> requests.models.Response:
        url = self.__append_to_broker_url('broker', 'download', uuid)
        response = requests.get(url, headers=self.__create_basic_header_with_result_type('application/xml'))
        response.raise_for_status()
        return response

    def get_tagged_requests_completion_as_dict(self) -> dict:
        list_requests = self.__get_request_ids_with_tag(self.RKI_TAG)
        dict_broker = {}
        for id_request in list_requests:
            completion = self.__get_request_result_completion(id_request)
            dict_broker[id_request] = str(completion)
        return dict_broker

    def __get_request_ids_with_tag(self, tag: str) -> list:
        logging.info('Checking for requests with tag %s', tag)
        url = self.__append_to_broker_url('broker', 'request', 'filtered')
        url = '?'.join([url, urllib.parse.urlencode(
            {'type': 'application/vnd.aktin.query.request+xml', 'predicate': "//tag='%s'" % tag})])
        response = requests.get(url, headers=self.__create_basic_header_with_result_type('application/xml'))
        response.raise_for_status()
        list_request_id = [element.get('id') for element in ET.fromstring(response.content)]
        logging.info('%d requests found', len(list_request_id))
        return list_request_id

    def __get_request_result_completion(self, id_request: str) -> int:
        """
        Get the status of given broker request and compute result completion
        by counting connected nodes and number of nodes which completed request.
        As each tag/node gets a default namespace through lxml, the namespace
        is removed prior counting to allow a search with xpath.
        """
        url = self.__append_to_broker_url('broker', 'request', id_request, 'status')
        response = requests.get(url, headers=self.__create_basic_header_with_result_type('application/xml'))
        tree = ET.fromstring(response.content)
        tree = self.__remove_namespace_from_tree(tree)
        num_nodes = tree.xpath('count(//node)')
        num_completed = tree.xpath('count(//completed)')
        return round(num_completed / num_nodes, 2) if num_nodes else 0.0

    def __remove_namespace_from_tree(self, tree: ET._ElementTree) -> ET._ElementTree:
        for elem in tree.getiterator():
            if not hasattr(elem.tag, 'find'):
                continue
            i = elem.tag.find('}')
            if i >= 0:
                elem.tag = elem.tag[i + 1:]
        return tree


class SftpFileManager:

    # TODO HARDOCDED?
    SFTP_HOST = '192.168.56.1'
    SFTP_PORT = 22
    SFTP_USERNAME = 'ftpuser'
    SFTP_PASSWORD = 'ftpuser'

    # connection timeout in seconds
    SFTP_TIMEOUT = 25

    # Folder on sftp server to upload files to
    # Corresponding user permissions must be set on sftp server!
    SFTP_FOLDERNAME = 'rki'

    # Path to key for symmetric encryption (AES with 128-bit CBC)
    PATH_KEY_ENCRYPTION = r'C:\Users\User\PycharmProjects\rki\rki.key'
    ENCRYPTOR = None

    def __init__(self):
        self.__check_sftp_server_availability()
        self.__init_encryptor()

    def __check_sftp_server_availability(self) -> None:
        url = ''.join(['https://', self.SFTP_HOST])
        response = requests.head(url)
        if response.status_code != 200:
            raise ConnectionError('Could not connect to SFTP-Server')

    def __init_encryptor(self) -> None:
        key = open(self.PATH_KEY_ENCRYPTION, 'rb').read()
        self.ENCRYPTOR = Fernet(key)

    def __connect_to_sftp(self) -> paramiko.sftp_client.SFTPClient:
        transport = paramiko.Transport((self.SFTP_HOST, self.SFTP_PORT))
        transport.set_keepalive(self.SFTP_TIMEOUT)
        transport.connect(username=self.SFTP_USERNAME, password=self.SFTP_PASSWORD)
        return paramiko.SFTPClient.from_transport(transport)

    def upload_request_result(self, response: requests.models.Response) -> None:
        """
        Uploads response content from BrokerConnection.get_request_result() to
        sftp server. Extracts name of file from response header. Prior uploading,
        stores file temporarily in current local folder and encrypts it
        """
        name_zip = self.__extract_filename_from_broker_response(response)
        try:
            with open(name_zip, 'wb') as file_zip:
                file_encrypted = self.__encrypt_file(response.content)
                file_zip.write(file_encrypted)
            self.upload_file(name_zip)
        finally:
            if os.path.isfile(name_zip):
                os.remove(name_zip)

    def __extract_filename_from_broker_response(self, response: requests.models.Response) -> str:
        return re.search('filename=\"(.*)\"', response.headers['Content-Disposition']).group(1)

    def __encrypt_file(self, file: bytes) -> bytes:
        return self.ENCRYPTOR.encrypt(file)

    def upload_file(self, filename: str) -> None:
        """
        Upload file from current local folder to sftp server, overwrites file
        if it already exists on sftp
        """
        logging.info('Sending %s to sftp server', filename)
        with self.__connect_to_sftp() as sftp:
            sftp.put(filename, '%s/%s' % (self.SFTP_FOLDERNAME, filename))

    def delete_request_result(self, id_request: str) -> None:
        name_zip = self.__create_results_file_name(id_request)
        self.__delete_file(name_zip)

    def __create_results_file_name(self, id_request: str) -> str:
        """
        Naming convention of AKTIN Broker for downloaded results
        """
        return ''.join(['export_', id_request, '.zip'])

    def __delete_file(self, filename: str) -> None:
        logging.info('Deleting %s from sftp server', filename)
        try:
            with self.__connect_to_sftp() as sftp:
                sftp.remove('%s/%s' % (self.SFTP_FOLDERNAME, filename))
        except FileNotFoundError:
            logging.info('%s could not be found', filename)


class StatusXmlManager:
    # Name of the status xml. Is used to keep track of all uploaded broker
    # request results to sftp server
    STATUS_XML_NAME = 'status.xml'
    FORMAT_DATE = '%Y-%m-%d %H:%M:%S'

    # content of status.xml as xml tree
    ELEMENT_TREE = None

    def __init__(self):
        if not os.path.isfile(self.STATUS_XML_NAME):
            self.__init_status_xml()
        self.ELEMENT_TREE = ET.parse(self.STATUS_XML_NAME)

    def __init_status_xml(self) -> None:
        """
        Create a new status xml file in current folder with an empty <status> tag.
        """
        root = ET.Element('status')
        self.ELEMENT_TREE = ET.ElementTree(root)
        self.__save_status_xml_as_file()

    def __save_status_xml_as_file(self) -> None:
        self.ELEMENT_TREE.write(self.STATUS_XML_NAME, pretty_print=True, encoding='utf-8')

    def add_new_node_to_status_xml(self, id_request: str, completion: str) -> None:
        if self.__is_node_in_statux_xml(id_request):
            raise ValueError('Node with id %s already exists in xml' % id_request)
        element = self.__create_new_status_node(id_request, completion)
        self.ELEMENT_TREE.getroot().append(element)
        self.__save_status_xml_as_file()

    def __is_node_in_statux_xml(self, id_request: str) -> bool:
        node = self.ELEMENT_TREE.xpath("//*[local-name()='request-status']/id[text()='%s']/./.." % id_request)
        if node:
            return True
        return False

    def __create_new_status_node(self, id_request: str, completion: str) -> ET._Element:
        element = ET.Element('request-status')
        ET.SubElement(element, 'id').text = id_request
        ET.SubElement(element, 'completion').text = str(completion)
        ET.SubElement(element, 'uploaded').text = datetime.utcnow().strftime(self.FORMAT_DATE)
        return element

    def update_request_completion_of_status_node(self, id_request: str, completion: str) -> None:
        parent = self.__get_node_from_status_xml(id_request)
        parent.find('.//completion').text = completion
        self.__add_or_update_date_tag_in_node(parent, 'last-update')
        self.__save_status_xml_as_file()

    def add_delete_tag_to_status_node(self, id_request: str) -> None:
        parent = self.__get_node_from_status_xml(id_request)
        self.__add_or_update_date_tag_in_node(parent, 'deleted')
        self.__save_status_xml_as_file()

    def __get_node_from_status_xml(self, id_request: str) -> ET._Element:
        if not self.__is_node_in_statux_xml(id_request):
            raise ValueError('Node with id %s could not be found' % id_request)
        return self.ELEMENT_TREE.xpath("//*[local-name()='request-status']/id[text()='%s']/./.." % id_request)[0]

    def __add_or_update_date_tag_in_node(self, parent: ET._Element, name_tag: str) -> None:
        child = parent.find('.//%s' % name_tag)
        if child is None:
            ET.SubElement(parent, name_tag).text = datetime.utcnow().strftime(self.FORMAT_DATE)
        else:
            child.text = datetime.utcnow().strftime(self.FORMAT_DATE)

    def get_status_node_completion_as_dict(self) -> dict:
        """
        Extracts from each element in status xml the request id and the
        corresponding result completion and returns them as a dict
        """
        root = self.ELEMENT_TREE.getroot()
        list_ids = [element.text for element in root.findall('.//id')]
        list_completion = [element.text for element in root.findall('.//completion')]
        return dict(zip(list_ids, list_completion))

    def compare_request_completion_between_broker_and_sftp(self, dict_broker: dict, dict_xml: dict) -> tuple[
        set, set, set]:
        set_new = set(dict_broker.keys()).difference(set(dict_xml.keys()))
        set_update = self.__get_requests_to_update(dict_broker, dict_xml)
        set_delete = self.__get_requests_to_delete(dict_broker, dict_xml)
        logging.info('%d new requests, %d requests to update, %d requests to delete' % (
            len(set_new), len(set_update), len(set_delete)))
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
        parent = self.__get_node_from_status_xml(id_request)
        child = parent.find('.//deleted')
        return False if child is None else True


'''
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
MAIN
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
'''


def __init_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.StreamHandler()])


def __stop_logger():
    [logging.root.removeHandler(handler) for handler in logging.root.handlers[:]]
    logging.shutdown()


def __main_job():
    broker = BrokerRequestResultManager()
    sftp = SftpFileManager()
    xml = StatusXmlManager()

    dict_broker = broker.get_tagged_requests_completion_as_dict()
    dict_xml = xml.get_status_node_completion_as_dict()
    set_new, set_update, set_delete = xml.compare_request_completion_between_broker_and_sftp(dict_broker, dict_xml)

    for id_request in set_delete:
        sftp.delete_request_result(id_request)
        xml.add_delete_tag_to_status_node(id_request)
    for id_request in set_new.union(set_update):
        response_zip = broker.get_request_result(id_request)
        sftp.upload_request_result(response_zip)
        completion = dict_broker.get(id_request)
        if id_request in set_new:
            xml.add_new_node_to_status_xml(id_request, completion)
        if id_request in set_update:
            xml.update_request_completion_of_status_node(id_request, completion)
    sftp.upload_file(xml.STATUS_XML_NAME)


if __name__ == '__main__':
    try:
        __init_logger()
        __main_job()
    except Exception as e:
        logging.exception(e)
    finally:
        __stop_logger()
