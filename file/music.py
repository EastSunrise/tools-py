#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description Application of Kugou API
@Author Kingen
@Date 2020/3/31
"""
import gzip
import hashlib
import json
import os
from urllib.request import urlopen, Request

from file import base
from utils import config

logger = config.get_logger(__name__)


class Kugou:

    def __init__(self) -> None:
        self.__headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/66.0.3359.139 Safari/537.36',
            'Content-Type': 'text/html; charset=utf-8',
            'Host': 'mobilecdnbj.kugou.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8'
        }
        self.__md5object = hashlib.md5()

    def __get_result(self, url):
        logger.info('Get from %s', url)
        return json.loads(gzip.decompress(urlopen(Request(url, headers=self.__headers)).read()).decode('utf-8'))

    def get_songs_by_singer(self, singer_id, page_size=20) -> list:
        """
        Query songs of the specified singer.
        :param page_size:
        :param singer_id: id of the singer
        :return: list of songs
        """
        if page_size > 300:
            page_size = 300
        url = 'http://mobilecdnbj.kugou.com/api/v3/singer/song?singerid={singer_id}&pagesize={page_size}'.format(singer_id=singer_id, page_size=page_size)
        return self.__get_result(url)['data']['info']

    def __hash_file(self, filepath):
        with open(filepath, 'rb') as file:
            self.__md5object.update(file.read())
            return self.__md5object.hexdigest()

    def search_duplicate_songs(self, src_dir, recursive=False):
        """
        Search duplicate songs with the same name or hash value.
        :param src_dir:
        :param recursive:
        :return:
        """
        base.find_duplicate(src_dir, self.__hash_file, recursive)
        base.find_duplicate(src_dir, lambda filepath: os.path.splitext(os.path.basename(filepath))[0], recursive)
