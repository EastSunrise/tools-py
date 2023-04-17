#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Producers of D2PASS group.

@Author Kingen
"""
import re
from datetime import date, datetime, time
from typing import List, Dict

from werkzeug.exceptions import NotFound

import common
from internet.adult import AdultSite, JA_ALPHABET

log = common.create_logger(__name__)


class Caribbean(AdultSite):
    def __init__(self):
        super().__init__('https://www.caribbeancom.com/index2.htm', name='caribbean', encoding='EUC-JP')

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
                    'releaseDate': date.fromisoformat(item.select_one('.meta-data').text.strip()),
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
            'producer': self.name,
            'description': info.select_one('[itemprop="description"]').text.strip(),
            'genres': [x.text.strip() for x in info.select('.spec-item')],
            'trailer': f'https://smovie.caribbeancom.com/sample/movies/{sn}/{quality}.mp4',
            'images': [self.root_uri + x['src'] for x in gallery.select('.gallery-image')] if gallery else None,
            'source': self.root_uri + f'/moviepages/{sn}/index.html',
            'actors': [x.text.strip() for x in info.select('[itemprop="actor"]')]
        }


class OnePondo(AdultSite):

    def __init__(self):
        super().__init__('https://www.1pondo.tv/', name='1pondo')

    def list_actors(self) -> List[Dict]:
        return [self.__refactor_actor(a) for g in self.get_json('/dyn/phpauto/actresses.json').values() for arr in g.values() for a in arr]

    def __refactor_actor(self, actor: dict):
        image = actor.pop('image_url')
        actor['images'] = self.root_uri + image if image else None
        actor['source'] = self.root_uri + '/search/?a=' + str(actor['id'])
        return actor

    def list_works(self) -> List[Dict]:
        start, total = 0, 51
        works = []
        while start < total:
            data = self.get_json(f'/dyn/phpauto/movie_lists/list_oldest_{start}.json', cache=start + 50 < total)
            works.extend(self.__refactor_work(w) for w in data['Rows'])
            start += data['SplitSize']
            total = data['TotalRows']
        return works

    def __refactor_work(self, work: dict):
        mid = work["MovieID"]
        work['title'] = work.pop('Title')
        work['serialNumber'] = mid
        work['year'] = work.pop('Year')
        work['cover'] = work['ThumbUltra']
        work['duration'] = work.pop('Duration')
        work['releaseDate'] = work.pop('Release')
        work['producer'] = self.name
        work['series'] = work.pop('Series')
        work['description'] = work.pop('Desc').strip()
        work['genres'] = work.pop('UCNAME')
        work['trailer'] = sorted(work['SampleFiles'], key=lambda x: x['FileSize'])[-1]['URL'] if 'SampleFiles' in work else None
        if work['Gallery']:
            rows = self.get_json(f'/dyn/dla/json/movie_gallery/{mid}.json', cache=True)['Rows']
            work['images'] = [self.root_uri + '/dyn/dla/images/' + x['Img'] for x in rows]
        work['source'] = self.root_uri + f'/movies/{mid}/'
        work['actors'] = work['ActressesJa']
        return work


class Heyzo(AdultSite):
    SITE_ID = 3000

    def __init__(self):
        super().__init__('https://www.heyzo.com/index2.html', name='heyzo')

    def list_actors(self) -> List[Dict]:
        soup = self.get_soup('/actor_all.html')
        actors, exists = [], set()
        for dd in soup.select('.actor_list dd'):
            aid = int(dd.select_one('a')['href'].split('_')[1])
            img = dd.select_one('.actress_image')
            name = img['alt']
            if name in exists:
                continue
            exists.add(name)
            actors.append({
                'id': aid,
                'name': name,
                'images': self.root_uri + img['src'].replace('_s', ''),
                'source': self.root_uri + f'/listpages/actor_{aid}_1.html'
            })
        return actors

    def list_works(self) -> List[Dict]:
        return [self.get_work_detail(x['id']) for x in self.list_work_indices()]

    def list_work_indices(self) -> List[Dict]:
        page, total = 1, 1
        indices = []
        while page <= total:
            soup = self.get_soup(f'/listpages/all_{page}.html')
            for item in soup.select('#movies .movie'):
                img = item.select_one('img.lazy')
                indices.append({
                    'id': item['data-movie-id'],
                    'cover': self.root_uri + img['data-original'],
                    'title': img['title'],
                    'releaseDate': date.fromisoformat(item.select_one('.release').text.strip()[-10:])
                })
            page += 1
            total = int(soup.select_one('.list_pagetotal').text.strip())
        return indices

    def get_work_detail(self, wid: str):
        soup = self.get_soup(f'/moviepages/{wid}/index.html', cache=True)
        if soup.select_one('title').text.startswith('HEYZO 404'):
            raise NotFound()
        section = soup.select_one('div#movie')
        info = section.select_one('.movieInfo')
        scripts = ''.join(x.get_text() for x in soup.select('script'))
        idx = scripts.find('"full":"')
        if idx >= 0:
            duration = time.fromisoformat(scripts[idx + 8:scripts.index('"', idx + 8)])
        else:
            duration = None
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
            'serialNumber': 'HEYZO-' + wid,
            'cover': self.root_uri + f'/contents/{self.SITE_ID}/{wid}/images/player_thumbnail.jpg',
            'duration': (duration.hour * 60 + duration.minute) * 60 + duration.second if duration else None,
            'releaseDate': release,
            'producer': self.name,
            'series': series if series != '-----' else None,
            'description': memo.text.strip() if memo else None,
            'genres': [x.text.strip() for x in tag.select('li')] if tag else None,
            'trailer': self.root_uri + f'/contents/{self.SITE_ID}/{wid}/sample_low.mp4',
            'images': images[:-3],
            'source': self.root_uri + f'/moviepages/{wid}/index.html',
            'actors': [x.text.strip() for x in info.select('.table-actor a')]
        }
