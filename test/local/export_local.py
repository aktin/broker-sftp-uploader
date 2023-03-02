import os
import sys
import time
from pathlib import Path

this_path = Path(os.path.realpath(__file__))
path_src = os.path.join(this_path.parents[2], 'src')
sys.path.insert(0, path_src)

import sftp_export

path_settings = os.path.join(this_path.parents[1], 'resources', 'settings.toml')
start_time = time.time()
sftp_export.main(path_settings)
print("--- %s seconds ---" % (time.time() - start_time))
