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

from common import create_logger, ComplexEncoder, YearMonth
from internet import BaseSite
from internet.adult import original_date, OrderedAdultSite, MonthlyAdultSite

log = create_logger(__name__)

update_interval = timedelta(days=30)


class KingenWeb(BaseSite):
    def __init__(self, home='http://127.0.0.1:12301/'):
        super().__init__(home, 'kingen-web')

    def import_actor(self, actor: dict):
        return self.post_json('/study/actor/import', params=actor)

    def import_work(self, work: dict):
        return self.post_json('/study/work/import', params=work)


kingen_web = KingenWeb()


def export_data(data: List[dict], export_func):
    """
    Exports data by the specific function.
    """
    ignored, updated, errors = 0, 0, []
    for datum in data:
        datum = json.loads(json.dumps(datum, ensure_ascii=False, cls=ComplexEncoder))
        result = export_func(datum)
        if result['code'] == 0:
            if result['updated']:
                updated += 1
            else:
                ignored += 1
        else:
            errors.append({'error': result, 'source': datum})
    return {
        'update_at': datetime.now(),
        'ignored': ignored,
        'updated': updated,
        'errors_count': len(errors),
        'errors': errors
    }


def import_data(filepath, list_func, refactor_func, export_func=None) -> None:
    """
    Imports the result of the functions to destination json file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    update_at, content = datetime.combine(original_date, time_cls()), {}
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as fp:
            content: dict = json.load(fp)
        update_at = datetime.strptime(content['update_at'], '%Y-%m-%d %H:%M:%S.%f')

    updated = False
    if datetime.now() - update_at >= update_interval:
        data = [x.copy() for x in list_func()]
        for datum in data:
            refactor_func(datum)
        content = {
            'update_at': datetime.now(),
            'count': len(data),
            'data': data
        }
        updated = True
    if 'export' not in content and export_func is not None:
        content['export'] = export_data(content['data'], export_func)
        updated = True
    if updated:
        with open(filepath, 'w', encoding='utf-8') as fp:
            json.dump(content, fp, ensure_ascii=False, cls=ComplexEncoder)


def import_ordered_works(filepath, site: OrderedAdultSite, export_func=None) -> None:
    """
    Imports in-order works of the given site to destination json file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    start, stop, records = original_date, date.today(), []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as fp:
            records: List[dict] = json.load(fp)
        start = date.fromisoformat(records[0]['stop'])

    updated = False
    if stop - start >= update_interval:
        works = [x.copy() for x in site.list_works_between(start, stop)]
        for work in works:
            site.refactor_work(work)
        record = {
            'update_at': datetime.now(),
            'start': start,
            'stop': stop,
            'count': len(works),
            'data': works
        }
        records.insert(0, record)
        updated = True
    for record in records:
        if 'export' not in record and export_func is not None:
            record['export'] = export_data(record['data'], export_func)
            updated = True
    if updated:
        with open(filepath, 'w', encoding='utf-8') as fp:
            json.dump(records, fp, ensure_ascii=False, cls=ComplexEncoder)


def import_monthly_works(filepath, site: MonthlyAdultSite, export_func=None) -> None:
    """
    Imports monthly works of the given site to destination json file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    start, stop, records = site.start_month, YearMonth.now(), []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as fp:
            records: List[dict] = json.load(fp)
        start = YearMonth.parse(records[0]['stop'])

    updated = False
    if start < stop:
        works = [x.copy() for x in site.list_works_between(start, stop)]
        for work in works:
            site.refactor_work(work)
        record = {
            'update_at': datetime.now(),
            'start': str(start),
            'stop': str(stop),
            'count': len(works),
            'data': works
        }
        records.insert(0, record)
        updated = True
    for record in records:
        if 'export' not in record and export_func is not None:
            record['export'] = export_data(record['data'], export_func)
            updated = True
    if updated:
        with open(filepath, 'w', encoding='utf-8') as fp:
            json.dump(records, fp, ensure_ascii=False, cls=ComplexEncoder)


def validate_works(works: List[dict], sn_regexp: Pattern, ordered=True) -> bool:
    """
    Validates properties of given works.
    """
    all_valid = True
    log.debug('# checking serial_numbers')
    for work in works:
        sn = work.get('serial_number')
        if sn is not None and sn_regexp.fullmatch(sn) is None:
            all_valid = False
            log.error('mismatched sn: ' + sn)

    if ordered:
        log.debug('# checking release dates')
        last_date = None
        for work in works:
            release_date = work.get('release_date')
            if release_date is None:
                log.error('no release date: ' + str(work))
            elif last_date is not None and last_date < release_date:
                log.error('not descending release date from [%s] to [%s]', last_date, release_date)
            last_date = release_date
    return all_valid
