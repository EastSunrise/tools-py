#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Adult sites and resources.

@Author Kingen
"""
import abc
from datetime import date
from typing import List, Dict

from common import YearMonth
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
    def list_works(self) -> List[Dict]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_work_detail(self, wid) -> Dict:
        raise NotImplementedError

    def refactor_work(self, work: dict) -> dict:
        copy = work.copy()
        copy['duration'] = work['duration'] * 60 if work.get('duration') is not None else None
        copy['producer'] = self.name
        return copy


class SortedAdultSite(AdultSite):
    def list_works(self) -> List[Dict]:
        return self.list_works_since()

    @abc.abstractmethod
    def list_works_since(self, since: date = start_date) -> List[Dict]:
        raise NotImplementedError


class MonthlyAdultSite(SortedAdultSite):
    def __init__(self, home, start_month: YearMonth, **kwargs):
        super().__init__(home, **kwargs)
        self.__start_month = start_month

    def list_works_since(self, since: date = start_date) -> List[Dict]:
        works, ym, over = [], YearMonth.now().plus_months(-1), False
        while not over and ym >= self.__start_month:
            for work in self._list_monthly(ym):
                work.update(self._get_more_detail(work))
                if work['release_date'] < since:
                    over = True
                    break
                works.append(work)
            ym = ym.plus_months(-1)
        return works

    @abc.abstractmethod
    def _list_monthly(self, ym: YearMonth) -> List[Dict]:
        pass

    def _get_more_detail(self, idx: dict) -> dict:
        return self.get_work_detail(idx['id'])


class ActorSupplier:
    @abc.abstractmethod
    def list_actors(self) -> List[Dict]:
        raise NotImplementedError

    def refactor_actor(self, actor: dict) -> dict:
        return actor.copy()
