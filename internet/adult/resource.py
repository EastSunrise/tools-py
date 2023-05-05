#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Sites of adult resources.

@Author Kingen
"""
import math
import re
from typing import List, Dict, Tuple

from werkzeug.exceptions import NotFound

from internet import base_headers
from internet.adult import ActorSupplier, AdultSite


class HuiAV(AdultSite, ActorSupplier):
    INTRO_REGEX = re.compile("文件大小：\\s*-?((\\d+[,\\s])?\\d+(\\.\\.?\\d*)?)\\s?(KB|MB|GB)", re.RegexFlag.IGNORECASE)

    def __init__(self):
        headers = base_headers.copy()
        headers['cookie'] = 'sort=3'
        super().__init__('https://www.huiav.com', headers=headers)

    def list_actors(self) -> List[Dict]:
        return self.__list_records_by_page(lambda x: self.__parse_actor_indices(f'/home/0_{x}.html'))

    def __parse_actor_indices(self, path) -> Tuple[int, List[Dict]]:
        soup = self.get_soup(path, cache=True)
        total = int(soup.select_one('.actor_box h1 span').text.strip()[:-3])
        return total, [{
            'rank': int(ul.select_one('span.rank').text.strip()),
            'name': ul.select_one('a')['title'].strip(),
            'vid': int(ul.select_one('li.eye')['vid']),
            'image': ul.select_one('img')['img'],
            'count': int(ul.select_one('span[type=total]').text.strip()),
            'view': int(ul.select_one('span[type=view]').text.strip()),
            'like': int(ul.select_one('span[type=like]').text.strip())
        } for ul in soup.select_one('.actor_box').select('ul')]

    def list_works(self) -> List[Dict]:
        return [self.get_work_detail(x['vid']) for x in self.list_work_indices()]

    def list_work_indices(self) -> List[Dict]:
        indices = []
        for k, mosaic in [(1, True), (2, False)]:
            for w in self.__list_records_by_page(lambda x: self.__parse_work_indices(f'/home/{k}_{x}.html')):
                w['mosaic'] = mosaic
                indices.append(w)
        return sorted(indices, key=lambda x: x['vid'])

    def __parse_work_indices(self, path) -> Tuple[int, List[Dict]]:
        soup = self.get_soup(path, cache=True)
        actor_box = soup.select_one('.actor_box')
        if actor_box is None:
            return 0, []
        total = int(actor_box.select_one('h1 span').text.strip()[:-3])
        return total, [{
            'vid': int(ul.select_one('li.eye')['vid']),
            'title': ul.select_one('a')['title'],
            'cover': ul.select_one('img')['img'],
            'src_count': int(ul.select_one('span[type=total]').text.strip()),
            'view': int(ul.select_one('span[type=view]').text.strip()),
            'like': int(ul.select_one('span[type=like]').text.strip())
        } for ul in actor_box.select('ul')]

    def get_work_detail(self, vid) -> Dict:
        soup = self.get_soup(f'/{vid}/#.html', cache=True)
        if soup.select_one('.site') is None:
            raise NotFound()
        serial_number = soup.select('.site a')[-1].text.strip()
        cover = soup.select_one('.left').select_one('img')['img']
        actors = []
        for li in soup.select_one('.right').select_one('.actor').select('li'):
            parts = li.select_one('a')['href'].strip('/').split('/')
            actors.append({'vid': int(parts[0]), 'name': parts[1]})
        online_links = [{
            'link': ul.select_one('a')['href'].replace('\n', ' '),
            'image': ul.select_one('img')['img'],
            'time': ul.select_one('.time').text.strip(),
            'title': ul.select_one('.title').text.strip().replace('\n', ' ')
        } for ul in soup.select_one('.list_box').select('ul')]
        magnet_links = [{
            'title': ul.select_one('.title').text.strip().replace('\n', ' '),
            'filesize': self.__parse_filesize(ul.select_one('.intro').text.strip().replace('\n', ' ')),
            'link': ul.select_one('span').text.strip().replace('\n', ' ')
        } for ul in soup.select_one('#magnet').select('ul')]
        return {
            'vid': vid,
            'serial_number': serial_number,
            'cover': cover.replace(".jpgf.jpg", ".jpg"),
            'actors': actors,
            'online_links': online_links,
            'magnet_links': magnet_links
        }

    def __parse_filesize(self, intro):
        matcher = self.INTRO_REGEX.fullmatch(intro)
        if matcher is None:
            return None

        filesize = float(matcher.group(1).replace(",", "").replace(" ", "").replace("..", "."))
        if "GB" == matcher.group(4):
            filesize *= 1024 * 1024

        elif "MB" == matcher.group(4):
            filesize *= 1024
        filesize *= 1024
        return int(filesize)

    def __list_records_by_page(self, parse_func):
        page_index, stop, records = 1, 1, []
        while page_index <= stop:
            total, data = parse_func(page_index)
            records.extend(data)
            page_index += 1
            stop = math.ceil(total / 36)
        return sorted(records, key=lambda x: x['vid'])
