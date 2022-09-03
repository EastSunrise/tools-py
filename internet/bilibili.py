#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Crawls data from bilibili.com

@Author Kingen
"""

import requests

import internet


class Bilibili:
    API = 'https://api.bilibili.com'

    def __get_data(self, path: str, params: dict) -> dict:
        json = requests.get(self.API + path, params=params, headers=internet.base_headers).json()
        return json['data']

    def __get_content(self, path: str, params: dict) -> str:
        return requests.get(self.API + path, params=params, headers=internet.base_headers).text

    def get_series_list(self, userid: int, season_id: int, page_num=1, page_size=30) -> dict:
        params = {
            'mid': userid,
            'series_id': season_id,
            'only_normal': 'true',
            'sort': 'desc',
            'pn': page_num,
            'ps': page_size
        }
        return self.__get_data('/x/series/archives', params=params)

    def download_bullet_screen(self, vid: str, filepath: str) -> None:
        if vid.upper().startswith('BV'):
            params = {'bvid': vid}
        elif vid.upper().startswith('AV'):
            params = {'aid': vid[2:]}
        else:
            raise ValueError
        page_list = self.__get_data('/x/player/pagelist', params=params)
        params = {'oid': page_list[0]['cid']}
        with open(filepath, 'w') as f:
            f.write(self.__get_content('/x/v1/dm/list.so', params=params))

    def get_video(self, userid: int, page_num=1, page_size=30) -> dict:
        params = {
            'mid': userid,
            'tid': 0,
            'keyword': '',
            'pn': page_num,
            'ps': page_size,
            'order': 'pubdate',
            'jsonp': 'jsonp'
        }
        return self.__get_data('/x/space/arc/search', params=params)
