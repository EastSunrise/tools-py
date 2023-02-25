#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Basic operations for Internet.

@Author Kingen
"""
import json
import os
from typing import Optional

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
    def __init__(self, host, headers=None, cache_dir: Optional[str] = None):
        self.__host = host
        self.__headers = base_headers if headers is None else headers
        self.__cache_dir = cache_dir if cache_dir is not None else os.path.join(os.getenv('TEMP'), parse_url(host).host)

    @property
    def host(self):
        return self.__host

    @property
    def cache_dir(self):
        return self.__cache_dir

    def _get_soup(self, path, cache=False):
        if cache:
            return get_soup(f'{self.host}{path}', headers=self.__headers, cache_path=f'{self.__cache_dir}{path}')
        return get_soup(f'{self.host}{path}', headers=self.__headers)


def get_soup(url: str, params=None, charset='utf-8', headers=None, cache_path=None) -> BeautifulSoup:
    """
    Does request and returns a soup of the page.
    """

    def get_content():
        if params and len(params) > 0:
            log.info(f'Getting for {url} with {params}')
        else:
            log.info(f'Getting for {url}')
        return requests.get(url, params=params, headers=headers).content.decode(charset)

    if headers is None:
        headers = base_headers
    if cache_path is None:
        return BeautifulSoup(get_content(), 'html.parser')
    return BeautifulSoup(get_cache(cache_path, 'html', get_content), 'html.parser')


def get_cache(filepath, mode, do_func, *args, encoding='utf-8'):
    """
    Retrieves data within file cache.
    @param filepath: filepath to store cache
    @param mode: type of data
    @param do_func: actual function to retrieve data which is called when there is no cache
    @param args: args for actual function
    @param encoding: encoding for the cache file
    """
    for ch in ['?']:
        filepath = filepath.replace(ch, f'#{ord(ch)}')
    filepath.rstrip('/')
    if os.path.exists(filepath):
        log.info(f'Reading {filepath}')
        if mode == 'csv':
            if os.path.getsize(filepath) <= 5:
                return []
            return pandas.read_csv(filepath, encoding=encoding).to_dict('records')
        if mode == 'json':
            with open(filepath, 'r', encoding=encoding) as fp:
                return json.load(fp)
        if mode == 'html':
            with open(filepath, 'r', encoding=encoding) as fp:
                return fp.read()
        raise ValueError('Unknown mode')
    dirpath = os.path.dirname(filepath)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

    data = do_func(*args)

    log.info(f'Writing {filepath}')
    if mode == 'csv':
        DataFrame(data).to_csv(filepath, index=False, encoding=encoding)
    elif mode == 'json':
        with open(filepath, 'w', encoding=encoding) as fp:
            json.dump(data, fp, ensure_ascii=False)
    elif mode == 'html':
        with open(filepath, 'w', encoding=encoding) as fp:
            fp.write(data)
    else:
        raise ValueError('Unknown mode')
    return data
