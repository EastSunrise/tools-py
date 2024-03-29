#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Crawls data from douban.com

@Author Kingen
"""

from internet import BaseSite


class Douban(BaseSite):

    def __init__(self):
        super().__init__('https://movie.douban.com')

    def movie_top250(self, start=0):
        items = []
        while True:
            page = self.__get_items('/top250', start)
            items += page['items']
            start += page['count']
            if start >= page['total']:
                return items

    def __get_items(self, path: str, start=0):
        soup = self.get_soup(path, params={'start': start})
        items = [{
            'title': li.select_one('.title').text.strip()
        } for li in soup.select('#content li')]
        total = int(soup.select_one('.paginator .count').text.strip()[2:-2])
        return {
            'start': start,
            'count': len(items),
            'items': items,
            'total': total
        }
