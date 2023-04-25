#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Producers of SOD group.

@Author Kingen
"""
from datetime import datetime, date
from typing import List, Dict

from scrapy.exceptions import NotSupported
from werkzeug.exceptions import NotFound

from common import OptionalValue
from internet.adult import JA_SYLLABARY, AdultSite, start_date


class SODPrime(AdultSite):
    def __init__(self):
        super().__init__('https://ec.sod.co.jp/prime/')
        self.get_soup('/prime/_ontime.php')

    def list_actors(self) -> List[Dict]:
        actors = []
        for kana in JA_SYLLABARY:
            page, total = 0, 1
            while page < total:
                soup = self.get_soup('/prime/videos/actress/keyword.php', params={'kana': kana, 'page': page})
                for box in soup.select('#actress_searchbox'):
                    img = box.select_one('img')
                    image = img['src']
                    actors.append({
                        'id': int(img['id']),
                        'name': box.select_one('p').text.strip(),
                        'avatar': None if 'placeholder' in image else image
                    })
                page += 1
                page_list = soup.select('#page_list a')
                total = int(page_list[-1].text.strip()) if len(page_list) > 0 else 0
        return actors

    def list_works(self) -> List[Dict]:
        works, page, over = [], 0, False
        while not over:
            soup = self.get_soup(f'/prime/videos/genre/', params={'sort': 2, 'page': page})
            for box in soup.select('#videos_s_mainbox'):
                wid = box.select_one('a')['href'].split('=')[-1]
                try:
                    work = self.get_work_detail(wid)
                except NotFound:
                    contents = box.select_one('.videis_s_star p').contents
                    work = {
                        'id': wid,
                        'cover': box.select_one('img')['src'],
                        'title': box.select_one('h2').text.strip(),
                        'description': box.select_one('p').text.strip(),
                        'release_date': datetime.strptime(contents[2].text.strip().replace(' ', '')[-11:], '%Y年%m月%d日').date(),
                        'producer': contents[-2].text.strip()[4:].strip()
                    }
                works.append(work)
            page += 1
            over |= page >= int(soup.select('#page_list a')[-1].text.strip())
        return works

    def get_work_detail(self, wid) -> Dict:
        # access the media with 'Referer' header
        soup = self.get_soup('/prime/videos/', params={'id': wid}, cache=True)
        head = soup.select_one('#videos_head')
        if head is None:
            raise NotFound
        video_soup = self.get_soup('/prime/videos/sample.php', params={'id': wid}, cache=True)
        infos = soup.select('#v_introduction tr')
        if len(infos) == 0:
            infos = video_soup.select('#v_introduction tr')
        return {
            'id': wid,
            'title': head.select('h1')[-1].text.strip(),
            'cover': head.select_one('.popup-image')['href'],
            'description': head.select_one('article').text.strip(),
            'serial_number': infos[0].select('td')[-1].text.strip(),
            'release_date': datetime.strptime(head.select_one('.videos_detail').contents[2].text.strip().replace(' ', '')[-11:], '%Y年%m月%d日').date(),
            'duration': OptionalValue(infos[5].select('td')[-1].text.strip()[:-1]).not_empty().map(int).value,
            'series': OptionalValue(infos[2].select_one('a')).map(lambda x: x.text.strip()).not_empty().value,
            'director': [x.text.strip() for x in infos[6].select('a')],
            'producer': OptionalValue(infos[7].select_one('a')).map(lambda x: x.text.strip()).not_empty().value,
            'genres': [x.text.strip() for x in infos[9].select('a')],
            'actors': [x.text.strip() for x in infos[4].select('a')],
            'images': [x['src'] for x in soup.select('.img-gallery img')],
            'trailer': video_soup.select_one('#moviebox source')['src']
        }

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        raise NotSupported
