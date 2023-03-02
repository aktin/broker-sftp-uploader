import smtplib
from email.mime.text import MIMEText
from smtplib import SMTP_SSL as SMTP


class MyErrorNotifier:
    __TEXT_SUBTYPE: str = 'html'
    __ENCODING: str = 'iso-8859-1'

    __HOST: str = 'CHANGEME'
    __USER: str = 'CHANGEME'
    __PASSWORD: str = 'CHANGEME'
    __NOTIFIER: str = 'CHANGEME'

    __CONNECTION: smtplib.SMTP_SSL = None

    def __init__(self, name_script: str):
        self.__NAME_SCRIPT = name_script
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
