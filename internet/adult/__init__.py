#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Adult sites and resources.

@Author Kingen
"""
import abc
import os.path
from typing import List, Dict

from internet import BaseSite, run_cacheable

JA_ALPHABET = ['a', 'k', 's', 't', 'n', 'h', 'm', 'y', 'r', 'w']


class AdultSite(BaseSite):
    def __init__(self, home, **kwargs):
        super().__init__(home, **kwargs)

    @abc.abstractmethod
    def list_actors(self) -> List[Dict]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_works(self) -> List[Dict]:
        raise NotImplementedError

    def export(self, dirpath):
        run_cacheable(os.path.join(dirpath, 'actors.json'), self.list_actors)
        run_cacheable(os.path.join(dirpath, 'works.json'), self.list_works)


class IndexedAdultSite(AdultSite):
    def __init__(self, home, **kwargs):
        super().__init__(home, **kwargs)

    def list_actors(self) -> List[Dict]:
        return [self.get_actor_detail(x) for x in self.list_actor_indices()]

    @abc.abstractmethod
    def list_actor_indices(self) -> List[Dict]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_actor_detail(self, idx) -> Dict:
        raise NotImplementedError

    def list_works(self) -> List[Dict]:
        return [self.get_work_detail(x) for x in self.list_work_indices()]

    @abc.abstractmethod
    def list_work_indices(self) -> List[Dict]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_work_detail(self, idx) -> Dict:
        raise NotImplementedError
