#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Basic operations for Internet.

@Author Kingen
"""
import json
import os
import pickle
from typing import Optional
from urllib.parse import urlencode

import requests
import unicodedata
from bs4 import BeautifulSoup
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
        self.__name = name or self.__hostname
        self.__root_uri = '%s://%s' % (url.scheme, url.netloc)
        self.__headers = {**base_headers, 'Host': url.hostname, **(headers or {})}
        self.__encoding = encoding
        self.__cache_dir = cache_dir or os.path.join(os.getenv('TEMP'), self.__hostname)
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

    def get_soup(self, path, params=None, cache=False, retry=False):
        return BeautifulSoup(self._do_get_cacheable(path, params, cache, retry), 'html.parser')

    def get_json(self, path, params=None, cache=False, retry=False):
        return json.loads(self._do_get_cacheable(path, params, cache, retry))

    def format_json(self, data):
        if data is None:
            return None
        return json.loads(json.dumps(data, ensure_ascii=False, cls=common.ComplexEncoder))

    def post_json(self, path, query=None, data=None, json_data=None, cache=False, retry=False):
        return json.loads(self._do_post_cacheable(path, query, data, json_data, cache, retry))

    def _do_get_cacheable(self, path, params=None, cache=False, retry=False):
        if cache:
            op = 'cache' if not retry else 'put'
            filepath = self.cache_dir + path
            if params:
                filepath += '?' + urlencode(params)
            return run_cacheable(filepath, lambda: self._do_get(path, params), op)
        return self._do_get(path, params)

    def _do_get(self, path, params=None):
        if params and len(params) > 0:
            log.debug('Getting for %s%s?%s', self.root_uri, path, '&'.join(k + '=' + str(v) for k, v in params.items()))
        else:
            log.debug('Getting for %s%s', self.root_uri, path)
        response = self.__session.get(self.root_uri + path, params=params, headers=self.__headers)
        response.raise_for_status()
        return response.content.decode(self.__encoding, errors='ignore')

    def _do_post_cacheable(self, path, query=None, data=None, json_data=None, cache=False, retry=False):
        if cache:
            op = 'cache' if not retry else 'put'
            filepath = self.cache_dir + path
            if query:
                filepath += '?' + urlencode(query)
            return run_cacheable(filepath, lambda: self._do_post(path, query, data, json_data), op)
        return self._do_post(path, query, data, json_data)

    def _do_post(self, path, query=None, data=None, json_data=None):
        if query and len(query) > 0:
            log.debug('Posting for %s%s?%s', self.root_uri, path, '&'.join(k + '=' + str(v) for k, v in query.items()))
        else:
            log.debug('Posting for %s%s', self.root_uri, path)
        response = self.__session.post(self.root_uri + path, params=query, headers=self.__headers, data=data,
                                       json=json_data)
        return response.content.decode(self.__encoding, errors='ignore')


def run_cacheable(filepath, do_func, op='cache'):
    """
    Retrieves data directly or from associated cache stored as file.
    If op is 'cache', apply caching behaviour.
    If op is 'put', always invoke the actual function and cache the newer result.
    If op is 'evict', remove the cache if found and invoke the actual function

    @param filepath: filepath to store associate cache
    @param do_func: actual function to retrieve data
    @param op: option of 'cache', 'put' and 'evict'
    """
    for ch in ['?']:
        filepath = filepath.replace(ch, f'#{ord(ch)}')
    filepath = filepath.rstrip('/') + '.pkl'

    if op == 'cache' and os.path.exists(filepath):
        log.debug(f'reading cache from {filepath}')
        with open(filepath, 'rb') as fp:
            return pickle.load(fp)

    if (op == 'cache' and not os.path.exists(filepath)) or op == 'put':
        data = do_func()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        log.debug(f'writing cache to {filepath}')
        with open(filepath, 'wb') as fp:
            pickle.dump(data, fp)
        return data

    if op == 'evict':
        if os.path.exists(filepath):
            log.debug(f'removing cache from {filepath}')
            os.remove(filepath)
        return do_func()

    raise ValueError('cannot run with unknown operation: ' + op)


def normalize_str(s: str):
    res = ''
    for ch in s:
        width = unicodedata.east_asian_width(ch)
        if width == 'F' or width == 'H':
            ch = unicodedata.normalize('NFKC', ch)
        res += ch
    return res


class DuplicateError(Exception):
    pass
