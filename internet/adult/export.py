#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Persist data.

@Author Kingen
"""
import json
import os
from datetime import timedelta, time as time_cls, datetime, date
from re import Pattern
from typing import List

from requests import Response

from common import create_logger, ComplexEncoder, YearMonth
from internet import BaseSite
from internet.adult import original_date, OrderedAdultSite, MonthlyAdultSite

log = create_logger(__name__)


class KingenWeb(BaseSite):
    def __init__(self, home='http://127.0.0.1:12301/'):
        super().__init__(home, 'kingen-web')
        self.__api_prefix = '/study/api/v1'

    def import_actor(self, actor: dict) -> Response:
        return self._do_request_cacheable(self.__api_prefix + f'/actors/{actor["name"]}', 'PUT', query={'merge': 1},
                                          json_data=self.format_json(actor))

    def import_work(self, work: dict):
        return self._do_request_cacheable(self.__api_prefix + f'/works/{work["serialNumber"]}', 'PUT', query={'merge': 1},
                                          json_data=self.format_json(work))

    def import_resources(self, sn: str, resources: List[dict]):
        return self._do_request_cacheable(self.__api_prefix + f'/work/{sn}/resources', 'PUT', json_data=resources)


def export_data(data_file, export_func):
    """
    Exports data by the specific function.
    """
    if not os.path.exists(data_file):
        return
    with open(data_file, 'r', encoding='utf-8') as fp:
        records: List[dict] = json.load(fp)
    filename, ext = os.path.splitext(data_file)
    export_file = filename + '-export' + ext
    if os.path.exists(export_file):
        with open(export_file, 'r', encoding='utf-8') as fp:
            exports: List[dict] = json.load(fp)
    else:
        exports: List[dict] = []

    changed = False
    for i in range(len(records)):
        if i >= len(exports) or exports[i]['recordAt'] != records[i]['updateAt']:
            changed = True
            updated, created, ignored, errors = 0, 0, 0, []
            for datum in records[i]['data']:
                datum = json.loads(json.dumps(datum, ensure_ascii=False, cls=ComplexEncoder))
                resp = export_func(datum)
                if resp.status_code == 200:
                    updated += 1
                elif resp.status_code == 201:
                    created += 1
                elif resp.status_code == 204:
                    ignored += 1
                elif resp.status_code == 409:
                    errors.append({'error': json.loads(resp.content.decode('utf-8')), 'source': datum})
                else:
                    errors.append({'error': resp.content.decode('utf-8'), 'source': datum})
            export = {
                'recordAt': records[i]['updateAt'],
                'updateAt': datetime.now(),
                'updated': updated,
                'created': created,
                'ignored': ignored,
                'errorsCount': len(errors),
                'errors': errors
            }
            if i >= len(exports):
                exports.append(export)
            else:
                exports[i] = export
    if changed:
        with open(export_file, 'w', encoding='utf-8') as fp:
            json.dump(exports, fp, ensure_ascii=False, cls=ComplexEncoder)


def import_data(filepath, list_func, refactor_func, interval=timedelta(days=14)) -> None:
    """
    Imports the result of the functions to destination json file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as fp:
            records: List[dict] = json.load(fp)
        update_at = datetime.strptime(records[-1]['updateAt'], '%Y-%m-%d %H:%M:%S.%f')
    else:
        update_at = datetime.combine(original_date, time_cls())

    if datetime.now() - update_at >= interval:
        data = [x.copy() for x in list_func()]
        if len(data) == 0:
            return
        for datum in data:
            refactor_func(datum)
        records = [{
            'updateAt': datetime.now(),
            'count': len(data),
            'data': data
        }]
        with open(filepath, 'w', encoding='utf-8') as fp:
            json.dump(records, fp, ensure_ascii=False, cls=ComplexEncoder)


def import_ordered_works(filepath, site: OrderedAdultSite, interval=timedelta(days=1)) -> None:
    """
    Imports in-order works of the given site to destination json file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    start, stop, records = original_date, date.today(), []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as fp:
            records: List[dict] = json.load(fp)
        start = date.fromisoformat(records[-1]['stop'])

    if stop - start >= interval:
        works = [x.copy() for x in site.list_works_between(start, stop)]
        if len(works) == 0:
            return
        for work in works:
            site.refactor_work(work)
        records.append({
            'updateAt': datetime.now(),
            'start': start,
            'stop': stop,
            'count': len(works),
            'data': works
        })
        with open(filepath, 'w', encoding='utf-8') as fp:
            json.dump(records, fp, ensure_ascii=False, cls=ComplexEncoder)


def import_monthly_works(filepath, site: MonthlyAdultSite) -> None:
    """
    Imports monthly works of the given site to destination json file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    start, stop, records = site.start_month, YearMonth.now(), []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as fp:
            records: List[dict] = json.load(fp)
        start = YearMonth.parse(records[-1]['stop'])

    if start < stop:
        works = [x.copy() for x in site.list_works_between(start, stop)]
        if len(works) == 0:
            return
        for work in works:
            site.refactor_work(work)
        records.append({
            'updateAt': datetime.now(),
            'start': str(start),
            'stop': str(stop),
            'count': len(works),
            'data': works
        })
        with open(filepath, 'w', encoding='utf-8') as fp:
            json.dump(records, fp, ensure_ascii=False, cls=ComplexEncoder)


def validate_works(works: List[dict], sn_regexp: Pattern, ordered=True) -> None:
    """
    Validates properties of given works.
    """
    log.debug('# checking serial numbers')
    for work in works:
        sn = work.get('serialNumber')
        if sn is not None and sn_regexp.fullmatch(sn) is None:
            log.error('mismatched sn: ' + sn)

    if ordered:
        log.debug('# checking release dates')
        last_date = None
        for work in works:
            release_date = work.get('releaseDate')
            if release_date is None:
                log.error('no release date: ' + str(work))
            elif last_date is not None and last_date < release_date:
                log.error('not descending release date from [%s] to [%s]', last_date, release_date)
            last_date = release_date
