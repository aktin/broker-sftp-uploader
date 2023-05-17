import os
import time
import unittest
import xml.etree.ElementTree as et

from sftp_export import StatusXmlManager


class TestStatusXmlManager(unittest.TestCase):

    def setUp(self):
        self.dir_current = os.getcwd()
        os.environ['MISC.WORKING_DIR'] = self.dir_current
        self.addCleanup(os.remove, os.path.join(self.dir_current, 'status.xml'))

    def test_init(self):
        xml = StatusXmlManager()
        self.assertTrue(os.path.isfile(xml.path_status_xml))

    def test_add_node(self):
        xml = StatusXmlManager()
        xml.update_or_add_element('1', '10')
        xml.update_or_add_element('2', '20')
        xml.update_or_add_element('3', '30')
        tree = et.parse(xml.path_status_xml)
        root = tree.getroot()
        self.assertEqual(3, len(list(root)))

    def test_update_node(self):
        xml = StatusXmlManager()
        xml.update_or_add_element('1', '10')
        xml.update_or_add_element('2', '20')
        xml.update_or_add_element('3', '30')
        xml.update_or_add_element('1', '100')
        xml.update_or_add_element('2', '100')
        node_1 = xml.get_element_by_id('1')
        self.assertEqual('100', node_1.find('completion').text)
        self.assertIsNotNone(node_1.find('last-update'))
        node_2 = xml.get_element_by_id('2')
        self.assertEqual('100', node_2.find('completion').text)
        self.assertIsNotNone(node_2.find('last-update'))
        node_3 = xml.get_element_by_id('3')
        self.assertEqual('30', node_3.find('completion').text)
        self.assertIsNone(node_3.find('last-update'))

    def test_update_node_multiple(self):
        xml = StatusXmlManager()
        xml.update_or_add_element('1', '10')
        xml.update_or_add_element('1', '20')
        node_1 = xml.get_element_by_id('1')
        self.assertIsNotNone(node_1.find('last-update'))
        ts_update = node_1.find('last-update').text
        time.sleep(1)
        xml.update_or_add_element('1', '30')
        node_1 = xml.get_element_by_id('1')
        self.assertIsNotNone(node_1.find('last-update'))
        ts_update2 = node_1.find('last-update').text
        self.assertNotEqual(ts_update, ts_update2)

    def test_add_delete_tag(self):
        xml = StatusXmlManager()
        xml.update_or_add_element('1', '10')
        xml.update_or_add_element('2', '20')
        xml.update_or_add_element('3', '30')
        xml.add_delete_tag_to_element('1')
        xml.add_delete_tag_to_element('2')
        node_1 = xml.get_element_by_id('1')
        self.assertIsNotNone(node_1.find('deleted'))
        node_2 = xml.get_element_by_id('2')
        self.assertIsNotNone(node_2.find('deleted'))
        node_3 = xml.get_element_by_id('3')
        self.assertIsNone(node_3.find('deleted'))

    def test_add_delete_tag_multiple(self):
        xml = StatusXmlManager()
        xml.update_or_add_element('1', '10')
        xml.add_delete_tag_to_element('1')
        node_1 = xml.get_element_by_id('1')
        self.assertIsNotNone(node_1.find('deleted'))
        ts_delete = node_1.find('deleted').text
        time.sleep(1)
        xml.add_delete_tag_to_element('1')
        node_1 = xml.get_element_by_id('1')
        self.assertIsNotNone(node_1.find('deleted'))
        ts_delete2 = node_1.find('deleted').text
        self.assertNotEqual(ts_delete, ts_delete2)

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
        xml.update_or_add_element('1', '100')
        xml.add_delete_tag_to_element('1')
        xml.update_or_add_element('2', '200')
        xml.update_or_add_element('2', '300')
        xml.update_or_add_element('3', '400')
        xml.update_or_add_element('4', '500')
        xml.update_or_add_element('5', '600')
        xml.update_or_add_element('5', '700')
        xml.add_delete_tag_to_element('5')
        return xml


if __name__ == '__main__':
    unittest.main()
