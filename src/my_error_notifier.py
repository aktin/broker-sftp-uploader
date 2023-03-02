# -*- coding: utf-8 -*-
# Created on Thu Mar 02 10:22:24 2023
# @VERSION=1.0

#
#      Copyright (c) 2023  Alexander Kombeiz
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

import os
import smtplib
from email.mime.text import MIMEText
from smtplib import SMTP_SSL as SMTP


class MyErrorNotifier:
    """
    Initialization requires config TOML to be loaded as environment variables
    """

    __TEXT_SUBTYPE: str = 'html'
    __ENCODING: str = 'iso-8859-1'

    __NOTIFIER: str = 'CHANGEME'

    __CONNECTION: smtplib.SMTP_SSL = None

    def __init__(self, name_script: str):
        self.__NAME_SCRIPT = name_script
        self.__HOST = os.environ['SMTP.HOST']
        self.__USER = os.environ['SMTP.USERNAME']
        self.__PASSWORD = os.environ['SMTP.PASSWORD']
        self.__CONNECTION = SMTP(self.__HOST)
        self.__CONNECTION.login(self.__USER, self.__PASSWORD)

    def __del__(self):
        if self.__CONNECTION:
            self.__CONNECTION.close()

    def notify_me(self, exception: str):
        mail = MIMEText(exception, self.__TEXT_SUBTYPE, self.__ENCODING)
        mail['From'] = self.__USER
        mail['To'] = [self.__NOTIFIER]
        mail['Subject'] = 'ERROR in script {0}'.format(self.__NAME_SCRIPT)
        self.__CONNECTION.sendmail(self.__USER, [self.__NOTIFIER], mail.as_string())
