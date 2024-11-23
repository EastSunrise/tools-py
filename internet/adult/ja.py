#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Japanese adult producers.

@Author Kingen
"""
import argparse
import os
import re
import time
from abc import ABC
from collections import OrderedDict
from datetime import date, datetime, timedelta
from queue import Queue
from typing import List
from urllib.parse import urlparse, parse_qs, unquote, urljoin

import execjs
from bs4 import BeautifulSoup
from requests import HTTPError
from scrapy.exceptions import NotSupported
from urllib3.util import parse_url
from werkzeug.exceptions import NotFound, BadGateway

import common
from common import OptionalValue, YearMonth
from internet import normalize_str, DuplicateError
from internet.adult import ActorSite, AdultSite, OrderedAdultSite, MonthlyAdultSite, export

log = common.get_logger()

ja_alphabet = ['a', 'k', 's', 't', 'n', 'h', 'm', 'y', 'r', 'w']
ja_syllabary = [
    'あ', 'い', 'う', 'え', 'お',
    'か', 'き', 'く', 'け', 'こ',
    'さ', 'し', 'す', 'せ', 'そ',
    'た', 'ち', 'つ', 'て', 'と',
    'な', 'に', 'ぬ', 'ね', 'の',
    'は', 'ひ', 'ふ', 'へ', 'ほ',
    'ま', 'み', 'む', 'め', 'も',
    'や', 'ゆ', 'よ',
    'ら', 'り', 'る', 'れ', 'ろ',
    'わ', 'を'
]


def format_en_name(en_name, reverse=False):
    parts = [x.lower().capitalize() for x in re.split('\\s', en_name.strip()) if x.strip() != '']
    if reverse:
        parts.reverse()
    return ' '.join(parts)


class JaActorSite(ActorSite, ABC):
    def refactor_actor(self, actor: dict) -> None:
        super().refactor_actor(actor)
        actor['region'] = actor.get('region') or 'Japan'
        actor['ethnicity'] = actor.get('ethnicity') or 'Yamato'


class BaseWillProducer(OrderedAdultSite):
    sn_regexp = re.compile('([A-Z]+)(\\d{3})')

    def list_works_between(self, start: date, stop: date) -> List[dict]:
        available_dates = []
        for item in self.get_soup('/works/date').select('.p-accordion a.item'):
            available_dates.append(date.fromisoformat(item['href'].strip('/').split('/')[-1]))
        start_date = min(available_dates)
        if stop <= start_date:
            raise ValueError('cannot retrieve works too early')
        if start >= start_date:
            works = self.__list_works_among(available_dates, start, stop)
        else:
            works = self.__list_works_all(available_dates, start, stop)
        return sorted(works, key=lambda x: x['releaseDate'], reverse=True)

    def __list_works_among(self, dates, start, stop):
        works = []
        for day in dates:
            if start <= day < stop:
                for idx in self.__list_work_indices_by_date(day):
                    try:
                        work = self.get_work_detail(idx['wid'])
                    except NotFound:
                        work = self.get_work_detail(idx['wid'], retry=True)
                    works.append({**idx, **work})
        return works

    def __list_works_all(self, dates, start, stop):
        used, pending, works = set(), Queue(), []
        for day in dates:
            pending.put(day)
        prefix_ids: dict = {}
        while not pending.empty():
            day = pending.get()
            if day in used or day < start or day >= stop:
                continue
            used.add(day)
            for idx in self.__list_work_indices_by_date(day):
                try:
                    work = self.get_work_detail(idx['wid'])
                except NotFound:
                    work = self.get_work_detail(idx['wid'], retry=True)
                work['cover'] = idx['cover']
                works.append(work)

                match = self.sn_regexp.fullmatch(idx['wid'])
                prefix, num = match.group(1), int(match.group(2))
                last, notfound = prefix_ids.get(prefix, (0, 0))
                if num <= last:
                    continue
                for i in range(last + 1, num):
                    try:
                        pending.put(self.get_work_detail("%s%03d" % (prefix, i))['releaseDate'])
                    except NotFound:
                        notfound += 1
                prefix_ids[prefix] = (num, notfound)
        return works

    def __list_work_indices_by_date(self, day: date):
        soup = self.get_soup(f'/works/list/date/{day}', cache=True)
        cards = soup.select('.swiper-slide .c-card')
        return [{
            'wid': card.select_one('a.img')['href'].strip('/').split('/')[-1],
            'cover': card.select_one('img')['data-src'],
            'title': card.select_one('.text').text.strip()
        } for card in cards]

    def get_work_detail(self, wid, retry=False) -> dict:
        soup = self.get_soup(f'/works/detail/{wid}', cache=True, retry=retry)
        if soup.select_one('title').text.strip().startswith('404'):
            raise NotFound
        work_page = soup.select_one('.p-workPage')
        images = [x.select_one('img') for x in soup.select('.swiper-slide') if
                  'swiper-slide-duplicate' not in x.get_attribute_list('class', [])]
        items = work_page.select('.p-workPage__table > div.item')
        info = dict([(x.select_one('.th').text.strip(), x) for x in items])
        return {
            'wid': wid,
            'simpleTitle': soup.select('.c-bread .item')[-1].text.strip(),
            'images': [x.get('data-src', x.get('src')) for x in images],
            'title': work_page.select_one('h2').text.strip(),
            'description': work_page.select_one('.p-workPage__text').text.strip(),
            'actors': OptionalValue(info.get('女優')).map(
                lambda v: [normalize_str(x.text.strip()) for x in v.select('.item')]).get(),
            'releaseDate': date.fromisoformat(info.pop('発売日').select_one('a')['href'].strip('/').split('/')[-1]),
            'series': [x.text.strip() for x in info.get('シリーズ').select('.item')],
            'genres': [x.text.strip() for x in info.get('ジャンル').select('.item')],
            'directors': [y for y in [x.text.strip() for x in info.get('監督').select('.item')] if y != '---'],
            'duration': OptionalValue(info.pop('収録時間').select_one('p')).map(lambda x: x.contents[-1].text.strip()).get(),
            'trailer': OptionalValue(work_page.select_one('.p-workPage__side video')).map(lambda x: x['src']).get(),
            'source': [self.root_uri + f'/works/detail/{wid}', work_page.select('.p-workPage__side a')[-1]['href']]
        }

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name
        match = self.sn_regexp.fullmatch(work['wid'])
        work['serialNumber'] = match.group(1) + '-' + match.group(2)
        if len(work['images']) > 0:
            work['cover2'] = work['images'][0]


class WillProducer(BaseWillProducer, JaActorSite):
    measurements_regexp = re.compile('B(\\d{2,3}|--)cm \\(([-A-P])\\) W(\\d{2,3}|--)cm H(\\d{2,3}|--)cm')
    birthday_regexp = re.compile('\\d{4}年\\d{1,2}月\\d{1,2}日')

    def list_actors(self) -> List[dict]:
        actors = []
        for nav in self.get_soup('/actress').select_one('.p-tab').select('.dev_nav_item'):
            if '-current' in nav.get('class', ''):
                continue
            page, total = 1, 1
            while page <= total:
                soup = self.get_soup(f"{parse_url(nav['x-jump-url']).path}?page={page}")
                for card in soup.select('.c-card'):
                    aid = card.select_one('a')['href'].strip('/').split('/')[-1]
                    actors.append(self.get_actor_detail(aid))
                page += 1
                pagination = soup.select_one('.swiper-pagination')
                if pagination is not None:
                    total = int(pagination.find_all(recursive=False)[-2].text.strip())
        return actors

    def get_actor_detail(self, aid) -> dict:
        soup = self.get_soup(f'/actress/detail/{aid}', cache=True)
        headers = soup.select('.c-title-main > div')
        items = soup.select('.p-profile__info .table div.item')
        info = dict(
            [(x.select_one('.th').text.strip(), x.select_one('.td').text.strip()) for x in items if
             x.select_one('.th') is not None])
        birthday_op = OptionalValue(info.get('誕生日')).map(lambda x: self.birthday_regexp.fullmatch(x)).map(
            lambda x: x.group())
        return {
            'aid': aid,
            'name': normalize_str(headers[0].text.strip()).lower().capitalize(),
            'enName': ' '.join([x.strip().lower().capitalize() for x in re.split('[\\s　]', headers[1].text.strip()) if
                                x.strip() != '']),
            'image': OptionalValue(soup.select_one('.p-profile__imgArea img')).map(lambda x: x['data-src']).get(),
            'birthday': birthday_op.map(lambda x: datetime.strptime(x, '%Y年%m月%d日').date()).get(),
            'height': info.get('身長'),
            'measurements': OptionalValue(info.get('3サイズ')).map(lambda x: self.measurements_regexp.fullmatch(x)).map(
                lambda x: x.group()).get(),
            'websites': [x['href'] for x in soup.select('.p-profile__info .sns a')],
            'source': self.root_uri + f'/actress/detail/{aid}'
        }

    def refactor_actor(self, actor: dict) -> None:
        super().refactor_actor(actor)
        actor['height'] = OptionalValue(actor.get('height')).map(lambda x: int(x.rstrip('cm'))).get()
        measurements = actor['measurements']
        if measurements is not None:
            match = self.measurements_regexp.fullmatch(measurements)
            actor['measurements'] = f'B{match.group(1)}({match.group(2)})/W{match.group(3)}/H{match.group(4)}'


will_producers = [
    WillProducer('https://moodyz.com/top', name='Moodyz'),
    WillProducer('https://s1s1s1.com/top', name='S1'),
    WillProducer('https://ideapocket.com/top', name='IdeaPocket'),
    WillProducer('https://av-e-body.com/top', name='E-BODY'),
    WillProducer('https://mko-labo.net/top', name='えむっ娘ラボ'),
    WillProducer('https://miman.jp/top', name='未満'),
    WillProducer('https://muku.tv/top', name='無垢'),
    WillProducer('https://honnaka.jp/top', name='本中'),
    WillProducer('https://premium-beauty.com/top', name='Premium'),
    WillProducer('https://kirakira-av.com/top', name='kira☆kira'),
    WillProducer('https://oppai-av.com/top', name='OPPAI'),
    WillProducer('https://bibian-av.com/top', name='ビビアン'),
    WillProducer('https://madonna-av.com/top', name='Madonna'),
    BaseWillProducer('https://hhh-av.com/top', name='HHH'),
    WillProducer('https://attackers.net/top', name='Attackers'),
    WillProducer('https://rookie-av.jp/top', 'Rookie'),
    WillProducer('https://av-opera.jp/top', name='OPERA'),
    WillProducer('https://dasdas.jp/top', name='Das!'),
    WillProducer('https://wanz-factory.com/top', name='Wanz Factory'),
    WillProducer('https://befreebe.com/top', name='BeFree'),
    WillProducer('https://kawaiikawaii.jp/top', name='kawaii*'),
    WillProducer('https://bi-av.com/top', name='痴女ヘブン'),
    WillProducer('https://tameikegoro.jp/top', name='溜池ゴロー'),
    WillProducer('https://fitch-av.com/top', name='Fitch'),
    BaseWillProducer('https://mvg.jp/top', name='MVG'),
    BaseWillProducer('https://v-av.com/top', 'V（ヴィ）'),
    BaseWillProducer('https://to-satsu.com/top', name='変態紳士倶楽部'),
    BaseWillProducer('https://nanpa-japan.jp/top', name='ナンパJAPAN'),
    BaseWillProducer('https://fairway-av.com/top', name='FAIR&WAY'),
    BaseWillProducer('https://hajimekikaku.com/top', name='はじめ企画'),
]


class Caribbean(OrderedAdultSite, JaActorSite):

    def __init__(self):
        super().__init__('https://www.caribbeancom.com/index2.htm', name='カリビアンコム', encoding='EUC-JP')

    def list_actors(self) -> List[dict]:
        actors = []
        for alpha in ja_alphabet:
            for item in self.get_soup(f'/actress/{alpha}.html').select('.grid-item'):
                aid = item.select_one('.entry')['href'].split('/')[-2]
                actors.append({
                    'aid': aid,
                    'name': item.select_one('.meta-name').text.strip(),
                    'image': self.root_uri + item.select_one('img')['src'],
                    'source': self.root_uri + f'/search_act/{aid}/1.html'
                })
        return actors

    def list_works_between(self, start: date, stop: date) -> List[dict]:
        works, page = [], 1
        while True:
            soup = self.get_soup(f'/listpages/all{page}.htm')
            for item in soup.select('div.grid-item'):
                release_date = date.fromisoformat(item.select_one('.meta-data').text.strip())
                if release_date >= stop:
                    continue
                if release_date < start:
                    return works
                wid = item.select_one('[itemprop="url"]')['href'].split('/')[-2]
                works.append(self.get_work_detail(wid))
            if 'is-disabled' in soup.select('.pagination-item')[-1].get_attribute_list('class', []):
                return works
            page += 1

    def get_work_detail(self, wid) -> dict:
        soup = self.get_soup(f'/moviepages/{wid}/index.html', cache=True)
        info = soup.select_one('div.movie-info')
        quality = soup.select_one(".quality").text.strip()
        quality = quality[:quality.index('p') + 1]
        gallery = soup.select_one('.gallery')
        duration_op = OptionalValue(info.select_one('[itemprop="duration"]')).map(lambda x: x.text.strip().strip(':'))
        return {
            'wid': wid,
            'cover2': self.root_uri + f'/moviepages/{wid}/images/l_l.jpg',
            'trailer': f'https://smovie.caribbeancom.com/sample/movies/{wid}/{quality}.mp4',
            'title': info.select_one('.heading').text.strip(),
            'description': info.select_one('[itemprop="description"]').text.strip(),
            'actors': [x.text.strip() for x in info.select('[itemprop="actor"]')],
            'releaseDate': datetime.strptime(info.select_one('[itemprop="datePublished"]').text.strip(),
                                             '%Y/%m/%d').date(),
            'duration': duration_op.map(lambda x: x.replace(' ', '').replace('：', ":").replace(';', ':')).get(),
            'genres': [x.text.strip() for x in info.select('.spec-item')],
            'images': [self.root_uri + x['src'].replace('/s/', '/l/') for x in
                       gallery.select('.gallery-image')] if gallery else None,
            'source': self.root_uri + f'/moviepages/{wid}/index.html'
        }

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name
        work['serialNumber'] = work['wid'].upper()
        work['actors'] = [x for x in work['actors'] if x != '---']


class OnePondo(OrderedAdultSite, JaActorSite):
    def __init__(self):
        super().__init__('https://www.1pondo.tv/', name='一本道')

    def list_actors(self) -> List[dict]:
        return [a for g in self.get_json('/dyn/phpauto/actresses.json').values() for arr in g.values() for a in arr]

    def refactor_actor(self, actor: dict) -> None:
        super().refactor_actor(actor)
        actor['source'] = self.root_uri + f'/search/?a={actor["id"]}'

    def list_works_between(self, start: date, stop: date) -> List[dict]:
        works, index = [], 0
        while True:
            data = self.get_json(f'/dyn/phpauto/movie_lists/list_newest_{index}.json')
            for row in data['Rows']:
                row['releaseDate'] = date.fromisoformat(row['Release'])
                if row['releaseDate'] >= stop:
                    continue
                if row['releaseDate'] < start:
                    return works
                works.append(row)
            index += data['SplitSize']
            if index >= data['TotalRows']:
                return works

    def get_work_detail(self, wid) -> dict:
        return self.get_json(f'/dyn/phpauto/movie_details/movie_id/{wid}.json', cache=True)

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name
        work['title'] = work['Title'].strip()
        work['serialNumber'] = work['MovieID'].upper()
        work['year'] = work['Year']
        work['cover2'] = self.root_uri + urlparse(work['ThumbUltra']).path
        work['duration'] = work['Duration']
        work['releaseDate'] = work['Release']
        work['series'] = OptionalValue(work['Series']).strip().get()
        work['description'] = work['Desc'].strip()
        work['genres'] = work['UCNAME']
        work['trailer'] = sorted(work['SampleFiles'], key=lambda x: x['FileSize'])[-1][
            'URL'] if 'SampleFiles' in work else None
        if work['Gallery']:
            try:
                images = self.get_json(f'/dyn/dla/json/movie_gallery/{work["MovieID"]}.json', cache=True)['Rows']
                work['images'] = [self.root_uri + '/dyn/dla/images/' + x['Img'] for x in images]
            except HTTPError:
                pass
        work['source'] = self.root_uri + f'/movies/{work["MovieID"]}/'
        work['actors'] = [x.strip() for x in work['ActressesJa'] if x != '---']


class Kin8tengoku(OrderedAdultSite):
    def __init__(self):
        super().__init__('https://www.kin8tengoku.com/index.html', name='金髪天國', encoding='EUC-JP')

    def list_works_between(self, start: date, stop: date) -> List[dict]:
        works, page = [], 1
        while True:
            soup = self.get_soup(f'/listpages/all_{page}.htm')
            for item in soup.select('.movie_list'):
                wid = item.select_one('a')['href'].split('/')[-2]
                work = self.get_work_detail(wid)
                if work['releaseDate'] >= stop:
                    continue
                if work['releaseDate'] < start:
                    return works
                works.append(work)
            page += 1
            last = soup.select('.pagenation li')[-1]
            if 'next' not in last.get_attribute_list('class', []):
                return works

    def get_work_detail(self, wid) -> dict:
        soup = self.get_soup(f'/moviepages/{wid}/index.html', cache=True)
        if int(wid) >= 1155:
            trailer = f'https://smovie.kin8tengoku.com/{wid}/pht/sample.mp4'
        else:
            trailer = f'https://smovie.kin8tengoku.com/sample_mobile_template/{wid}/hls-1800k.mp4'
        infos = soup.select('#main table tr')
        return {
            'wid': wid,
            'title': OptionalValue(soup.select_one('.sub_title')).get(soup.select_one('.sub_title_vip')).text.strip(),
            'cover2': self.root_uri + f'/{wid}/pht/1.jpg',
            'trailer': trailer,
            'actors': [x.text.strip() for x in infos[0].select('a')],
            'genres': [x.text.strip() for x in infos[1].select('a')],
            'duration': OptionalValue(infos[2].select('td')[-1].text.strip()).not_blank().get(),
            'releaseDate': date.fromisoformat(infos[3].select('td')[-1].text.strip()),
            'description': infos[4].text.strip(),
            'images': ['https:' + x['src'].replace('.jpg', '_lg.jpg') for x in soup.select('#gallery img')],
            'source': self.root_uri + f'/moviepages/{wid}/index.html'
        }

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name
        work['serialNumber'] = 'KIN8-' + work['wid']


d2pass_producers = [Caribbean(), OnePondo(), Kin8tengoku()]


class FalenoProducer(AdultSite):
    sn_regexp = re.compile('([a-z]+)-?(\\d{3}[a-z]?)')

    def __init__(self, home, name, prefix=''):
        super().__init__(home, name)
        self.__prefix = prefix

    def list_works(self) -> List[dict]:
        works, page, today = [], 1, date.today()
        while True:
            soup = self.get_soup(f'{self.__prefix}/work/{"" if page == 1 else f"page/{page}/"}')
            for item in soup.select('.back02 li'):
                wid = item.select_one('a')['href'].strip('/').split('/')[-1]
                try:
                    release_date = datetime.strptime(item.select('.view_timer')[-1]['data-start-date'],
                                                     '%Y/%m/%d %H:%M').date()
                    if release_date >= today:
                        continue
                except:
                    log.warn('cannot get release date of %s from %s', wid, self.name)
                    pass
                works.append({
                    'cover': item.select_one('img')['src'].split('?')[0],
                    **self.get_work_detail(wid)
                })
            if soup.select_one('.nextpostslink') is None:
                return works
            page += 1

    def get_work_detail(self, wid) -> dict:
        soup = self.get_soup(f'{self.__prefix}/works/{wid}/', cache=True)
        infos = soup.select('.box_works01_list p')
        sources = []
        for tag in soup.select('#bottom-bar a'):
            if tag.text.strip() == 'FANZAで購入' and 'href' in tag:
                sources.append(tag['href'])
                break
        return {
            'wid': wid,
            'title': normalize_str(soup.select_one('h1').text.strip()),
            'cover2': soup.select_one('.box_works01_img img')['src'].split('?')[0],
            'trailer': OptionalValue(soup.select_one('.box_works01_img .pop_sample')).map(lambda x: x['href']).get(),
            'images': [x['href'] for x in soup.select('.box_works01_ga .pop_img')],
            'description': normalize_str(soup.select_one('.box_works01_text').text.strip()),
            'actors': re.split('[ /　]', infos[0].text.strip()),
            'duration': OptionalValue(infos[1].text.strip()).not_blank().get(),
            'releaseDate': datetime.strptime(
                OptionalValue(infos[-1].text.strip('-')).not_blank().get(infos[-2].text.strip()), '%Y/%m/%d').date(),
            'source': [self.root_uri + self.__prefix + f'/works/{wid}/'] + sources
        }

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name
        match = self.sn_regexp.fullmatch(work['wid'])
        work['serialNumber'] = (match.group(1) + '-' + match.group(2)).upper()


class SODPrime(OrderedAdultSite, JaActorSite):
    NO_IMAGE = '/prime/videos/thumbnail/now'

    def __init__(self):
        super().__init__('https://ec.sod.co.jp/prime/', name='sod', headers={'Referer': 'https://ec.sod.co.jp/prime/'})
        self.__timestamp = None

    def _do_get(self, path, params=None):
        current = time.time()
        if self.__timestamp is None or current - self.__timestamp > 1800:
            self.__timestamp = current
            super()._do_get('/prime/_ontime.php')
        return super()._do_get(path, params)

    def list_actors(self) -> List[dict]:
        actors = []
        for kana in ja_syllabary:
            page, total = 0, 1
            while page < total:
                soup = self.get_soup('/prime/videos/actress/keyword.php', params={'kana': kana, 'page': page})
                for box in soup.select('#actress_searchbox'):
                    aid = box.select_one('img')['id']
                    actors.append({
                        'aid': aid,
                        'name': format_en_name(box.select_one('p').text.strip()),
                        'source': self.root_uri + '/prime/videos/genre/?actress[]=' + aid
                    })
                page += 1
                page_list = soup.select('#page_list a')
                total = int(page_list[-1].text.strip()) if len(page_list) > 0 else 0
        return actors

    def list_works_between(self, start: date, stop: date) -> List[dict]:
        works, page = [], 0
        while True:
            soup = self.get_soup(f'/prime/videos/genre/', params={'sort': 3, 'page': page})
            for box in soup.select('#videos_s_mainbox'):
                contents = box.select_one('.videis_s_star p').contents
                release_date = datetime.strptime(contents[2].text.strip().replace(' ', '')[-11:], '%Y年%m月%d日').date()
                if release_date >= stop:
                    continue
                if release_date < start:
                    return works
                wid = box.select_one('a')['href'].split('=')[-1]
                work = {
                    'wid': wid,
                    'serialNumber': wid,
                    'cover': box.select_one('img')['src'],
                    'releaseDate': release_date,
                    'title': box.select_one('h2').text.strip(),
                    'description': box.select_one('p').text.strip(),
                    'producer': contents[-2].text.strip()[4:].strip(),
                    'source': self.root_uri + '/prime/videos/?id=' + wid,
                }
                try:
                    work.update(self.get_work_detail(wid))
                except NotFound:
                    pass
                works.append(work)
            page += 1
            if page >= int(soup.select('#page_list a')[-1].text.strip()):
                return works

    def get_work_detail(self, wid) -> dict:
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
            'wid': wid,
            'title': head.select('h1')[-1].text.strip(),
            'cover': OptionalValue(head.select_one('.popup-image img')['src']).filter(
                lambda x: not x.startswith(self.NO_IMAGE)).get(),
            'cover2': OptionalValue(head.select_one('.popup-image')['href']).filter(
                lambda x: not x.startswith(self.NO_IMAGE)).get(),
            'description': head.select_one('article').text.strip(),
            'images': [x['src'] for x in soup.select('.img-gallery img') if not x['src'].startswith(self.NO_IMAGE)],
            'serialNumber': infos[0].select('td')[-1].text.strip(),
            'releaseDate': datetime.strptime(
                head.select_one('.videos_detail').contents[2].text.strip().replace(' ', '')[-11:],
                '%Y年%m月%d日').date(),
            'series': [x.text.strip() for x in infos[2].select('a')],
            'actors': [x.text.strip() for x in infos[4].select('a')],
            'duration': OptionalValue(infos[5].select('td')[-1].text.strip()).not_blank().filter(
                lambda x: x not in ['分', '0分']).get(),
            'directors': [x.text.strip() for x in infos[6].select('a')],
            'producer': [x.text.strip() for x in infos[7].select('a')],
            'genres': [x.text.strip() for x in infos[9].select('a')],
            'trailer': video_soup.select_one('#moviebox source')['src'],
            'source': self.root_uri + '/prime/videos/?id=' + wid
        }

    def refactor_work(self, work: dict) -> None:
        if len(work['producer']) == 0:
            work['producer'] = None
        else:
            work['producer'] = work['producer'][0]


class Prestige(OrderedAdultSite, JaActorSite):
    nuxt_regexp = re.compile('window.__NUXT__=(.*);')
    js_ctx = execjs.compile('')
    prefixes = ['GOOE', 'PTKT', 'CTKT', 'STKT', 'TKT']

    def __init__(self):
        super().__init__('https://prestige-av.com', name='Prestige', headers={'Cookie': '__cred__=; __age_auth__=true'})

    def list_actors(self) -> List[dict]:
        return self.get_json('/api/actress')['list']

    def refactor_actor(self, actor: dict) -> None:
        super().refactor_actor(actor)
        actor['source'] = self.root_uri + '/goods?actress=' + actor['name']
        actor['name'] = actor['name'].replace(' ', '')
        actor['enName'] = OptionalValue(actor['nameRoma']).not_blank().map(lambda x: format_en_name(x, True)).get()
        actor['image'] = OptionalValue(actor['media']).map(lambda x: self.media(x['path'])).get()

    def list_works_between(self, start: date, stop: date) -> List[dict]:
        works = OrderedDict()
        for release in self.get_json('/api/sku/salesDate', params={'sort': 'desc'}):
            release_date = date.fromisoformat(release['salesStartAt'])
            if release_date >= stop:
                continue
            if release_date < start:
                break
            params = {
                'isEnabledQuery': 'true',
                'date[]': release['salesStartAt'],
                'from': 0, 'size': 100, 'order': 'new'
            }
            data = self.get_json('/api/search', params=params, cache=date.today() - release_date >= timedelta(days=7))
            for doc in data['hits']['hits']:
                source: dict = doc['_source']
                source['releaseDate'] = release_date
                sn = self._format_sn(source['deliveryItemId'])
                if sn not in works:
                    # this is blocked
                    # try:
                    #     source.update(self.get_work_detail(source['productUuid']))
                    # except (NotFound, RequestException) as ex:
                    #     log.warning(f'Cannot to get work detail of {sn} from {self.name}: {ex}')
                    #     continue
                    works[sn] = source
        return list(works.values())

    def get_work_detail(self, wid) -> dict:
        soup = self.get_soup(f'/goods/{wid}', cache=True)
        js_func = self.nuxt_regexp.fullmatch(soup.select_one('body script').text).group(1)
        nuxt = self.js_ctx.eval(js_func)
        for data in nuxt['fetch'].values():
            if 'product' in data:
                return data['product']
        raise NotFound()

    def refactor_work(self, work: dict) -> None:
        work['serialNumber'] = self._format_sn(work['deliveryItemId'])
        work['title'] = work['title'].strip()
        work['cover'] = OptionalValue(work.get('productThumbnail')).map(lambda x: self.media(x['path'])).get()
        work['cover2'] = OptionalValue(work.get('packageImage')).map(lambda x: self.media(x['path'])).get()
        work['duration'] = OptionalValue(work.get('playTime')).filter(lambda x: x != 0).map(lambda x: x * 60).get()
        work['directors'] = [x['name'].strip() for x in work['productDirectors']]
        work['producer'] = work['productMaker'][0]['name']
        work['series'] = [x['name'].strip() for x in work['productSeries']]
        work['description'] = OptionalValue(work['productBody']).strip().not_blank().get()
        work['genres'] = [x['name'].strip() for x in work['productGenre']]
        work['trailer'] = OptionalValue(work.get('productMovie')).map(lambda x: self.media(x['path'])).get()
        work['images'] = [self.media(x['path']) for x in work.get('media', [])]
        work['source'] = self.root_uri + '/goods/' + work['uuid']
        work['actors'] = [y.replace(' ', '') for x in work['productActress'] for y in x['name'].strip('/').split('/')]

    def media(self, path):
        return f'{self.root_uri}/api/media/{path}'

    def _format_sn(self, sn):
        for prefix in self.prefixes:
            if sn.startswith(prefix):
                return sn[len(prefix):]
        return sn


class Venus(MonthlyAdultSite):
    def __init__(self):
        super().__init__('https://venus-av.com/', YearMonth(2009, 4), name='VENUS')

    def _list_monthly(self, ym: YearMonth) -> List[dict]:
        soup = self.get_soup('/products/%04d/%02d/' % (ym.year, ym.month), cache=ym < YearMonth.now())
        return [{'wid': unquote(li.select_one('a')['href'].split('/')[-2])} for li in
                soup.select('.topNewreleaseList li')]

    def get_work_detail(self, wid) -> dict:
        soup = self.get_soup(f'/products/{wid}/', cache=True)
        main = soup.select_one('#main')
        infos = main.select('.productsDataDetail dd')
        match = re.fullmatch('(\\d{4})[年月](\\d{1,2})月(\\d{1,2})日', infos[4].text.strip())
        return {
            'wid': wid,
            'title': main.select_one('h1').text.strip(),
            'cover2': self.root_uri + main.select_one('.productsImg img')['src'],
            'description': infos[0].text.strip(),
            'actors': infos[1].text.strip().strip('/').split('/'),
            'serialNumber': OptionalValue(infos[2].text.strip()).not_blank().get(),
            'genres': infos[3].text.strip().split('/'),
            'releaseDate': date(int(match.group(1)), int(match.group(2)), int(match.group(3))),
            'source': self.root_uri + f'/products/{wid}/'
        }


class Indies(MonthlyAdultSite, JaActorSite):
    measurements_regexp = re.compile('B:(\\d{2,3})?cm\\(([A-O])?カップ\\) / W: (\\d{2})?cm / H:(\\d{2,3})?cm')

    def __init__(self):
        super().__init__('https://www.indies-av.co.jp/', start_month=YearMonth(2007, 6), name='桃太郎映像出版')

    def list_actors(self) -> List[dict]:
        actors = []
        for option in self.get_soup('/actpage/').select('#toprelease_dd')[1].select('option')[1:]:
            prefix, page = option['value'], 1
            while True:
                soup = self.get_soup(f'{prefix}/page/{page}/')
                for li in soup.select('.inner .package'):
                    aid = li.select_one('a')['href'].strip('/').split('/')[-1]
                    actor = {
                        'aid': aid,
                        'name': li.select_one('p').text.strip(),
                        'image': li.select_one('img')['src'],
                        'source': self.root_uri + f'{prefix}/page/{page}/'
                    }
                    try:
                        actor.update(self.get_actor_detail(aid))
                    except BadGateway:
                        pass
                    actors.append(actor)
                pages = soup.select('.page-item a')
                if len(pages) == 0 or 'current' in pages[-1].get_attribute_list('class', []):
                    break
                page += 1
        return actors

    def get_actor_detail(self, aid) -> dict:
        soup = self.get_soup(f'/actress/{aid}/', cache=True)
        if soup.select_one('title').text.strip().startswith('502'):
            raise BadGateway()
        section = soup.select_one('section.inner')
        infos = dict(
            [(x.select('div')[0].text.strip(), x.select('div')[-1]) for x in section.select('[itemscope] >li')])
        return {
            'aid': aid,
            'image': section.select_one('.img_popup')['href'],
            'name': infos.get('女優名').text.strip(),
            'websites': [x['href'] for x in infos.get('ソーシャル').select('a')],
            'birthday': OptionalValue(infos.get('生年月日')).map(lambda x: x.text.strip()).get(),
            'height': OptionalValue(infos.get('身長').text.strip()).filter(lambda x: x != 'cm').get(),
            'measurements': infos.get('スリーサイズ').text.strip(),
            'source': self.root_uri + f'/actress/{aid}/'
        }

    def refactor_actor(self, actor: dict) -> None:
        super().refactor_actor(actor)
        actor['birthday'] = OptionalValue(actor.get('birthday')).map(
            lambda x: datetime.strptime(x, '%Y年%m月%d日').date()).get()
        actor['height'] = OptionalValue(actor.get('height')).map(lambda x: int(x.rstrip('cm'))).get()
        actor['measurements'] = OptionalValue(actor.get('measurements')).map(
            lambda x: self.measurements_regexp.fullmatch(x)) \
            .map(
            lambda x: f'B{x.group(1) or "--"}({x.group(2) or "-"})/W{x.group(3) or "--"}/H{x.group(4) or "--"}').get()

    def _list_monthly(self, ym: YearMonth) -> List[dict]:
        indices = []
        soup = self.get_soup('/ym/%04d%02d/' % (ym.year, ym.month), cache=ym < YearMonth.now())
        for item in reversed(soup.select('ul.d-md-flex li.package')):
            metadata = dict([(x['itemprop'], x['content']) for x in item.select('meta')])
            indices.append({
                'wid': metadata['url'].strip('/').split('/')[-1],
                'title': metadata['name'],
                'releaseDate': date.fromisoformat(metadata['releaseDate']),
                'serialNumber': metadata['sku'],
                'cover': item.select_one('img')['src'],
                'source': metadata['url']
            })
        return sorted(indices, key=lambda x: x['releaseDate'], reverse=True)

    def get_work_detail(self, wid) -> dict:
        soup = self.get_soup(f'/title/{wid}/', cache=True)
        if soup.select_one('title').text.strip().startswith('502'):
            raise BadGateway()
        contents = soup.select_one('ul.px-0').select('li')
        metadata = dict([(x.select('div')[0].text.strip(), x.select_one('.pl-3')) for x in contents[2:]])
        return {
            'wid': wid,
            'cover2': OptionalValue(soup.select_one('[itemprop="image"]')['src']).not_blank().get(),
            'title': re.split('\\n', soup.select_one('h1[itemprop="name"]').text.strip())[-1].strip(),
            'description': soup.select_one('[name="twitter:description"]')['content'].strip(),
            'actors': [x.strip() for x in re.split('[／/、]', metadata.get('女優名').text.strip()) if x],
            'serialNumber': soup.select_one('[itemprop="sku"]').text.strip(),
            'series': [x.text.strip() for x in metadata.get('シリーズ').select('a')],
            'directors': metadata.get('監督').text.strip(),
            'duration': OptionalValue(metadata.get('収録時間').text.strip()).filter(
                lambda x: x != '分' and x != '0分').get(),
            'releaseDate': date.fromisoformat(soup.select_one('[itemprop="releaseDate"]')['content']),
            'genres': [x.text.strip() for x in metadata.get('キーワード').select('a')],
            'trailer': OptionalValue(soup.select_one('video')).map(lambda x: x.select_one('source')['src']).get(),
            'images': [x['href'] for x in soup.select('#gallery a') if x['href'] and x['href'].strip()],
            'source': self.root_uri + f'/title/{wid}/'
        }

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name


class Planetplus(MonthlyAdultSite):
    def __init__(self):
        super().__init__('http://planetplus.jp/wp01/', YearMonth(2008, 6), name='Planetplus')
        self.__tags = {}

    def _list_monthly(self, ym: YearMonth) -> List[dict]:
        indices, page = [], 1
        while True:
            soup = self.get_soup('/wp01/tag/%04d年%02d月/page/%d/' % (ym.year, ym.month, page),
                                 cache=ym < YearMonth.now())
            for article in soup.select('article'):
                indices.append({
                    'wid': article['id'].split('-')[-1],
                    'cover': article.select_one('img')['data-src']
                })
            if OptionalValue(soup.select_one('.pagination .current')).map(
                    lambda x: x.find_next_sibling('a')).get() is None:
                break
            page += 1
        return indices

    def get_work_detail(self, wid) -> dict:
        data = self.get_json(f'/wp01/wp-json/wp/v2/posts/{wid}', cache=True)
        content = BeautifulSoup(data['content']['rendered'], 'html.parser')
        infos = content.select('table div[align]')
        genres = []
        for tid in data['tags']:
            if tid not in self.__tags:
                self.__tags[tid] = self.get_json(f'/wp01/wp-json/wp/v2/tags/{tid}', cache=True)['name']
            genres.append(self.__tags[tid])
        return {
            'wid': wid,
            'title': data['title']['rendered'].strip(),
            'cover2': OptionalValue(content.select_one('.panel-widget-style a')).map(lambda x: x['href']).get(),
            'serialNumber': infos[0].text.strip(),
            'releaseDate': datetime.strptime(infos[3].text.strip(), '%Y年%m月%d日').date(),
            'duration': OptionalValue(infos[4].text.strip()).filter(lambda x: x != '- なし -').not_blank().get(),
            'actors': [x.strip() for x in re.split('[/／、]', infos[6].text.strip())],
            'directors': OptionalValue(infos[7].text.strip()).not_blank().get(),
            'description': infos[8].text.strip(),
            'genres': genres,
            'source': data['guid']['rendered']
        }

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name


class Deeps(OrderedAdultSite):
    def __init__(self):
        super().__init__('https://deeps.net/', name="DEEP'S")

    def list_works_between(self, start: date, stop: date) -> List[dict]:
        works, page = [], 1
        while True:
            soup = self.get_soup('/item/', params={'sort': 'new', 'p': page})
            for li in soup.select('.product_list_wrap .list_box li'):
                wid = li.select_one('a')['href'].strip('/').split('/')[-1]
                work = self.get_work_detail(wid)
                if work['releaseDate'] >= stop:
                    continue
                if work['releaseDate'] < start:
                    return works
                works.append(work)
            if page >= int(soup.select('.pager a')[-1]['href'].split('=')[-1]):
                return works
            page += 1

    def get_work_detail(self, wid) -> dict:
        soup = self.get_soup(f'/product/{wid}/', cache=True)
        inner = soup.select_one('.inner')
        infos = inner.select('td')
        return {
            'wid': wid,
            'cover': inner.select_one('img.sp')['src'],
            'cover2': inner.select_one('img.pc')['src'],
            'title': inner.select_one('h1').text.strip(),
            'releaseDate': datetime.strptime(infos[0].text.strip(), '%Y.%m.%d').date(),
            'duration': OptionalValue(infos[1].text.strip()).filter(lambda x: x != '0分').get(),
            'directors': OptionalValue(infos[2].text).not_blank().split('[/]').get(),
            'serialNumber': OptionalValue(infos[3].text.split('/')[0].strip()).not_blank().get(wid.upper()),
            'actors': OptionalValue(infos[4].text).not_blank().split('[／/、]').strip().get(),
            'series': OptionalValue(infos[5].text).not_blank().split('/').strip().get(),
            'genres': [x.strip() for x in infos[6].text.split('/') if x.strip() != ''] + [x.strip() for x in
                                                                                          infos[7].text.split('/') if
                                                                                          x.strip() != ''],
            'trailer': OptionalValue(inner.select_one('source')).map(lambda x: x['src']).value,
            'images': [x['src'] for x in soup.select('.sample_img img')],
            'description': inner.select_one('.item_content').text.strip(),
            'source': self.root_uri + f'/product/{wid}/'
        }

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name


class Maxing(OrderedAdultSite, JaActorSite):
    def __init__(self):
        super().__init__('https://www.maxing.jp/top/', name='Maxing', encoding='EUC-JP')

    def list_actors(self) -> List[dict]:
        actors, page = [], 0
        while True:
            soup = self.get_soup(f'/actress/pos/{page}.html')
            for td in soup.select('#actList .actTd'):
                actors.append({
                    'name': td.select_one('p').text.strip(),
                    'image': td.select_one('img')['src'],
                    'source': td.select_one('a')['href'],
                })
            if soup.select('p[align] a')[-1].select_one('img') is None:
                return actors
            page += 1

    def list_works_between(self, start: date, stop: date) -> List[dict]:
        works, page, over = [], 0, False
        while not over:
            soup = self.get_soup(f'/shop/src/page/{page}.html')
            for td in soup.select('#shopList .proTd'):
                date_str = td.select_one('form p').text.strip()[:10]
                release_date = datetime.strptime(date_str, '%Y/%m/%d').date()
                if release_date >= stop:
                    continue
                if release_date < start:
                    return works
                work = {
                    'wid': td.select_one('a')['href'].split('/')[-1].split('.')[0],
                    'cover': td.select_one('img')['src'],
                    'releaseDate': release_date
                }
                works.append({**work, **self.get_work_detail(work['wid'])})
            if soup.select('p[align] a')[-1].select_one('img') is None:
                return works
            page += 1

    def get_work_detail(self, wid) -> dict:
        # access the media with 'Referer' header
        soup = self.get_soup(f'/shop/pid/{wid}.html', cache=True)
        main = soup.select_one('#main')
        p_img = main.select_one('.pImg')
        infos = main.select('.pDetailDl dd')
        return {
            'wid': wid,
            'title': main.select_one('h2').text.strip(),
            'cover': p_img.select_one('img')['src'],
            'cover2': p_img.select_one('a')['href'],
            'serialNumber': infos[0].text.strip(),
            'directors': OptionalValue(infos[1].text.strip()).not_blank().get(),
            'duration': OptionalValue(re.match('\\d+', infos[2].text.strip())).map(lambda x: int(x.group())).get(),
            'releaseDate': datetime.strptime(infos[3].text.strip(), '%Y年%m月%d日').date(),
            'series': [x.text.strip() for x in infos[6].select('a')],
            'actors': [x.strip() for x in re.split('[、・\\s]+', infos[7].text.strip())],
            'genres': [x.strip() for x in re.split('[、\\s]+', infos[8].text.strip())],
            'description': infos[9].text.strip(),
            'source': self.root_uri + f'/shop/pid/{wid}.html'
        }

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name
        work['duration'] = OptionalValue(work['duration']).map(lambda x: x * 60).get()


class CrystalEizou(MonthlyAdultSite):
    def __init__(self):
        super().__init__('https://www.crystal-eizou.jp/info/index.html', YearMonth(2014, 5), name='クリスタル映像')

    def _list_monthly(self, ym: YearMonth) -> List[dict]:
        path = '/info/archive/%04d_%02d.html' % (ym.year, ym.month)
        soup = self.get_soup(path, cache=ym < YearMonth.now())
        works = []
        for section in reversed(soup.select('.itemSection')):
            infos = section.select('.right2 p')
            if len(infos) == 0:
                continue
            info = infos[1].text.strip()
            wid = re.search('品番：/?([A-Z\\d]+[-－]\\d+)', info).group(1).replace('－', '-')
            works.append({
                'wid': wid,
                'cover': self.root_uri + urljoin('/info/archive/index.html', section.select_one('img')['src']),
                'cover2': OptionalValue(section.select_one('.zoomImg')).map(
                    lambda x: self.root_uri + urljoin('/info/archive/index.html', x['href'])).get(),
                'title': infos[0].text.strip(),
                'releaseDate': datetime.strptime(re.search('発売日：(\\d+/\\d+/\\d+)', info).group(1),
                                                 '%Y/%m/%d').date(),
                'serialNumber': wid,
                'duration': re.search('時間：(\\d+分)', info).group(1),
                'description': infos[2].text.strip(),
                'actors': OptionalValue(re.search('】([^（(]+)', infos[3].text.strip())).map(lambda x: x.group(1)).split(
                    '[、　 ]+').get() if len(infos) > 3 else None,
                'source': self.root_uri + path
            })
        return works

    def get_work_detail(self, wid) -> dict:
        raise NotSupported

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name


class KmProduce(MonthlyAdultSite, JaActorSite):
    def __init__(self):
        super().__init__('https://www.km-produce.com/', YearMonth(2012, 12), name='K.M.Produce')

    def list_actors(self) -> List[dict]:
        soup = self.get_soup('/girls')
        actors = []
        for div in soup.select('.act'):
            img = div.select_one('img')
            actors.append({
                'name': img['alt'],
                'image': img['src'],
                'source': urljoin(self.root_uri + '/girls', div.select_one('a')['href'])
            })
        return actors

    def refactor_actor(self, actor: dict) -> None:
        super().refactor_actor(actor)

    def _list_monthly(self, ym: YearMonth) -> List[dict]:
        soup = self.get_soup('/works', {'archive': f'{ym.year}年{ym.month}月'}, cache=ym < YearMonth.now())
        works = []
        for article in soup.select('article.post'):
            img = article.select_one('img')
            href = article.select_one('h3 a')['href']
            if href.startswith('goods'):
                continue
            works.append({
                'wid': href.strip('/').split('/')[-1],
                'title': img['alt'],
                'cover': self.root_uri + img['src']
            })
        return works

    def get_work_detail(self, wid) -> dict:
        soup = self.get_soup(f'/works/{wid}', cache=True)
        article = soup.select_one('#single')
        infos = dict((x.text.strip(), x.find_next_sibling('dd')) for x in article.select('.information dt'))
        return {
            'wid': wid,
            'title': article.select_one('h1').text.strip(),
            'cover2': self.root_uri + article.select_one('#fulljk img')['src'],
            'description': article.select_one('p.intro').text.strip(),
            'actors': [x.text.strip() for x in infos.get('出演女優').select('a') if x.text.strip()],
            'directors': [x.text.strip() for x in infos.get('監督').select('a')],
            'genres': [x.text.strip() for x in infos.get('ジャンル').select('a')],
            'releaseDate': OptionalValue(infos.get('発売日').text.strip()).not_value("発売日未定").map(
                lambda x: datetime.strptime(x, '%Y/%m/%d').date()).get(),
            'serialNumber': infos.get('品番').text.strip(),
            'duration': OptionalValue(infos.get('収録時間').text.strip().replace(' ', '')).not_blank().get(),
            'source': self.root_uri + f'/works/{wid}'
        }

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name


class AliceJapan(MonthlyAdultSite, JaActorSite):

    def __init__(self):
        super().__init__('https://www.alicejapan.co.jp/top.php', YearMonth(1984, 5), name='アリスJAPAN',
                         headers={'Cookie': 'ageverification=t'})

    def _list_monthly(self, ym: YearMonth) -> List[dict]:
        indices, page = [], 0
        while True:
            params = {'date_word': '%04d%02d' % (ym.year, ym.month)}
            if page > 0:
                params['p'] = page
            soup = self.get_soup('/search_item.php', params=params, cache=ym < YearMonth.now())
            for item in soup.select('.video-list li'):
                url = urlparse(urljoin(self.root_uri, item.select_one('a')['href']))
                indices.append({
                    'wid': parse_qs(url.query).get('item_id')[0],
                    'title': item.select_one('.item-title').text.strip(),
                    'cover': item.select_one('img')['src'],
                    'source': url.geturl()
                })
            if soup.select_one('.pager-last a') is None:
                break
            page += 1
        return indices

    def get_work_detail(self, wid) -> dict:
        soup = self.get_soup(f'/item.php', params={'item_id': wid}, cache=True)
        jacket = soup.select_one('.item-data-disc-jacket')
        trs = soup.select('.mod-item-data-table tr')
        info = dict([(x.select_one('th').text.strip(), x.select_one('td')) for x in trs])
        sn = info.get('品番').text.strip()
        title = soup.select_one('.item-data-title h1').text.strip()
        if sn.endswith('DC') or sn.endswith('b') or title.startswith('■アウトレット限定商品■'):
            raise DuplicateError
        return {
            'wid': wid,
            'title': title,
            'serialNumber': sn,
            'cover2': jacket.select_one('a.zoom')['href'],
            'actors': [x.text.strip() for x in info.get('女優名').select('a')],
            'directors': OptionalValue(info.get('監督名').text.strip()).not_blank().get(),
            'series': OptionalValue(info.get('シリーズ')).map(
                lambda td: [x.text.strip() for x in td.select('a')]).get(),
            'genres': [x.text.strip() for x in info.get('ジャンル').select('a')],
            'duration': OptionalValue(info.get('収録時間').text.strip()).not_blank().filter(
                lambda x: x not in ['分', '0分']).get(),
            'releaseDate': datetime.strptime(info.get('発売日').text.strip(), '%Y年%m月%d日').date(),
            'images': [x['href'] for x in soup.select('.item-data-image-gallery-body li a')],
            'source': self.root_uri + f'/item.php?item_id={wid}'
        }

    def refactor_work(self, work: dict) -> None:
        work['producer'] = self.name

    def list_actors(self) -> List[dict]:
        actors = []
        for alpha in ja_alphabet:
            soup = self.get_soup(f'/actress_list.php', params={'name_syllabary': alpha})
            for item in soup.select('.actress-list-table-container li'):
                url = urlparse(urljoin(self.root_uri, item.select_one('a')['href']))
                aid = parse_qs(url.query).get('actress_id')[0]
                actors.append({
                    'aid': aid,
                    'name': item.select_one('a').text.strip(),
                    'source': url.geturl()
                })
        return actors


jav_producers = [
    FalenoProducer('https://faleno.jp/top/', 'Faleno', prefix='/top'),
    FalenoProducer('https://dahlia-av.jp/', 'DAHLIA'),
    SODPrime(),
    Prestige(),
    Venus(),
    Indies(),
    Planetplus(),
    Deeps(),
    Maxing(),
    CrystalEizou(),
    KmProduce(),
    AliceJapan()
]


def persist_producer(site: AdultSite, data_dir, export_api):
    log.info('Start persisting actors and works of %s', site.hostname)

    try:
        actor_path = os.path.join(data_dir, 'actor', site.hostname + '.json')
        if isinstance(site, ActorSite):
            export.import_data(actor_path, site.list_actors, site.refactor_actor)
            export.export_data(actor_path, export_api.import_actor)

        work_path = os.path.join(data_dir, 'work', site.hostname + '.json')
        if isinstance(site, OrderedAdultSite):
            export.import_ordered_works(work_path, site)
        elif isinstance(site, MonthlyAdultSite):
            export.import_monthly_works(work_path, site)
        else:
            export.import_data(work_path, site.list_works, site.refactor_work)
        export.export_data(work_path, export_api.import_work)
        log.info('Successfully persist actors and works of %s', site.hostname)
    except Exception as ex:
        log.error('Fail to persist actors and works of %s: %s', site.hostname, ex)


def read_kwargs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h', '--host', default='127.0.0.1', help='specify the host name or IP address')
    parser.add_argument('-p', '--port', type=int, default=80, help='specify the port number')
    parser.add_argument('-d', '--data-dir', default='', help='specify the directory of data')
    parser.add_argument('-e', '--excluded', default='', help='specify excluded producers, separated by comma')
    parser.add_argument('--help', action='help')
    return parser.parse_args()


# pyinstaller -n export-ja -F ja.py
if __name__ == '__main__':
    args = read_kwargs()
    kingen_api = export.KingenWeb(f'http://{args.host}:{args.port}')
    dirpath = args.data_dir
    if dirpath is None or dirpath.strip() == '':
        dirpath = os.path.join(os.getenv('TEMP'), 'export-ja')
    if not os.path.isdir(dirpath):
        log.info('create directory: ' + dirpath)
        os.makedirs(dirpath, exist_ok=True)
    excluded = set(x.strip() for x in args.excluded.strip().split(','))

    for producer in will_producers + jav_producers + d2pass_producers:
        if producer.name in excluded:
            log.info('skip producer: ' + producer.name)
            continue
        persist_producer(producer, dirpath, kingen_api)
