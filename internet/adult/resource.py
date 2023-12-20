#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Sites of adult resources.

@Author Kingen
"""
import math
import os
import re
from typing import Tuple, List
from urllib.parse import urljoin

from werkzeug.exceptions import NotFound

from common import create_logger
from internet import base_headers
from internet.adult import AdultSite, ActorSite, export

log = create_logger(__name__)


class HuiAV(AdultSite, ActorSite):
    intro_regexp = re.compile("文件大小：\\s*-?((\\d+[,\\s])?\\d+(\\.\\.?\\d*)?)\\s?(KB|MB|GB)", re.RegexFlag.IGNORECASE)

    def __init__(self):
        headers = base_headers.copy()
        headers['cookie'] = 'sort=3'
        super().__init__('https://www.huiav.com', name='huiav', headers=headers)

    def list_actors(self) -> List[dict]:
        return self.__list_records_by_page(lambda x: self.__parse_actor_indices(f'/home/0_{x}.html'))

    def __parse_actor_indices(self, path) -> Tuple[int, List[dict]]:
        soup = self.get_soup(path, cache=True)
        total = int(soup.select_one('.actor_box h1 span').text.strip()[:-3])
        return total, [{
            'aid': ul.select_one('li.eye')['vid'],
            'name': ul.select_one('a')['title'].strip(),
            'rank': int(ul.select_one('span.rank').text.strip()),
            'count': int(ul.select_one('span[type=total]').text.strip()),
            'view': int(ul.select_one('span[type=view]').text.strip()),
            'like': int(ul.select_one('span[type=like]').text.strip()),
            'source': self.root_uri + f'/{ul.select_one("li.eye")["vid"]}/'
        } for ul in soup.select_one('.actor_box').select('ul')]

    def list_works(self, detailed=False) -> List[dict]:
        works = []
        for k in [1, 2]:
            for work in self.__list_records_by_page(lambda x: self.__parse_work_indices(f'/home/{k}_{x}.html')):
                if detailed:
                    try:
                        work.update(self.get_work_detail(work['wid']))
                    except NotFound:
                        work.update(self.get_work_detail(work['wid'], retry=True))
                works.append(work)
        return works

    def __parse_work_indices(self, path) -> Tuple[int, List[dict]]:
        soup = self.get_soup(path)
        actor_box = soup.select_one('.actor_box')
        if actor_box is None:
            return 0, []
        total = int(actor_box.select_one('h1 span').text.strip()[:-3])
        return total, [{
            'wid': ul.select_one('li.eye')['vid'],
            'serial_number': ul.select_one('a')['title'],
            'cover2': ul.select_one('img')['img'].replace(".jpgf.jpg", ".jpg"),
            'src_count': int(ul.select_one('span[type=total]').text.strip()),
            'view': int(ul.select_one('span[type=view]').text.strip()),
            'like': int(ul.select_one('span[type=like]').text.strip())
        } for ul in actor_box.select('ul')]

    def get_work_detail(self, wid, retry=False) -> dict:
        soup = self.get_soup(f'/{wid}/', cache=True, retry=retry)
        if soup.select_one('.site') is None:
            raise NotFound()
        serial_number = soup.select('.site a')[-1].text.strip()
        cover = soup.select_one('.left').select_one('img')['img']
        actors = []
        for li in soup.select_one('.right').select_one('.actor').select('li'):
            parts = li.select_one('a')['href'].strip('/').split('/')
            actors.append({'aid': int(parts[0]), 'name': parts[1]})
        online_links = [{
            'title': ul.select_one('.title').text.strip().replace('\n', ' '),
            'url': urljoin(self.root_uri, ul.select_one('a')['href'].replace('\n', ' ')),
            'image': ul.select_one('img')['img'],
            'time': ul.select_one('.time').text.strip(),
        } for ul in soup.select_one('.list_box').select('ul')]
        magnet_links = [{
            'title': ul.select_one('.title').text.strip().replace('\n', ' '),
            'url': ul.select_one('span').text.strip().replace('\n', ' '),
            'filesize': self.__parse_filesize(ul.select_one('.intro').text.strip().replace('\n', ' '))
        } for ul in soup.select_one('#magnet').select('ul')]
        return {
            'wid': wid,
            'serial_number': serial_number,
            'cover2': cover.replace(".jpgf.jpg", ".jpg"),
            'actors': actors,
            'online_links': online_links,
            'magnet_links': magnet_links,
        }

    def refactor_work(self, work: dict):
        work['serial_number'] = work['serial_number'].upper()
        work['actors'] = [x['name'] for x in work.get('actors', [])]
        root_resource = {'title': work['serial_number'] + ' - ' + self.name, 'url': self.root_uri + f'/{work["wid"]}/'}
        work['resources'] = [root_resource] + work.get('online_links', []) + work.get('magnet_links', [])

    def __parse_filesize(self, intro):
        matcher = self.intro_regexp.fullmatch(intro)
        if matcher is None:
            return None

        filesize = float(matcher.group(1).replace(",", "").replace(" ", "").replace("..", "."))
        if "GB" == matcher.group(4):
            filesize *= 1024 * 1024

        elif "MB" == matcher.group(4):
            filesize *= 1024
        filesize *= 1024
        return int(filesize)

    def __list_records_by_page(self, parse_func) -> List[dict]:
        page_index, stop, records = 1, 1, []
        while page_index <= stop:
            total, data = parse_func(page_index)
            records.extend(data)
            page_index += 1
            stop = math.ceil(total / 36)
        return records


if __name__ == '__main__':
    site = HuiAV()
    data_file = os.path.join('tmp', site.name + '.json')
    export.import_data(data_file, site.list_works, site.refactor_work)
    api = export.KingenWeb()
    export.export_data(data_file, lambda w: api.import_resources(w['serial_number'], w['resources']))
