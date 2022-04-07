#!/usr/bin/env python
# -*- coding: utf8 -*-
import base64
import gzip
import json
import logging
import os

import requests as requests

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# environment variables
ES_ADDRESS = os.getenv('ES_ADDRESS')
ES_USER = os.getenv('ES_USER')
ES_PASSWORD = os.getenv('ES_PASSWORD')
ES_API_KEY = os.getenv('ES_API_KEY')
ES_INDEX = os.getenv('ES_INDEX')
SPLUNK_TIMEOUT = os.getenv('SPLUNK_TIMEOUT')
SPLUNK_SSL_VERIFY = os.getenv('SPLUNK_SSL_VERIFY')
SPLUNK_TOKEN = os.getenv('SPLUNK_TOKEN')
SPLUNK_HTTPS = os.getenv('SPLUNK_HTTPS')
SPLUNK_HOST = os.getenv('SPLUNK_HOST')
SPLUNK_PORT = os.getenv('SPLUNK_PORT')
SPLUNK_SOURCETYPE = os.getenv('SPLUNK_SOURCETYPE')
SPLUNK_SOURCE = os.getenv('SPLUNK_SOURCE')
SPLUNK_INDEX = os.getenv('SPLUNK_INDEX')

# log setting
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # 日志等级


def write_data_to_splunk(content):
    records = content['records']

    default_fields = {}
    if SPLUNK_SOURCETYPE:
        default_fields['SPLUNK_SOURCETYPE'] = SPLUNK_SOURCETYPE
    if SPLUNK_SOURCE:
        default_fields['SPLUNK_SOURCE'] = SPLUNK_SOURCE
    if SPLUNK_INDEX:
        default_fields['SPLUNK_INDEX'] = SPLUNK_INDEX

    r = requests.session()
    r.max_redirects = 1
    r.verify = SPLUNK_SSL_VERIFY if SPLUNK_SSL_VERIFY else True
    r.headers['Authorization'] = "Splunk {}".format(SPLUNK_TOKEN)
    url = "{0}://{1}:{2}/services/collector/event".format("http" if not SPLUNK_HTTPS else "https", SPLUNK_HOST,
                                                          SPLUNK_PORT)
    timeout = SPLUNK_TIMEOUT if SPLUNK_TIMEOUT else 120
    logger.info("Log count: %s" % len(records))
    for record in records:
        # Send data to Splunk
        event = {}
        event.update(default_fields)
        event['event'] = json.dumps(record)
        data = json.dumps(event, sort_keys=True)
        try:
            res = r.post(url, data=data, timeout=timeout)
            logger.info("Response status: {}, content: {}".format(res.status_code, res.content))
            res.raise_for_status()

        except Exception as err:
            logger.debug("Failed to connect to remote Splunk server ({0}). Exception: {1}", url, err)

            # 根据需要，添加一些重试或者报告。

    logger.info("Complete send data to splunk")


# write to es
def write_data_to_es(content):
    try:
        # es client
        es = Elasticsearch([ES_ADDRESS], api_key=ES_API_KEY)
        # es = Elasticsearch([ES_ADDRESS], http_auth=(ES_USER, ES_PASSWORD))
        records = content['records']
        actions = []
        for record in records:
            action = {
                "_index": ES_INDEX,
                "_type": "_doc",
                "_source": record
            }
            actions.append(action)
        bulk(es, actions, index=ES_INDEX)
    except Exception as e:
        logger.error("Error occurred when writing to es", e)
        raise


def main_handler(event, context):
    logger.debug("start main_handler")
    logger.info(event)
    debase = base64.b64decode(event['clslogs']['data'])
    data = gzip.decompress(debase).decode()
    print(data)
    write_data_to_es(json.loads(data))
    write_data_to_splunk(json.loads(data))

    return 'success'
