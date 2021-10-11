FROM python:3.9

WORKDIR /opt

RUN python -m pip install --upgrade pip
RUN python -m pip install pytest lxml requests paramiko cryptography

ADD scripts/* /opt/
ADD keys/* /opt/

RUN chmod +x count_tag_in_status_xml.sh
