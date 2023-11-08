FROM python:3.8

WORKDIR /opt

RUN python -m pip install --upgrade pip
RUN python -m pip install pytest

ADD scripts/* ./
ADD resources/* ./
ADD keys/* ./

RUN chmod +x count_tag_in_status_xml.sh
