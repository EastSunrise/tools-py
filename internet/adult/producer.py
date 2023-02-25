#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Sites of adult producers.

@Author Kingen
"""
from datetime import date, datetime
from typing import List, Dict

from urllib3.util import parse_url

from common import OptionalValue
from internet.adult import AdultSite


class Moodyz(AdultSite):
    def __init__(self):
        super().__init__('https://moodyz.com')

    def list_actor_indices(self) -> List[Dict]:
        head_soup = self._get_soup('/actress')
        indices = []
        for nav in head_soup.select_one('.p-tab').select('.dev_nav_item'):
            if '-current' in nav.get('class', ''):
                continue
            page, total_pages = 1, 1
            while page <= total_pages:
                soup = self._get_soup(f"{parse_url(nav['x-jump-url']).path}?page={page}")
                for card in soup.select('.c-card'):
                    indices.append({
                        'aid': int(self.__parse_id(card.select_one('a')['href'])),
                        'avatar': card.select_one('img')['data-src'],
                        'name': card.select_one('.name').text.strip(),
                        'en_name': card.select_one('.en').text.strip()
                    })
                page += 1
                pagination = soup.select_one('.swiper-pagination')
                if pagination is not None:
                    total_pages = int(pagination.find_all(recursive=False)[-2].text.strip())
        return indices

    def get_actor_detail(self, aid: int) -> Dict:
        soup = self._get_soup(f'/actress/detail/{aid}', cache=True)
        headers = soup.select('.c-title-main > div')
        info = dict([(x.select_one('.th').text.strip(), x.select_one('.td').text.strip()) for x in soup.select('.p-profile__info .table div.item') if x.select_one('.th') is not None])
        birthday = None
        if '誕生日' in info:
            try:
                birthday = datetime.strptime(info.pop('誕生日'), '%Y年%m月%d日').date()
            except ValueError:
                pass
        return {
            'aid': aid,
            'name': headers[0].text.strip(),
            'en_name': headers[1].text.strip(),
            'avatar': soup.select_one('.p-profile__imgArea img')['data-src'],
            'birthday': birthday,
            'height': int(info.pop('身長')[:-2]) if '身長' in info else None,
            'measurements': info.pop('3サイズ') if '3サイズ' in info else None
        }

    def list_work_indices(self) -> List[Dict]:
        header = self._get_soup('/works/date')
        indices = []
        for item in header.select('.p-accordion a.item'):
            path: str = parse_url(item['href'].strip()).path
            day = date.fromisoformat(self.__parse_id(path))
            soup = self._get_soup(path, cache=True)
            for card in soup.select('.swiper-slide .c-card'):
                indices.append({
                    'wid': self.__parse_id(card.select_one('a.img')['href']),
                    'cover': card.select_one('img')['data-src'],
                    'title': card.select_one('.text').text.strip(),
                    'release_date': day
                })
        return indices

    def get_work_detail(self, wid: int) -> Dict:
        soup = self._get_soup(f'/works/detail/{wid}', cache=True)
        work_page = soup.select_one('.p-workPage')
        rows = work_page.select('.p-workPage__table > div')
        return {
            'wid': wid,
            'serial_number': OptionalValue(rows[6].select_one('p')).map(lambda x: x.contents[-1].text.strip()).value,
            'simple_title': soup.select('.c-bread .item')[-1].text.strip(),
            'title': work_page.select_one('h2').text.strip(),
            'images': '#'.join([x['data-src'] for x in soup.select('.swiper-wrapper img')[1:-2]]),
            'release_date': date.fromisoformat(self.__parse_id(rows[1].select_one('a')['href'])),
            'director': '#'.join([x.text.strip() for x in rows[5].select('p')]),
            'duration': OptionalValue(rows[7].select_one('p')).map(lambda x: int(x.contents[-1].text.strip('分'))).value,
            'series': '#'.join([x.text.strip() for x in rows[2].select('a')]),
            'tags': '#'.join([x.text.strip() for x in rows[4].select('a')]),
            'description': work_page.select_one('.p-workPage__text').text.strip(),
            'video': OptionalValue(work_page.select_one('.p-workPage__side video')).map(lambda x: x['src']).value,
            'actors': [{'aid': int(self.__parse_id(x['href'])), 'name': x.text.strip()} for x in rows[0].select('a')]
        }

    def __parse_id(self, href):
        return href.strip('/').split('/')[-1]
