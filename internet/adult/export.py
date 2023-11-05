#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Persist data.

@Author Kingen
"""
import json
import os
from datetime import timedelta

import common
from internet.adult import original_date
from internet.adult.ja import *

log = common.create_logger(__name__)

update_interval = timedelta(days=7)
name_regexp = re.compile('[\\sA-Za-z\u0800-\u4e00\u4e00-\u9fa5]{1,6}')
measurements_regexp = re.compile('B(--|\\d{2,3})\\([-A-Z]\\)/W(--|\\d{2,3})/H(--|\\d{2,3})')


def validate_actors(actors: List[dict]):
    """
    Validates properties of given actors.
    """
    log.debug('# checking names')
    error_names: set = set()
    for actor in actors:
        name = actor.get('name')
        if name is None or name.strip() == '':
            log.error('no actor name: ' + str(actor))
        if not isinstance(name, str) or name_regexp.fullmatch(name) is None:
            error_names.add(name)
    for name in sorted(error_names, key=lambda x: len(x)):
        log.error('mismatched actor name: ' + name)

    log.debug('# checking birthdays')
    for actor in actors:
        birthday = actor.get('birthday')
        if birthday is None or isinstance(birthday, date):
            continue
        try:
            date.fromisoformat(str(birthday))
        except Exception:
            log.error('illegal birthday: ' + str(birthday))

    log.debug('# checking heights')
    for actor in actors:
        height = actor.get('height')
        if height is not None and (not isinstance(height, int) or height < 100 or height > 200):
            log.error('illegal height: ' + str(height))

    log.debug('# checking weights')
    for actor in actors:
        weight = actor.get('weight')
        if weight is not None and (not isinstance(weight, int) or weight < 30 or weight > 100):
            log.error('illegal weight: ' + str(weight))

    log.debug('# checking measurements')
    for actor in actors:
        measurements = actor.get('measurements')
        if measurements is not None and measurements_regexp.fullmatch(measurements) is None:
            log.error('mismatched measurements: ' + measurements)

    log.debug('# checking sources')
    for actor in actors:
        source = actor.get('source')
        if source is None or source.strip() == '':
            log.error('no source: ' + str(actor))


def validate_works(works: List[dict], sn_exp, ordered=True):
    """
    Validates properties of given works.
    """
    log.debug('# checking producers')
    ps = {}
    for work in works:
        prod = work.get('producer')
        if prod is None:
            log.error('no producer: ' + str(work))
        else:
            ps[prod] = ps.get(prod, 0) + 1
    log.info('all producers: ')
    for p, c in sorted(ps.items(), key=lambda x: x[1]):
        log.info(f'{p}: {c}')

    log.debug('# checking titles and serial_numbers')
    sn_regexp = re.compile(sn_exp)
    for work in works:
        title, sn = work.get('title'), work.get('serial_number')
        if title is None and sn is None:
            log.error('no work title or sn: ' + str(work))
        if sn is not None and sn_regexp.fullmatch(sn) is None:
            log.error('mismatched sn: ' + sn)

    log.debug('# checking durations')
    for work in works:
        duration = work.get('duration')
        if duration is not None and (not isinstance(duration, int) or duration < 1 or duration > 180000):
            log.error('illegal duration: ' + str(duration) + ', sn=' + work['serial_number'])

    log.debug('# checking release dates')
    for work in works:
        release_date = work.get('release_date')
        if ordered and release_date is None:
            log.error('no release date: ' + str(work))
            continue
        if release_date is None or isinstance(release_date, date):
            continue
        try:
            date.fromisoformat(str(release_date))
        except Exception:
            log.error('illegal release date: ' + str(release_date))
    if ordered:
        for i in range(1, len(works)):
            if works[i - 1]['release_date'] < works[i]['release_date']:
                log.error('not descending release date at ' + str(works[i - 1]['release_date']))

    log.debug('# checking genres')
    all_genres = set()
    for work in works:
        genres = work.get('genres')
        if genres is not None:
            all_genres.update(genres)
    log.info('all genres: ' + str(sorted(all_genres, key=lambda x: len(x))))

    log.debug('# checking sources')
    for work in works:
        source = work.get('source')
        if source is None or source.strip() == '':
            log.error('no source: ' + str(work))

    log.debug('# checking actors')
    error_actors = set()
    for work in works:
        actors = work.get("actors")
        if actors is None:
            continue
        for actor in actors:
            if not isinstance(actor, str) or name_regexp.fullmatch(actor) is None:
                error_actors.add(actor)
    for name in sorted(error_actors, key=lambda x: len(x)):
        log.error('mismatched actor name: ' + name)


def export_data(filepath, list_func, refactor_func):
    """
    Exports the result of the functions to destination json file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as fp:
            content: dict = json.load(fp)
        update_at = datetime.strptime(content['update_at'], '%Y-%m-%d %H:%M:%S.%f')
        if datetime.now() - update_at < update_interval:
            return content['data']
    data = [x.copy() for x in list_func()]
    for datum in data:
        refactor_func(datum)
    content = {
        'update_at': datetime.now(),
        'count': len(data),
        'data': data
    }
    with open(filepath, 'w', encoding='utf-8') as fp:
        json.dump(content, fp, ensure_ascii=False, cls=common.ComplexEncoder)
    return data


