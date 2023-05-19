#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Producers of ALL-PRO group.

@Author Kingen
"""
import re
from datetime import datetime
from typing import Dict, List

from common import OptionalValue
from internet.adult import AdultSite


class Faleno(AdultSite):
    SN_REGEX = re.compile('([a-z]+)(\\d{3})')

    def __init__(self):
        super().__init__('https://faleno.jp/top/', name='faleno')

    def list_works(self) -> List[Dict]:
        works, page, over = [], 1, False
        while not over:
            soup = self.get_soup(f'/top/work/page/{page}/')
            for item in soup.select('.back02 li'):
                wid = item.select_one('a')['href'].strip('/').split('/')[-1]
                work = self.get_work_detail(wid)
                work['cover'] = item.select_one('img')['src'].split('?')[0]
                works.append(work)
            page += 1
            over |= soup.select_one('.nextpostslink') is None
        return works

    def get_work_detail(self, wid) -> Dict:
        soup = self.get_soup(f'/top/works/{wid}/', cache=True)
        head = soup.select_one('.back04')
        infos = soup.select('.box_works01_list p')
        return {
            'id': wid,
            'title': head.select_one('h1').text.strip(),
            'cover2': head.select_one('img')['src'].split('?')[0],
            'trailer': OptionalValue(head.select_one('.pop_sample')).map(lambda x: x['href']).get(),
            'images': [x['href'] for x in soup.select('.box_works01_ga .pop_img')],
            'description': soup.select_one('.box_works01_text').text.strip(),
            'actors': re.split('[ /　]', infos[0].text.strip()),
            'duration': OptionalValue(re.match('\\d+', infos[1].text.strip())).map(lambda x: int(x.group())).get(),
            'release_date': datetime.strptime(OptionalValue(infos[2].text.strip()).not_blank().get(infos[3].text.strip('-')), '%Y/%m/%d').date(),
            'source': self.root_uri + f'/top/works/{wid}/'
        }

    def refactor_work(self, work: dict) -> dict:
        copy = super().refactor_work(work)
        match = self.SN_REGEX.fullmatch(copy['id'])
        copy['serial_number'] = copy['id'].upper() if match is None else match.group(1).upper() + '-' + match.group(2)
        return copy
