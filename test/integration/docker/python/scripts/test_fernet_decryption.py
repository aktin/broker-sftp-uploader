# -*- coding: utf-8 -*-
"""
Created on Fri Okt  8 09:47:32 2021
@author: Alexander Kombeiz (akombeiz@ukaachen.de)
"""

import os
import zipfile
import unittest

from sftp_export import SftpFileManager


class TestFernetDecryption(unittest.TestCase):

    def setUp(self) -> None:
        self.NAME_FILE = 'export_2.zip'
        os.environ['SFTP_HOST'] = ''
        os.environ['SFTP_USERNAME'] = ''
        os.environ['SFTP_PASSWORD'] = ''
        os.environ['SFTP_TIMEOUT'] = '1'
        os.environ['SFTP_FOLDERNAME'] = ''
        os.environ['PATH_KEY_ENCRYPTION'] = 'rki.key'

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


if __name__ == '__main__':
    unittest.main()
