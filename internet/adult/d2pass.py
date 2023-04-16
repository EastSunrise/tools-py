#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Producers of D2PASS group.

@Author Kingen
"""
import re
from datetime import date, datetime
from typing import List, Dict

import common
from internet.adult import AdultSite, JA_ALPHABET

log = common.create_logger(__name__)


class Caribbean(AdultSite):
    def __init__(self):
        super().__init__('https://www.caribbeancom.com/index2.htm', encoding='EUC-JP')

    def list_actors(self) -> List[Dict]:
        actors = []
        for alpha in JA_ALPHABET:
            soup = self.get_soup(f'/actress/{alpha}.html')
            for item in soup.select('.grid-item'):
                actors.append({
                    'id': int(item.select_one('.entry')['href'].split('/')[-2]),
                    'name': item.select_one('.meta-name').text.strip(),
                    'images': self.root_uri + item.select_one('img')['src'],
                    'source': self.root_uri + item.select_one('.entry')['href']
                })
        return actors

    def list_works(self) -> List[Dict]:
        return [self.get_work_detail(x['sn']) for x in self.list_work_indices()]

    def list_work_indices(self) -> List[Dict]:
        page, total = 1, 1
        indices = []
        while page <= total:
            soup = self.get_soup(f'/listpages/all{page}.htm')
            for item in soup.select('div.grid-item'):
                indices.append({
                    'sn': item.select_one('[itemprop="url"]')['href'].split('/')[-2],
                    'title': item.select_one('.meta-title').text.strip(),
                    'release_date': date.fromisoformat(item.select_one('.meta-data').text.strip()),
                    'image': item.select_one('.media-image')['src'],
                    'actors': [x.text.strip() for x in item.select('[itemprop="name"]')]
                })
            page += 1
            total = int(soup.select('div.pagination-page')[-1].text.strip())
        return indices

    def get_work_detail(self, sn):
        soup = self.get_soup(f'/moviepages/{sn}/index.html', cache=True)
        info = soup.select_one('div.movie-info')
        duration = info.select_one('[itemprop="duration"]')
        seconds = 0
        try:
            for v in re.split('[:：]', duration.text.strip()):
                seconds = seconds * 60 + int(v)
        except Exception as ex:
            log.error(ex)
            seconds = -1
        quality = soup.select_one(".quality").text.strip()
        quality = quality[:quality.index('p') + 1]
        gallery = soup.select_one('.gallery')
        return {
            'title': info.select_one('.heading').text.strip(),
            'serialNumber': sn,
            'cover': self.root_uri + f'/moviepages/{sn}/images/l_l.jpg',
            'duration': seconds if seconds > 0 else None,
            'releaseDate': datetime.strptime(info.select_one('[itemprop="datePublished"]').text.strip(), '%Y/%m/%d').date(),
            'producer': 'caribbean',
            'description': info.select_one('[itemprop="description"]').text.strip(),
            'genres': [x.text.strip() for x in info.select('.spec-item')],
            'trailer': f'https://smovie.caribbeancom.com/sample/movies/{sn}/{quality}.mp4',
            'images': [self.root_uri + x['src'] for x in gallery.select('.gallery-image')] if gallery else None,
            'source': self.root_uri + f'/moviepages/{sn}/index.html',
            'actors': [x.text.strip() for x in info.select('[itemprop="actor"]')]
        }
