# -*- coding: utf-8 -*-
"""
Created on Fri Okt  8 09:47:32 2021
@author: Alexander Kombeiz (akombeiz@ukaachen.de)
"""

import os
import unittest
import zipfile

import toml
from sftp_export import SftpFileManager


class TestFernetDecryption(unittest.TestCase):

    def setUp(self) -> None:
        self.NAME_FILE = 'export_2.zip'
        self.NAME_CONFIG = 'settings.toml'
        self.__load_config_file()

    def test_decryption(self) -> None:
        self.assertTrue(os.path.exists(self.NAME_FILE))
        self.assertFalse(zipfile.is_zipfile(self.NAME_FILE))
        self.__decrypt_with_fernet()
        self.assertTrue(zipfile.is_zipfile(self.NAME_FILE))
        self.__encrypt_with_fernet()
        self.assertFalse(zipfile.is_zipfile(self.NAME_FILE))

    def __decrypt_with_fernet(self) -> None:
        sftp = SftpFileManager()
        with open(self.NAME_FILE, 'rb') as file_zip:
            file_encrypted = file_zip.read()
        file_decrypted = sftp.ENCRYPTOR.decrypt(file_encrypted)
        with open(self.NAME_FILE, 'wb') as file_zip:
            file_zip.write(file_decrypted)

    def __encrypt_with_fernet(self) -> None:
        sftp = SftpFileManager()
        with open(self.NAME_FILE, 'rb') as file_zip:
            file_decrypted = file_zip.read()
        file_encrypted = sftp.ENCRYPTOR.encrypt(file_decrypted)
        with open(self.NAME_FILE, 'wb') as file_zip:
            file_zip.write(file_encrypted)

    def __flatten_dict(self, d, parent_key='', sep='.'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.__flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def __load_config_file(self):
        with open(self.NAME_CONFIG) as file_json:
            dict_config = toml.load(file_json)
            flattened_config = self.__flatten_dict(dict_config)
        set_keys = set(flattened_config.keys())
        for key in set_keys:
            os.environ[key] = flattened_config.get(key)


if __name__ == '__main__':
    unittest.main()
