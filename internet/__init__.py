#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Basic operations for Internet.

@Author Kingen
"""
import json
import os
from typing import Optional
from urllib.parse import urlencode

import pandas
import requests
from bs4 import BeautifulSoup
from pandas import DataFrame
from urllib3.util import parse_url

import common

log = common.create_logger(__name__)
base_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/80.0.3987.132 Safari/537.36'
}


class BaseSite:
    def __init__(self, home, name=None, headers=None, cache_dir: Optional[str] = None, encoding='utf-8'):
        url = parse_url(home)
        self.__hostname = url.hostname
        self.__name = name if name else self.__hostname
        self.__root_uri = '%s://%s' % (url.scheme, url.netloc)
        self.__headers = base_headers if headers is None else headers
        self.__encoding = encoding
        self.__cache_dir = cache_dir if cache_dir is not None else os.path.join(os.getenv('TEMP'), self.__hostname)
        self.__session = requests.session()

    @property
    def hostname(self):
        return self.__hostname

    @property
    def name(self):
        return self.__name

    @property
    def root_uri(self):
        return self.__root_uri

    @property
    def cache_dir(self):
        return self.__cache_dir

    def get_soup(self, path, params=None, cache=False):
        if cache:
            filepath = self.cache_dir + path
            if params:
                filepath += '?' + urlencode(params)
            html = run_cacheable(filepath, lambda: self.__do_get(path, params), self.__encoding, ext='.html')
            return BeautifulSoup(html, 'html.parser')
        return BeautifulSoup(self.__do_get(path, params), 'html.parser')

    def get_json(self, path, params=None, cache=False):
        if cache:
            filepath = self.cache_dir + path
            if params:
                filepath += '?' + urlencode(params)
            return json.loads(run_cacheable(filepath, lambda: self.__do_get(path, params), self.__encoding, ext='.json'))
        return json.loads(self.__do_get(path, params))

    def __do_get(self, path, params):
        if params and len(params) > 0:
            log.info('Getting for %s%s with %s', self.root_uri, path, params)
        else:
            log.info('Getting for %s%s', self.root_uri, path)
        response = self.__session.get(self.root_uri + path, params=params, headers=self.__headers)
        return response.content.decode(self.__encoding, errors='ignore')


CSV_EXTENSIONS = ['.csv']
JSON_EXTENSIONS = ['.json']
PLAIN_EXTENSIONS = ['.html', '.htm', '.txt', '.php', '']


def run_cacheable(filepath, do_func, encoding='utf-8', ext: str = None):
    """
    Retrieves data directly or from file caches.
    @param filepath: filepath to store caches
    @param do_func: actual function to retrieve data
    @param encoding: encoding for the cache file
    @param ext: extension of the file
    """
    for ch in ['?']:
        filepath = filepath.replace(ch, f'#{ord(ch)}')
    filepath = filepath.rstrip('/')
    if ext is None:
        ext = str(os.path.splitext(filepath)[-1]).lower()
    if os.path.exists(filepath):
        log.info(f'Reading {filepath}')
        if ext in CSV_EXTENSIONS:
            if os.path.getsize(filepath) <= 5:
                return []
            return pandas.read_csv(filepath, encoding=encoding).to_dict('records')
        if ext in JSON_EXTENSIONS:
            with open(filepath, 'r', encoding=encoding) as fp:
                return json.load(fp)
        if ext in PLAIN_EXTENSIONS:
            with open(filepath, 'r', encoding=encoding) as fp:
                return fp.read()
        raise ValueError('Unknown mode')
    dirpath = os.path.dirname(filepath)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

    data = do_func()

    log.info(f'Writing {filepath}')
    if ext in CSV_EXTENSIONS:
        DataFrame(data).to_csv(filepath, index=False, encoding=encoding)
    elif ext in JSON_EXTENSIONS:
        with open(filepath, 'w', encoding=encoding) as fp:
            json.dump(data, fp, ensure_ascii=False, cls=common.ComplexEncoder)
    elif ext in PLAIN_EXTENSIONS:
        with open(filepath, 'w', encoding=encoding) as fp:
            fp.write(data)
    else:
        raise ValueError('Unknown mode')
    return data
