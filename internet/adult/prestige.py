#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Producers of Prestige group.

@Author Kingen
"""
from collections import OrderedDict
from datetime import date
from typing import List, Dict

from scrapy.exceptions import NotSupported

from common import OptionalValue
from internet.adult import ActorSupplier, SortedAdultSite, start_date


class Prestige(SortedAdultSite, ActorSupplier):
    def __init__(self):
        super().__init__('https://prestige-av.com', name='prestige')

    def list_actors(self) -> List[Dict]:
        return self.get_json('/api/actress')['list']

    def refactor_actor(self, actor: dict) -> dict:
        return {
            'id': actor['uuid'],
            'name': actor['name'].replace(' ', ''),
            'avatar': OptionalValue(actor['media']).map(lambda x: self.media(x['path'])).get(),
            'source': self.root_uri + '/goods?actress=' + actor['name']
        }

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        works, now = OrderedDict(), date.today()
        for release in self.get_json('/api/sku/salesDate', params={'sort': 'desc'}):
            release_date = date.fromisoformat(release['salesStartAt'])
            if release_date > now:
                continue
            if release_date < since:
                break
            params = {
                'isEnabledQuery': 'true',
                'date[]': release['salesStartAt'],
                'from': 0, 'size': 100, 'order': 'new'
            }
            data = self.get_json('/api/search', params=params, cache=True)
            for doc in data['hits']['hits']:
                source = doc['_source']
                pid = source['productUuid']
                sn = source['deliveryItemId']
                if pid in works:
                    if sn in works[pid]['serial_number']:
                        works[pid]['serial_number'] = sn
                    continue
                works[pid] = {
                    'id': pid,
                    'serial_number': source['deliveryItemId'],
                    'title': source['productTitle'],
                    'description': source['productBody'],
                    'release_date': release_date,
                    'mgs_link': OptionalValue(source['productMgsLink']).map(lambda x: 'https://www.mgstage.com' + x).get(),
                    'cover': OptionalValue(source.get('productThumbnail')).map(lambda x: self.media(x['path'])).get(),
                    'trailer': OptionalValue(source.get('productMovie')).map(lambda x: self.media(x['path'])).get(),
                    'actors': [y for x in source['productActress'] for y in x['searchName'].split('/')],
                    'director': [x['searchName'] for x in source['productDirectors']],
                    'producer': [x['name'] for x in source['productMaker']],
                    'series': [x['name'] for x in source['productSeries']],
                    'genres': [x['name'] for x in source['productGenre']],
                    'source': self.root_uri + '/goods/' + pid
                }
        return list(works.values())

    def refactor_work(self, work: dict) -> dict:
        return work.copy()

    def get_work_detail(self, wid) -> Dict:
        raise NotSupported

    def media(self, path):
        return f'{self.root_uri}/api/media/{path}'
