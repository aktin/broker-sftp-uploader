import os
import src.sftp_export

try:
    path_parent = os.path.dirname(os.getcwd())
    path_local = os.path.join(path_parent, 'local')
    path_settings = os.path.join(path_local, 'settings.json')
    src.sftp_export.main(path_settings)
finally:
    os.remove('status.xml')
