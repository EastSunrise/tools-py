#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Other producers.

@Author Kingen
"""
import re
from datetime import date, datetime
from typing import Dict, List
from urllib import parse

from scrapy.exceptions import NotSupported

from common import YearMonth, OptionalValue
from internet.adult import SortedAdultSite, start_date, ActorSupplier


class Deeps(SortedAdultSite):
    def __init__(self):
        super().__init__('https://deeps.net/', name='deeps')

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        works, page, over = [], 1, False
        while not over:
            soup = self.get_soup('/item/', params={'sort': 'new', 'p': page}, cache=True)
            for li in soup.select('.product_list_wrap .list_box li'):
                wid = li.select_one('a')['href'].strip('/').split('/')[-1]
                work = self.get_work_detail(wid)
                if work['release_date'] < since:
                    over = True
                    break
                work['cover'] = li.select_one('img')['src']
                works.append(work)
            page += 1
            over |= page > int(soup.select('.pager a')[-1]['href'].split('=')[-1])
        return works

    def get_work_detail(self, wid):
        soup = self.get_soup(f'/product/{wid}/', cache=True)
        inner = soup.select_one('.inner')
        infos = inner.select('td')
        return {
            'id': wid,
            'cover': inner.select_one('img.sp')['src'],
            'cover2': inner.select_one('img.pc')['src'],
            'title': inner.select_one('h1').text.strip(),
            'release_date': datetime.strptime(infos[0].text.strip(), '%Y.%m.%d').date(),
            'duration': int(re.match('\\d+', infos[1].text.strip()).group()),
            'director': OptionalValue(infos[2].text).not_blank().split('[/]').get(),
            'serial_number': infos[3].text.split('/')[0].strip(),
            'actors': OptionalValue(infos[4].text).not_blank().split('[/、]').get(),
            'series': OptionalValue(infos[5].text).not_blank().split('/').get(),
            'genres': [x.strip() for x in infos[6].text.split('/')] + [x.strip() for x in infos[7].text.split('/')],
            'trailer': OptionalValue(inner.select_one('source')).map(lambda x: x['src']).value,
            'images': [x['src'] for x in soup.select('.sample_img img')],
            'description': inner.select_one('.item_content').text.strip(),
            'source': self.root_uri + f'/product/{wid}/'
        }


class CrystalEizou(SortedAdultSite):
    start_month = YearMonth(2014, 5)

    def __init__(self):
        super().__init__('https://www.crystal-eizou.jp/info/index.html', name='crystal-eizou')

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        works, ym, over = [], YearMonth.now().plus_months(-1), False
        while not over and ym >= self.start_month:
            path = '/info/archive/%04d_%02d.html' % (ym.year, ym.month)
            soup = self.get_soup(path, cache=True)
            sections = soup.select('.itemSection')
            for section in reversed(sections):
                infos = section.select('.right2 p')
                if len(infos) == 0:
                    continue
                info = infos[1].text.strip()
                works.append({
                    'cover': self.root_uri + parse.urljoin('/info/archive/index.html', section.select_one('img')['src']),
                    'cover2': OptionalValue(section.select_one('.zoomImg')).map(lambda x: self.root_uri + parse.urljoin('/info/archive/index.html', x['href'])).get(),
                    'title': infos[0].text.strip(),
                    'release_date': datetime.strptime(re.search('発売日：(\\d+/\\d+/\\d+)', info).group(1), '%Y/%m/%d').date(),
                    'serial_number': re.search('品番：/?([A-Z\\d]+[-－]\\d+)', info).group(1).replace('－', '-'),
                    'duration': int(re.search('時間：(\\d+)分', info).group(1)),
                    'description': infos[2].text.strip(),
                    'actors': OptionalValue(re.search('】([^（(]+)', infos[3].text.strip())).map(lambda x: x.group(1)).split('[、　 ・]+').get() if len(infos) > 3 else None,
                    'source': self.root_uri + path
                })
            ym = ym.plus_months(-1)
        return works

    def get_work_detail(self, wid) -> Dict:
        raise NotSupported


class Venus(SortedAdultSite):
    start_month = YearMonth(2009, 4)

    def __init__(self):
        super().__init__('https://venus-av.com/', name='venus')

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        works, ym, over = [], YearMonth.now().plus_months(-1), False
        while not over and ym >= self.start_month:
            soup = self.get_soup('/products/%04d/%02d/' % (ym.year, ym.month), cache=True)
            for li in soup.select('.topNewreleaseList li'):
                wid = li.select_one('a')['href'].split('/')[-2]
                work = self.get_work_detail(wid)
                if work['release_date'] < since:
                    over = True
                    break
                works.append(work)
            ym = ym.plus_months(-1)
        return works

    def get_work_detail(self, wid) -> Dict:
        soup = self.get_soup(f'/products/{wid}/', cache=True)
        main = soup.select_one('#main')
        infos = main.select('.productsDataDetail dd')
        match = re.fullmatch('(\\d{4})[年月](\\d{1,2})月(\\d{1,2})日', infos[4].text.strip())
        return {
            'title': main.select_one('h1').text.strip(),
            'cover2': self.root_uri + main.select_one('.productsImg img')['src'],
            'description': infos[0].text.strip(),
            'actors': infos[1].text.strip().split('/'),
            'serial_number': infos[2].text.strip(),
            'genres': infos[3].text.strip().split('/'),
            'release_date': date(int(match.group(1)), int(match.group(2)), int(match.group(3))),
            'source': self.root_uri + f'/products/{wid}/'
        }


class Maxing(SortedAdultSite, ActorSupplier):
    def __init__(self):
        super().__init__('https://www.maxing.jp/top/', name='maxing', encoding='EUC-JP')

    def list_actors(self) -> List[Dict]:
        actors, page, over = [], 0, False
        while not over:
            soup = self.get_soup(f'/actress/pos/{page}.html')
            for td in soup.select('#actList .actTd'):
                actors.append({
                    'source': td.select_one('a')['href'],
                    'avatar': td.select_one('img')['src'],
                    'name': td.select_one('p').text.strip()
                })
            page += 1
            over |= soup.select('p[align] a')[-1].select_one('img') is None
        return actors

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        works, page, over = [], 0, False
        while not over:
            soup = self.get_soup(f'/shop/src/page/{page}.html')
            for td in soup.select('#shopList .proTd'):
                wid = td.select_one('a')['href'].split('/')[-1].split('.')[0]
                work = self.get_work_detail(wid)
                if work['release_date'] < since:
                    over = True
                    break
                works.append(work)
            page += 1
            over |= soup.select('p[align] a')[-1].select_one('img') is None
        return works

    def get_work_detail(self, wid) -> Dict:
        # access the media with 'Referer' header
        soup = self.get_soup(f'/shop/pid/{wid}.html', cache=True)
        main = soup.select_one('#main')
        p_img = main.select_one('.pImg')
        infos = main.select('.pDetailDl dd')
        return {
            'id': wid,
            'title': main.select_one('h2').text.strip(),
            'cover': p_img.select_one('img')['src'],
            'cover2': p_img.select_one('a')['href'],
            'serial_number': infos[0].text.strip(),
            'director': OptionalValue(infos[1].text.strip()).not_blank().get(),
            'duration': OptionalValue(re.match('\\d+', infos[2].text.strip())).map(lambda x: int(x.group())).get(),
            'release_date': datetime.strptime(infos[3].text.strip(), '%Y年%m月%d日').date(),
            'series': [x.text.strip() for x in infos[6].select('a')],
            'actors': [x.text.strip() for x in infos[7].select('a')],
            'genres': [x.text.strip() for x in infos[8].select('a')],
            'description': infos[9].text.strip(),
            'source': self.root_uri + f'/shop/pid/{wid}.html'
        }