def export_actors(producer: ActorProducer, filepath):
    """
    Exports actors of the given site to destination json file.
    """
    return export_data(filepath, lambda: producer.list_actors(), lambda x: producer.refactor_actor(x))


def export_works(producer: AdultProducer, filepath):
    """
    Exports works of the given site to destination json file.
    """
    return export_data(filepath, lambda: producer.list_works(), lambda x: producer.refactor_work(x))


def export_ordered_works(producer: OrderedAdultProducer, filepath):
    """
    Exports in-order works of the given site to destination json file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    start, stop, records = original_date, date.today(), []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as fp:
            records: List[dict] = json.load(fp)
        start = date.fromisoformat(records[0]['stop'])
    if stop - start < update_interval:
        return records[0]['data']
    works = [x.copy() for x in producer.list_works_between(start, stop)]
    for work in works:
        producer.refactor_work(work)
    record = {
        'update_at': datetime.now(),
        'start': start,
        'stop': stop,
        'count': len(works),
        'data': works
    }
    records.insert(0, record)
    with open(filepath, 'w', encoding='utf-8') as fp:
        json.dump(records, fp, ensure_ascii=False, cls=common.ComplexEncoder)
    return works


def export_monthly_works(producer: MonthlyAdultProducer, filepath):
    """
    Exports monthly works of the given site to destination json file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    start, stop, records = producer.start_month, YearMonth.now(), []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as fp:
            records: List[dict] = json.load(fp)
        start = YearMonth.parse(records[0]['stop'])
    if start >= stop:
        return records[0]['data']
    works = [x.copy() for x in producer.list_works_between(start, stop)]
    for work in works:
        producer.refactor_work(work)
    record = {
        'update_at': datetime.now(),
        'start': str(start),
        'stop': str(stop),
        'count': len(works),
        'data': works
    }
    records.insert(0, record)
    with open(filepath, 'w', encoding='utf-8') as fp:
        json.dump(records, fp, ensure_ascii=False, cls=common.ComplexEncoder)
    return works


def export_producer(producer: AdultProducer, dirpath, sn_exp):
    log.info('Start exporting actors and works of %s', producer.name)
    producer_name = producer.name
    if isinstance(producer, ActorProducer):
        actors = export_actors(producer, os.path.join(dirpath, 'actor', producer_name + '.json'))
        validate_actors(actors)

    if isinstance(producer, OrderedAdultProducer):
        works = export_ordered_works(producer, os.path.join(dirpath, 'work', producer_name + '.json'))
        validate_works(works, sn_exp)
    elif isinstance(producer, MonthlyAdultProducer):
        works = export_monthly_works(producer, os.path.join(dirpath, 'work', producer_name + '.json'))
        validate_works(works, sn_exp)
    else:
        works = export_works(producer, os.path.join(dirpath, 'work', producer_name + '.json'))
        validate_works(works, sn_exp, ordered=False)
    return works


if __name__ == '__main__':
    for site in will_producers:
        export_producer(site, 'tmp/will', sn_exp='[A-Z]{2,6}-\\d{3}')

    export_producer(prestige, 'tmp', sn_exp='[A-Z]{3,7}-\\d{3}')
    export_producer(sod_prime, 'tmp', sn_exp='[A-Z\\d]{2,7}-\\d{3,5}(-\\d+|-?[A-Z])?')

    for site in d2pass_producers:
        export_producer(site, 'tmp/d2pass', sn_exp='(\\d{6}[-_]\\d{3}|KIN8-\\d{4})')

    for site in other_producers:
        export_producer(site, 'tmp/other', sn_exp='[A-Z]{3,5}-\\d{2,4}')
