FROM ubuntu:15.04
MAINTAINER Tim Marcinowski <marshyski@gmail.com>

USER root

RUN apt-get update && apt-get install -y \
  python2.7 \
  python-dev \
  libffi-dev \
  libssl-dev \
  python-pip

#RUN pip install requests[security]
RUN mkdir -p /opt/devhub
ADD . /opt/devhub
RUN pip install -r /opt/devhub/requirements.txt
RUN pip freeze | sort

EXPOSE 8888

CMD cd /opt/devhub && python __init__.py
