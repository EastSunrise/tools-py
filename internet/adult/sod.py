#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Producers of SOD group.

@Author Kingen
"""
import re
from datetime import datetime, date
from typing import List, Dict

from scrapy.exceptions import NotSupported
from werkzeug.exceptions import NotFound

from common import OptionalValue
from internet.adult import JA_SYLLABARY, AdultSite, start_date, Exportable


class SODPrime(AdultSite, Exportable):
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
                        'id': img['id'],
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
            soup = self.get_soup(f'/prime/videos/genre/', params={'sort': 3, 'page': page})
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

    def refactor_actor(self, actor: dict) -> dict:
        return {
            'name': actor['name'],
            'avatar': actor['avatar'],
            'source': self.root_uri + '/prime/videos/genre/?actress[]=' + actor['id']
        }

    def refactor_work(self, work: dict) -> dict:
        copy = work.copy()
        copy['serial_number'] = work['id']
        copy['duration'] = work['duration'] * 60 if work.get('duration') else None
        copy['source'] = self.root_uri + '/prime/videos/?id=' + work['id']
        return copy


class NaturalHigh(AdultSite, Exportable):
    def __init__(self):
        super().__init__('https://www.naturalhigh.co.jp/', name='natural-high', headers={'Cookie': 'age_gate=18'})

    def list_actors(self) -> List[Dict]:
        raise NotSupported

    def refactor_actor(self, actor: dict) -> dict:
        raise NotSupported

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        raise NotSupported

    def list_works(self) -> List[Dict]:
        works, page, over = [], 1, False
        while not over:
            soup = self.get_soup('/all/', params={'sf_paged': page})
            for li in soup.select('.archive_style li'):
                wid = li.select_one('a')['href'].strip('/').split('/')[-1]
                try:
                    work = self.get_work_detail(wid)
                except TypeError:
                    continue
                works.append(work)
            page += 1
            over |= soup.select_one('.pagination .nextpostslink') is None
        return works

    def get_work_detail(self, wid) -> Dict:
        soup = self.get_soup(f'/all/{wid}', cache=True)
        if 'グッズ' in soup.select_one('.single_cat').text.strip():
            raise TypeError('Not a work')
        infos = soup.select('.single_over dd')
        img = soup.select_one('.single_main_image img')
        if img.has_attr('srcset'):
            images = [x.strip().split(' ') for x in img['srcset'].split(',')]
            cover = max(images, key=lambda x: int(x[-1][:-1]))[0]
        else:
            cover = img['src']
        matcher = re.fullmatch('(\\d{4})/?(\\d{1,2})/(\\d{1,2})', infos[1].text.strip())
        return {
            'id': wid,
            'title': soup.select_one('#single_cap h1').text.strip(),
            'cover': cover,
            'description': OptionalValue(soup.select_one('#single_cap dd')).map(lambda x: x.contents[0].text.strip()).value,
            'director': [x.text.strip() for x in infos[0].select('a')],
            'release_date': date(int(matcher.group(1)), int(matcher.group(2)), int(matcher.group(3))),
            'series': OptionalValue(infos[2].text.strip()).filter(lambda x: x != 'ー').not_empty().value,
            'duration': OptionalValue(infos[3].text.strip()[:-1]).not_empty().map(int).value,
            'serial_number': infos[4].text.strip(),
            'trailer': OptionalValue(soup.select_one('#movie_inline video')).map(lambda x: x['src']).value,
            'images': [x['href'] for x in soup.select('.p-style__gallery a')]
        }

    def refactor_work(self, work: dict) -> dict:
        copy = work.copy()
        copy['duration'] = work['duration'] * 60 if work.get('duration') else None
        copy['producer'] = self.name
        copy['source'] = self.root_uri + '/all/' + work['id']
        return copy


class IEnergy(AdultSite, Exportable):
    def __init__(self):
        super().__init__('http://www.ienergy1.com/', name='i-energy', headers={'Cookie': 'over18=Yes'})

    def list_actors(self) -> List[Dict]:
        raise NotSupported

    def refactor_actor(self, actor: dict) -> dict:
        raise NotSupported

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        works, current, over = [], date.today().strftime('%Y/%m'), False
        for option in self.get_soup('/search/').select('select[name=release] option')[1:]:
            release_month = option['value']
            soup = self.get_soup('/search/index.php', params={'release': release_month}, cache=release_month < current)
            for div in soup.select('.searchview'):
                wid = div.select_one('a')['href'].split('=')[-1]
                work = self.get_work_detail(wid)
                if work['release_date'] < since:
                    over = True
                    break
                works.append(work)
            if over:
                break
        return works

    def get_work_detail(self, wid) -> Dict:
        soup = self.get_soup('/dvd/index.php', params={'dvd_id': wid}, cache=True)
        main = soup.select_one('#main')
        infos = main.select('.data tr')
        sn = infos[4].select_one('p.tp02').text.strip()
        return {
            'id': wid,
            'title': main.select_one('h2').text.strip(),
            'cover': self.root_uri + main.select_one('.cover img')['src'],
            'description': main.select_one('.summary').text.strip(),
            'serial_number': sn,
            'duration': OptionalValue(re.match('\\d+', infos[2].select_one('p.tp02').text.strip())).map(lambda x: int(x.group())).value,
            'director': infos[3].select_one('p.tp02').text.strip(),
            'release_date': datetime.strptime(infos[5].select_one('p.tp02').text.strip(), '%Y/%m/%d').date(),
            'genres': re.split(' +', infos[1].select_one('p.tp02').text.strip()),
            'series': infos[6].select_one('p.tp02').text.strip(),
            'images': [self.root_uri + x['src'] for x in main.select('.photos img')],
            'trailer': OptionalValue(main.select_one('#player_a source')).map(lambda x: self.root_uri + x['src']).value,
            'actors': re.split('[、 ,　・]+', infos[0].select_one('p.tp02').text.strip())
        }

    def refactor_work(self, work: dict) -> dict:
        copy = work.copy()
        copy['producer'] = self.name
        copy['duration'] = work['duration'] * 60 if work['duration'] else None
        copy['source'] = self.root_uri + '/dvd/index.php?dvd_id=' + work['id']
        return copy
