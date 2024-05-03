#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Adult sites and resources.

@Author Kingen
"""
import abc
from datetime import date
from typing import List

from scrapy.exceptions import NotSupported
from werkzeug.exceptions import HTTPException

from common import YearMonth
from internet import BaseSite, DuplicateError

original_date = date(1900, 1, 1)


class AdultSite(BaseSite):
    @abc.abstractmethod
    def list_works(self) -> List[dict]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_work_detail(self, wid) -> dict:
        raise NotImplementedError

    def refactor_work(self, work: dict) -> None:
        """
        Refactors properties of the work in-place.
        """
        pass


class OrderedAdultSite(AdultSite):
    def list_works(self) -> List[dict]:
        return self.list_works_between(original_date, date.today())

    @abc.abstractmethod
    def list_works_between(self, start: date, stop: date) -> List[dict]:
        """
        Retrieves works between the two dates.
        @param start: start date(inclusive)
        @param stop: end date(exclusive)
        @return works order by date descending if possible
        """
        raise NotImplementedError


class MonthlyAdultSite(AdultSite):
    def __init__(self, home, start_month: YearMonth, **kwargs):
        super().__init__(home, **kwargs)
        self.__start_month = start_month

    @property
    def start_month(self):
        return self.__start_month

    def list_works(self) -> List[dict]:
        return self.list_works_between(self.__start_month, YearMonth.now())

    def list_works_between(self, start: YearMonth, stop: YearMonth) -> List[dict]:
        """
        Retrieves works between the two months.
        @param start: start month(inclusive)
        @param stop: end month(exclusive), not after current month
        """
        works, ym = [], stop.plus_months(-1)
        while ym >= self.__start_month and ym >= start:
            for work in self._list_monthly(ym):
                try:
                    work.update(self.get_work_detail(work['wid']))
                except DuplicateError:
                    continue
                except (HTTPException, NotSupported):
                    pass
                works.append(work)
            ym = ym.plus_months(-1)
        return works

    @abc.abstractmethod
    def _list_monthly(self, ym: YearMonth) -> List[dict]:
        raise NotImplementedError


class ActorSite:
    @abc.abstractmethod
    def list_actors(self) -> List[dict]:
        raise NotImplementedError

    def refactor_actor(self, actor: dict) -> None:
        """
        Refactors properties of the actor in-place.
        """
        pass

