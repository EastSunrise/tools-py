#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Adult sites and resources.

@Author Kingen
"""
import abc
from datetime import date
from typing import List, Dict

from internet import BaseSite

start_date = date(1900, 1, 1)
JA_ALPHABET = ['a', 'k', 's', 't', 'n', 'h', 'm', 'y', 'r', 'w']
JA_SYLLABARY = [
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


class AdultSite(BaseSite):

    def __init__(self, home, **kwargs):
        super().__init__(home, **kwargs)

    @abc.abstractmethod
    def list_actors(self) -> List[Dict]:
        raise NotImplementedError

    def list_works(self) -> List[Dict]:
        return self.list_works_since()

    @abc.abstractmethod
    def list_works_since(self, since: date = start_date) -> List[Dict]:
        raise NotImplementedError


class IndexedAdultSite(AdultSite):
    def __init__(self, home, **kwargs):
        super().__init__(home, **kwargs)

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        return [self.get_work_detail(x['id']) for x in self.list_work_indices(since)]

    @abc.abstractmethod
    def list_work_indices(self, since: date = start_date) -> List[Dict]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_work_detail(self, wid) -> Dict:
        raise NotImplementedError
