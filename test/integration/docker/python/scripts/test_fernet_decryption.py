import os
import unittest
import zipfile

import toml
from sftp_export import SftpFileManager


class TestFernetDecryption(unittest.TestCase):

    def setUp(self) -> None:
        self.name_file = 'export_2.zip'
        self.name_config = 'settings.toml'
        self.__load_config_file()

    def test_decryption(self) -> None:
        self.assertTrue(os.path.exists(self.name_file))
        self.assertFalse(zipfile.is_zipfile(self.name_file))
        self.__decrypt_with_fernet()
        self.assertTrue(zipfile.is_zipfile(self.name_file))
        self.__encrypt_with_fernet()
        self.assertFalse(zipfile.is_zipfile(self.name_file))

    def __decrypt_with_fernet(self) -> None:
        sftp = SftpFileManager()
        with open(self.name_file, 'rb') as file_zip:
            file_encrypted = file_zip.read()
        file_decrypted = sftp.encryptor.decrypt(file_encrypted)
        with open(self.name_file, 'wb') as file_zip:
            file_zip.write(file_decrypted)

    def __encrypt_with_fernet(self) -> None:
        sftp = SftpFileManager()
        with open(self.name_file, 'rb') as file_zip:
            file_decrypted = file_zip.read()
        file_encrypted = sftp.encryptor.encrypt(file_decrypted)
        with open(self.name_file, 'wb') as file_zip:
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
        with open(self.name_config) as file_json:
            dict_config = toml.load(file_json)
            flattened_config = self.__flatten_dict(dict_config)
        set_keys = set(flattened_config.keys())
        for key in set_keys:
            os.environ[key] = flattened_config.get(key)


if __name__ == '__main__':
    unittest.main()
