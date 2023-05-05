#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Producers of WILL group.

@Author Kingen
"""
import re
from datetime import date, datetime
from queue import Queue
from typing import List, Dict

from urllib3.util import parse_url
from werkzeug.exceptions import NotFound

from common import OptionalValue
from internet.adult import start_date, SortedAdultSite, ActorSupplier


class WillProducer(SortedAdultSite, ActorSupplier):
    SN_REGEX = re.compile('([A-Z]+)(\\d{3})')
    FIGURE_REGEX = re.compile("B(--|\\d+)cm \\(([-A-Z])\\) W(--|\\d+)cm H(--|\\d+)cm")

    def list_actors(self) -> List[Dict]:
        actors = []
        for nav in self.get_soup('/actress').select_one('.p-tab').select('.dev_nav_item'):
            if '-current' in nav.get('class', ''):
                continue
            page, total = 1, 1
            while page <= total:
                soup = self.get_soup(f"{parse_url(nav['x-jump-url']).path}?page={page}")
                for card in soup.select('.c-card'):
                    aid = self.__parse_id(card.select_one('a')['href'])
                    actors.append(self.get_actor_detail(aid))
                page += 1
                pagination = soup.select_one('.swiper-pagination')
                if pagination is not None:
                    total = int(pagination.find_all(recursive=False)[-2].text.strip())
        return actors

    def get_actor_detail(self, aid) -> Dict:
        soup = self.get_soup(f'/actress/detail/{aid}', cache=True)
        headers = soup.select('.c-title-main > div')
        items = soup.select('.p-profile__info .table div.item')
        info = dict([(x.select_one('.th').text.strip(), x.select_one('.td').text.strip()) for x in items if x.select_one('.th') is not None])
        try:
            birthday = datetime.strptime(info.pop('誕生日'), '%Y年%m月%d日').date()
        except Exception:
            birthday = None
        return {
            'id': aid,
            'name': headers[0].text.strip(),
            'en_name': ' '.join([x.lower().capitalize() for x in headers[1].text.strip().split(' ')]),
            'avatar': OptionalValue(soup.select_one('.p-profile__imgArea img')).map(lambda x: x['data-src']).value,
            'birthday': birthday,
            'height': int(info.pop('身長')[:-2]) if '身長' in info else None,
            'measurements': info.pop('3サイズ')
        }

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        used_dates, unused_dates = set(), Queue()
        for item in self.get_soup('/works/date').select('.p-accordion a.item'):
            unused_dates.put(date.fromisoformat(item['href'].strip('/').split('/')[-1]))
        works, ids = [], {}
        while not unused_dates.empty():
            day = unused_dates.get()
            if day in used_dates:
                continue
            if day < since:
                continue
            used_dates.add(day)
            for idx in self.__list_work_indices_by_date(day):
                detail = self.get_work_detail(idx['id'])
                detail['cover'] = idx['cover']
                works.append(detail)

                match = self.SN_REGEX.fullmatch(idx['id'])
                prefix = match.group(1)
                num = int(match.group(2))
                last, notfound = ids.get(prefix, (0, 0))
                if num <= last:
                    continue
                for i in range(last + 1, num):
                    wid = "%s%03d" % (prefix, i)
                    try:
                        unused_dates.put(self.get_work_detail(wid)['release_date'])
                    except NotFound:
                        notfound += 1
                ids[prefix] = (num, notfound)
        works.sort(key=lambda x: x['release_date'], reverse=True)
        return works

    def __list_work_indices_by_date(self, day: date):
        soup = self.get_soup(f'/works/list/date/{day}', cache=True)
        cards = soup.select('.swiper-slide .c-card')
        return [{
            'id': self.__parse_id(card.select_one('a.img')['href']),
            'cover': card.select_one('img')['data-src'],
            'title': card.select_one('.text').text.strip()
        } for card in cards]

    def get_work_detail(self, wid) -> Dict:
        soup = self.get_soup(f'/works/detail/{wid}', cache=True)
        if soup.select_one('title').text.strip().startswith('404'):
            raise NotFound
        work_page = soup.select_one('.p-workPage')
        items = work_page.select('.p-workPage__table > div.item')
        info = dict([(x.select_one('.th').text.strip(), x.select_one('.td')) for x in items])
        actors = []
        if '女優' in info:
            for item in info.pop('女優').select('.item'):
                a = item.select_one('a')
                if a is None:
                    actors.append({'name': item.text.strip()})
                else:
                    actors.append({'id': int(self.__parse_id(a['href'])), 'name': item.text.strip()})
        release_date = date.fromisoformat(self.__parse_id(info.pop('発売日').select_one('a')['href']))
        return {
            'id': wid,
            'simple_title': soup.select('.c-bread .item')[-1].text.strip(),
            'title': work_page.select_one('h2').text.strip(),
            'images': [x['data-src'] for x in soup.select('.swiper-wrapper img')],
            'release_date': release_date,
            'director': [x.text.strip() for x in info.pop('監督').select('p')],
            'duration': OptionalValue(info.pop('収録時間').select_one('p')).map(lambda x: int(x.contents[-1].text.strip('分'))).value,
            'series': [x.text.strip() for x in info.pop('シリーズ').select('a')],
            'genres': [x.text.strip() for x in info.pop('ジャンル').select('a')],
            'description': work_page.select_one('.p-workPage__text').text.strip(),
            'trailer': OptionalValue(work_page.select_one('.p-workPage__side video')).map(lambda x: x['src']).value,
            'actors': actors
        }

    def __parse_id(self, href):
        return href.strip('/').split('/')[-1]


will_producers = [
    WillProducer('https://moodyz.com/top'),
    WillProducer('https://wanz-factory.com/top'),
    WillProducer('https://s1s1s1.com/top'),
    WillProducer('https://ideapocket.com/top'),
    WillProducer('https://kirakira-av.com/top'),
    WillProducer('https://av-e-body.com/top'),
    WillProducer('https://bi-av.com/top'),
    WillProducer('https://premium-beauty.com/top'),
    WillProducer('https://miman.jp/top'),
    WillProducer('https://madonna-av.com/top'),
    WillProducer('https://tameikegoro.jp/top'),
    WillProducer('https://fitch-av.com/top'),
    WillProducer('https://kawaiikawaii.jp/top'),
    WillProducer('https://befreebe.com/top'),
    WillProducer('https://muku.tv/top'),
    WillProducer('https://attackers.net/top'),
    WillProducer('https://mko-labo.net/top'),
    WillProducer('https://dasdas.jp/top'),
    WillProducer('https://mvg.jp/top'),
    WillProducer('https://av-opera.jp/top'),
    WillProducer('https://oppai-av.com/top'),
    WillProducer('https://v-av.com/top'),
    WillProducer('https://to-satsu.com/top'),
    WillProducer('https://bibian-av.com/top'),
    WillProducer('https://honnaka.jp/top'),
    WillProducer('https://rookie-av.jp/top'),
    WillProducer('https://nanpa-japan.jp/top'),
    WillProducer('https://hajimekikaku.com/top'),
    WillProducer('https://hhh-av.com/top')
]

# WillProducer('https://www.mousouzoku-av.com/top/')
# WillProducer('https://www.mutekimuteki.com/top/')
# WillProducer('https://manji-group.com/top/')
# WillProducer('http://www.hobicolle.com/')
