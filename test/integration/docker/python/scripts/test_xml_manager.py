# -*- coding: utf-8 -*-
"""
Created on Wed Aug  4 15:09:04 2021
@author: Alexander Kombeiz (akombeiz@ukaachen.de)
"""

import os
import unittest

import lxml.etree as ET
from sftp_export import StatusXmlManager


class TestStatusXmlManager(unittest.TestCase):

    def setUp(self):
        self.dir_current = os.getcwd()
        os.environ['MISC.WORKING_DIR'] = self.dir_current
        self.addCleanup(os.remove, os.path.join(self.dir_current, 'status.xml'))

    def test_init(self):
        xml = StatusXmlManager()
        self.assertTrue(os.path.isfile(xml.PATH_STATUS_XML))

    def test_add_node(self):
        xml = StatusXmlManager()
        xml.add_new_element_to_status_xml('1', '10')
        xml.add_new_element_to_status_xml('2', '20')
        xml.add_new_element_to_status_xml('3', '30')
        tree = ET.parse(xml.PATH_STATUS_XML)
        root = tree.getroot()
        self.assertEqual(3, len(root.getchildren()))

    def test_add_node_error(self):
        xml = StatusXmlManager()
        xml.add_new_element_to_status_xml('1', '10')
        with self.assertRaises(Exception):
            xml.add_new_element_to_status_xml('1', '20')

    def test_update_node(self):
        xml = StatusXmlManager()
        xml.add_new_element_to_status_xml('1', '10')
        xml.add_new_element_to_status_xml('2', '20')
        xml.add_new_element_to_status_xml('3', '30')
        xml.update_request_completion_of_status_element('1', '100')
        xml.update_request_completion_of_status_element('2', '100')
        tree = ET.parse(xml.PATH_STATUS_XML)
        list_tags = tree.getroot().findall('.//last-update')
        self.assertEqual(2, len(list_tags))
        node_1 = tree.xpath("//*[local-name()='request-status']/id[text()='%s']/./.." % '1')[0]
        self.assertEqual('100', node_1.find('.//completion').text)
        node_2 = tree.xpath("//*[local-name()='request-status']/id[text()='%s']/./.." % '2')[0]
        self.assertEqual('100', node_2.find('.//completion').text)
        node_3 = tree.xpath("//*[local-name()='request-status']/id[text()='%s']/./.." % '3')[0]
        self.assertEqual('30', node_3.find('.//completion').text)

    def test_update_node_error(self):
        xml = StatusXmlManager()
        with self.assertRaises(Exception):
            xml.update_request_completion_of_status_element('1', '100')

    def test_update_node_multiple(self):
        xml = StatusXmlManager()
        xml.add_new_element_to_status_xml('1', '10')
        xml.update_request_completion_of_status_element('1', '20')
        xml.update_request_completion_of_status_element('1', '30')
        xml.update_request_completion_of_status_element('1', '40')
        tree = ET.parse(xml.PATH_STATUS_XML)
        node_1 = tree.xpath("//*[local-name()='request-status']/id[text()='%s']/./.." % '1')[0]
        self.assertEqual(1, len(node_1.findall('.//last-update')))
        self.assertEqual('40', node_1.find('.//completion').text)

    def test_add_delete_tag(self):
        xml = StatusXmlManager()
        xml.add_new_element_to_status_xml('1', '10')
        xml.add_new_element_to_status_xml('2', '20')
        xml.add_new_element_to_status_xml('3', '30')
        xml.add_delete_tag_to_status_element('1')
        xml.add_delete_tag_to_status_element('2')
        tree = ET.parse(xml.PATH_STATUS_XML)
        list_tags = tree.getroot().findall('.//deleted')
        self.assertEqual(2, len(list_tags))

    def test_add_delete_tag_error(self):
        xml = StatusXmlManager()
        with self.assertRaises(Exception):
            xml.add_delete_tag_to_status_element('1')

    def test_add_delete_tag_multiple(self):
        xml = StatusXmlManager()
        xml.add_new_element_to_status_xml('1', '10')
        xml.add_delete_tag_to_status_element('1')
        xml.add_delete_tag_to_status_element('1')
        xml.add_delete_tag_to_status_element('1')
        tree = ET.parse(xml.PATH_STATUS_XML)
        node_1 = tree.xpath("//*[local-name()='request-status']/id[text()='%s']/./.." % '1')[0]
        self.assertEqual(1, len(node_1.findall('.//deleted')))

    def test_dict_node_completion(self):
        xml = StatusXmlManager()
        xml = self.__fill_xml_tree(xml)
        dict_xml = xml.get_request_completion_as_dict()
        expect = {'1': '100', '2': '300', '3': '400', '4': '500', '5': '700'}
        self.assertEqual(expect, dict_xml)

    def test_compare_completion_only_new(self):
        xml = StatusXmlManager()
        xml = self.__fill_xml_tree(xml)
        dict_broker = {'5': '50', '6': '60'}
        dict_xml = xml.get_request_completion_as_dict()
        set_new, _, _ = xml.compare_request_completion_between_broker_and_sftp(dict_broker, dict_xml)
        self.assertEqual(1, len(set_new))

    def test_compare_completion_only_update(self):
        xml = StatusXmlManager()
        xml = self.__fill_xml_tree(xml)
        dict_broker = {'1': '10', '2': '20', '3': '30', '6': '60'}
        dict_xml = xml.get_request_completion_as_dict()
        _, set_update, _ = xml.compare_request_completion_between_broker_and_sftp(dict_broker, dict_xml)
        self.assertEqual(2, len(set_update))

    def test_compare_completion_only_delete(self):
        xml = StatusXmlManager()
        xml = self.__fill_xml_tree(xml)
        dict_broker = {'2': '20', '3': '30', '6': '60'}
        dict_xml = xml.get_request_completion_as_dict()
        _, _, set_delete = xml.compare_request_completion_between_broker_and_sftp(dict_broker, dict_xml)
        self.assertEqual(1, len(set_delete))

    @staticmethod
    def __fill_xml_tree(xml: StatusXmlManager):
        xml.add_new_element_to_status_xml('1', '100')
        xml.add_delete_tag_to_status_element('1')
        xml.add_new_element_to_status_xml('2', '200')
        xml.update_request_completion_of_status_element('2', '300')
        xml.add_new_element_to_status_xml('3', '400')
        xml.add_new_element_to_status_xml('4', '500')
        xml.add_new_element_to_status_xml('5', '600')
        xml.update_request_completion_of_status_element('5', '700')
        xml.add_delete_tag_to_status_element('5')
        return xml


if __name__ == '__main__':
    unittest.main()
