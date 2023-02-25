#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Adult sites and resources.

@Author Kingen
"""
import abc
from typing import List, Dict

from internet import BaseSite


class AdultSite(BaseSite):
    def __init__(self, host, **kwargs):
        super().__init__(host, **kwargs)

    @abc.abstractmethod
    def list_actor_indices(self) -> List[Dict]:
        pass

    @abc.abstractmethod
    def get_actor_detail(self, aid: int) -> Dict:
        pass

    @abc.abstractmethod
    def list_work_indices(self) -> List[Dict]:
        pass

    @abc.abstractmethod
    def get_work_detail(self, wid: int) -> Dict:
        pass
