#!/usr/bin/env python
# -*- coding: utf8 -*-

import datetime
import gzip
import json
import logging
import os
from io import StringIO

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# 必填参数
ES_Address = os.getenv('ES_Address')
ES_User = os.getenv('ES_User')
ES_Password = os.getenv('ES_Password')
ES_Api_Key = os.getenv('ES_API_KEY')

# 按照天或者小时设置Index，默认按照天建立索引，如填day, hour
ES_Index_TimeFormat = "day"

# es索引前缀关键词
ES_Index_KeyWord = "Log"

# 定义需要屏蔽的字符串, 以字典形式，如密码123456
ES_Clean_Word = {"123456"}

# 日志设置
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # 日志等级

# 构建es客户端
# es = Elasticsearch([ES_Address], api_key=ES_Api_Key)
es = Elasticsearch([ES_Address], http_auth=(ES_User, ES_Password))


# 自定义es索引
def createIndex(ES_Index_KeyWord, ES_Index_TimeFormat):
    # 这里可以自行更改自定义索引
    if ES_Index_TimeFormat == "day":
        ES_Index_TimeFormat = "%Y-%m-%d"
    elif ES_Index_TimeFormat == "hour":
        ES_Index_TimeFormat = "%Y-%m-%d-%H"

    index = ES_Index_KeyWord + '-' + datetime.datetime.now().strftime(ES_Index_TimeFormat)
    return index


# 定制日志清洗功能,将字符串中的敏感信息替换成***
def cleanData(data):
    try:
        if isinstance(data, str):
            for word in ES_Clean_Word:
                data = data.replace(word, "***")
        return data
    except:
        logger.error("Error occured when cleanning data")
        raise


# 处理cls数据
def deal_with_data(content):
    # 自定义index
    index_name = createIndex(ES_Index_KeyWord, ES_Index_TimeFormat)

    # 清洗功能
    # content = cleanData(content)

    # 这里可以自定义增加需要上传es的信息
    data = {
        "_index": index_name,
        "content": content,
        "doc_as_upsert": True
    }

    return data


# 写入es
def write_data_to_es(data):
    # 处理数据再写入
    data = deal_with_data(data)

    # 写入es
    try:
        bulk(es, data)
    except Exception as e:
        logger.error("Error occurred when writing to es", e)
        raise


def main_handler(event, context):
    logger.debug("start main_handler")
    logger.info(event)
    event = json.loads(gzip.GzipFile(fileobj=StringIO(event['clslogs']['data'])).read())
    data = json.dumps(event, indent=4, sort_keys=True)
    print(data)
    write_data_to_es(data)

    return 'success'
