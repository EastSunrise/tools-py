#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Basic operations for Internet.

@Author Kingen
"""

import requests
from bs4 import BeautifulSoup
from selenium import webdriver

base_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/80.0.3987.132 Safari/537.36'
}


def get_soup(url: str, params=None, charset='utf-8') -> BeautifulSoup:
    """
    Does request and returns a soup of the page.
    """
    if params and len(params) > 0:
        print(f'Getting for {url} with {params}')
    else:
        print('Getting for %s', url)
    return BeautifulSoup(requests.get(url, params=params, headers=base_headers).content.decode(charset), 'html.parser')


class Imitator:
    def __init__(self):
        self.edge = webdriver.Edge()

    def close(self):
        self.edge.quit()
