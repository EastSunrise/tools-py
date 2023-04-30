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

    @abc.abstractmethod
    def list_actors(self) -> List[Dict]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_works(self) -> List[Dict]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_work_detail(self, wid) -> Dict:
        raise NotImplementedError

    def refactor_actor(self, actor: dict) -> dict:
        return actor.copy()

    def refactor_work(self, work: dict) -> dict:
        return work.copy()


class SortedAdultSite(AdultSite):
    def list_works(self) -> List[Dict]:
        return self.list_works_since()

    @abc.abstractmethod
    def list_works_since(self, since: date = start_date) -> List[Dict]:
        raise NotImplementedError
