#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Producers of D2PASS group.

@Author Kingen
"""
import re
from datetime import date, datetime
from typing import List, Dict

from werkzeug.exceptions import NotFound

import common
from internet.adult import JA_ALPHABET, start_date, SortedAdultSite

log = common.create_logger(__name__)


class Caribbean(SortedAdultSite):
    def __init__(self):
        super().__init__('https://www.caribbeancom.com/index2.htm', name='caribbean', encoding='EUC-JP')

    def list_actors(self) -> List[Dict]:
        actors = []
        for alpha in JA_ALPHABET:
            soup = self.get_soup(f'/actress/{alpha}.html')
            actors.extend([{
                'id': item.select_one('.entry')['href'].split('/')[-2],
                'name': item.select_one('.meta-name').text.strip(),
                'avatar': self.root_uri + item.select_one('img')['src']
            } for item in soup.select('.grid-item')])
        return actors

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        works, page, over = [], 1, False
        while not over:
            soup = self.get_soup(f'/listpages/all{page}.htm')
            for item in soup.select('div.grid-item'):
                release_date = date.fromisoformat(item.select_one('.meta-data').text.strip())
                if release_date < since:
                    over = True
                    break
                wid = item.select_one('[itemprop="url"]')['href'].split('/')[-2]
                works.append(self.get_work_detail(wid))
            page += 1
            over |= 'is-disabled' in soup.select('.pagination-item')[-1].get_attribute_list('class', [])
        return works

    def get_work_detail(self, wid) -> Dict:
        soup = self.get_soup(f'/moviepages/{wid}/index.html', cache=True)
        info = soup.select_one('div.movie-info')
        duration = None
        try:
            seconds = 0
            for v in re.split('[:：]', info.select_one('[itemprop="duration"]').text.strip()):
                seconds = seconds * 60 + int(v)
            mm, ss = divmod(seconds, 60)
            hh, mm = divmod(mm, 60)
            duration = "%02d:%02d:%02d" % (hh, mm, ss)
        except Exception:
            pass
        quality = soup.select_one(".quality").text.strip()
        quality = quality[:quality.index('p') + 1]
        gallery = soup.select_one('.gallery')
        return {
            'id': wid,
            'title': info.select_one('.heading').text.strip(),
            'cover2': self.root_uri + f'/moviepages/{wid}/images/l_l.jpg',
            'duration': duration,
            'release_date': datetime.strptime(info.select_one('[itemprop="datePublished"]').text.strip(), '%Y/%m/%d').date(),
            'description': info.select_one('[itemprop="description"]').text.strip(),
            'genres': [x.text.strip() for x in info.select('.spec-item')],
            'trailer': f'https://smovie.caribbeancom.com/sample/movies/{wid}/{quality}.mp4',
            'images': [self.root_uri + x['src'] for x in gallery.select('.gallery-image')] if gallery else None,
            'actors': [x.text.strip() for x in info.select('[itemprop="actor"]')]
        }


class OnePondo(SortedAdultSite):
    def __init__(self):
        super().__init__('https://www.1pondo.tv/', name='1pondo')

    def list_actors(self) -> List[Dict]:
        return [a for g in self.get_json('/dyn/phpauto/actresses.json').values() for arr in g.values() for a in arr]

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        works, start, over = [], 0, False
        while not over:
            data = self.get_json(f'/dyn/phpauto/movie_lists/list_newest_{start}.json')
            for row in data['Rows']:
                row['Release'] = date.fromisoformat(row['Release'])
                if row['Release'] < since:
                    over = True
                    break
                works.append(self.__get_gallery(row))
            start += data['SplitSize']
            over |= start >= data['TotalRows']
        return works

    def get_work_detail(self, wid) -> Dict:
        work = self.get_json(f'/dyn/phpauto/movie_details/movie_id/{wid}.json', cache=True)
        return self.__get_gallery(work)

    def __get_gallery(self, work: dict):
        if work['Gallery']:
            work['Images'] = self.get_json(f'/dyn/dla/json/movie_gallery/{work["MovieID"]}.json', cache=True)['Rows']
        return work


class Heyzo(SortedAdultSite):
    SITE_ID = 3000

    def __init__(self):
        super().__init__('https://www.heyzo.com/index2.html', name='heyzo')

    def list_actors(self) -> List[Dict]:
        actors, exists = [], set()
        for dd in self.get_soup('/actor_all.html').select('.actor_list dd'):
            img = dd.select_one('.actress_image')
            if img['alt'] in exists:
                continue
            exists.add(img['alt'])
            actors.append({
                'id': dd.select_one('a')['href'].split('_')[1],
                'name': img['alt'],
                'avatar': self.root_uri + img['src'].replace('_s', '')
            })
        return actors

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        works, page, total, over = [], 1, 1, False
        while not over and page <= total:
            soup = self.get_soup(f'/listpages/all_{page}.html')
            for item in soup.select('#movies .movie'):
                release = date.fromisoformat(item.select_one('.release').text.split('～')[0].strip()[-10:])
                if release < since:
                    over = True
                    break
                wid = item['data-movie-id']
                works.append(self.get_work_detail(wid))
            page += 1
            total = max(total, int(soup.select_one('.list_pagetotal').text.strip()))
        return works

    def get_work_detail(self, wid):
        soup = self.get_soup(f'/moviepages/{wid}/index.html', cache=True)
        if soup.select_one('title').text.startswith('HEYZO 404'):
            raise NotFound()
        section = soup.select_one('div#movie')
        info = section.select_one('.movieInfo')
        scripts = ''.join(x.get_text() for x in soup.select('script'))
        idx = scripts.find('"full":"')
        duration = scripts[idx + 8:scripts.index('"', idx + 8)] if idx >= 0 else None
        try:
            release = date.fromisoformat(info.select('.table-release-day td')[-1].text.strip()[:10])
        except ValueError:
            release = None
        memo = info.select_one('.memo')
        series = info.select('.table-series td')[-1].text.strip()
        images = []
        idx = 0
        while True:
            idx = scripts.find('"gallery_mobile" href="', idx)
            if idx < 0:
                break
            images.append(self.root_uri + scripts[idx + 23:scripts.index('"', idx + 23)].replace('/member', ''))
            idx += 23
        tag = info.select_one('.tag-keyword-list')
        return {
            'id': wid,
            'title': section.select_one('h1').text.split('-')[0].strip(),
            'cover2': self.root_uri + f'/contents/{self.SITE_ID}/{wid}/images/player_thumbnail.jpg',
            'duration': duration,
            'release_date': release,
            'series': series if series != '-----' else None,
            'description': memo.text.strip() if memo else None,
            'genres': [x.text.strip() for x in tag.select('li')] if tag else None,
            'trailer': self.root_uri + f'/contents/{self.SITE_ID}/{wid}/sample_low.mp4',
            'images': images[:-3],
            'actors': [x.text.strip() for x in info.select('.table-actor a')]
        }
