""" Search and manage video

@Author Kingen
@Date 2020/4/13
"""
import base64
import json
import math
import os
import re
import sys
from itertools import groupby
from operator import itemgetter
from sqlite3 import *
from urllib import request, parse, error

import bs4
from moviepy.video.io.VideoFileClip import VideoFileClip

from file.resource import VideoSearch
from internet.spider import IDM, do_request, get_soup, pre_download
from utils import config

logger = config.get_logger(__name__)


class Douban:
    """
    Refer to <https://eastsunrise.gitee.io/wiki-kingen/dev/apis/douban.html>.
    Functions whose names start with 'collect' is an extension to get all data once.
    Json files in the 'douban' directory are examples  for each functions
    """
    COUNT = 20
    START_DATE = '2005-03-06'

    def __init__(self, api_key, pause=12) -> None:
        self.__api_key = api_key
        self.__base_params = {
            'apikey': self.__api_key
        }
        self.__headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
        }
        self.__pause = pause

    def __get_url(self, path, netloc_cat='api', path_params=None, query_params=None):
        """
        get a full encoded url by join netloc and href
        """
        netloc = '%s.douban.com' % netloc_cat
        if netloc_cat == 'api':
            if query_params is None:
                query_params = self.__base_params
            else:
                query_params.update(self.__base_params)
        if path_params is not None:
            path = path.format(**path_params)
        query = parse.urlencode(query_params) if query_params is not None else ''
        return parse.urlunsplit(('https', netloc, path, query, None))

    def collect_my_movies(self, my_id, cookie, start_date=START_DATE):
        """
        collect my movies data since start_date with cookie got manually.
        :return: {'<id>': {<simple-subject>},...}
        """
        subjects = {}
        for record_cat in ['wish', 'do', 'collect']:
            start = 0
            while True:
                done = False
                records = self.user_collection_with_cookie(cookie, my_id, catalog='movie', record_cat=record_cat, sort_by='time', start=start)
                for subject in records['subjects']:
                    if subject['tag_date'] >= start_date:
                        subjects[subject['id']] = subject
                    else:
                        done = True
                        break
                start += records['count']
                if start >= records['total'] or done:
                    break
        return subjects

    def collect_hit_movies(self):
        """
        collect current hit movies
        :return: {'<id>': {<simple-subject>},...}
        """
        start = 0
        movies = {}
        while True:
            data = self.movie_in_theaters(start=start)
            for subject in data['subjects']:
                if subject['id'] not in movies:
                    movies[subject['id']] = subject
            start += data['count']
            if start >= data['total']:
                break

        data = self.movie_new_movies()
        for subject in data['subjects']:
            if subject['id'] not in movies:
                movies[subject['id']] = subject

        data = self.movie_weekly()
        for subject in [subject['subject'] for subject in data['subjects']]:
            if subject['id'] not in movies:
                movies[subject['id']] = subject

        return movies

    def user_collection_with_cookie(self, cookie, user_id, catalog='movie', record_cat='wish', sort_by='time', start=0):
        """
        Get user records with cookie
        :param cookie: got through logging in manually
        :param user_id:
        :param catalog: movie/book/music/..
        :param record_cat: wish/do/collect
        :param sort_by: time/rating/title
        :param start: start index
        :return: {
                    'start': start, 'count': count, 'total': total,
                    'subjects': [{'id': id, 'title': title, 'aka': aka, 'alt': alt, 'tag_date': '2010-01-01', 'status': status},...]
                }
        """
        url = self.__get_url(path='/people/{id}/{cat}', netloc_cat=catalog, path_params={
            'id': user_id,
            'cat': record_cat
        }, query_params={
            'sort': sort_by,
            'start': start,
            'mode': 'list'
        })
        headers = {
            'Cookie': cookie
        }
        headers.update(self.__headers)
        soup = get_soup(request.Request(url, headers=headers, method='GET'), pause=self.__pause)
        results = []
        for li in soup.find('ul', class_='list-view').find_all('li'):
            div = li.div.div
            mov_a = div.a
            titles = [title.strip() for title in mov_a.get_text().strip().split('/')]
            results.append({
                'id': os.path.split(mov_a['href'].strip('/'))[1],
                'title': titles[0],
                'aka': titles[1:],
                'alt': mov_a['href'],
                'tag_date': div.find_next('div').get_text().strip(),
                'status': record_cat
            })
        num_str = soup.find('span', class_='subject-num').get_text().strip()
        nums = [int(part) for part in re.split('[/-]', num_str)]
        return {
            'start': nums[0] - 1,
            'count': nums[1] - nums[0] + 1,
            'total': nums[2],
            'subjects': results
        }

    def movie_subject(self, subject_id):
        return self.__get_result('/v2/movie/subject/{id}', {'id': subject_id})

    def movie_subject_with_cookie(self, subject_id, cookie, title=None):
        """
        This is a backup for movies that can't be found by self.movie_subject().
        The movie is probably x-rated and restricted to be accessed only after logging in.

        :param title: Combined title is returned instead of title if title isn't specified.
                    Otherwise, split combined title and return title and original_title.
        :return:
        """
        url = self.__get_url('/subject/{id}', 'movie', path_params={'id': subject_id})
        soup = get_soup(request.Request(url, headers=dict(self.__headers, Cookie=cookie), method='GET'), pause=self.__pause)
        wrapper = soup.find('div', id='wrapper')
        subject = {}

        h1 = wrapper.find('h1')
        subject['combined_title'] = h1.find('span', property='v:itemreviewed').get_text().strip()
        if title is not None:
            subject['title'] = title
            subject['original_title'] = subject['combined_title'].replace(subject['title'], '', 1).strip()
            if subject['original_title'] == '':
                subject['original_title'] = subject['title']
        subject['year'] = h1.find('span', class_='year').get_text().strip().strip('()')

        spans = dict([(span_pl.get_text().strip(), span_pl) for span_pl in wrapper.find('div', id='info').find_all('span', class_='pl')])
        for pl in ['导演', '编剧', '主演']:
            if pl in spans:
                celebrities = []
                for celebrity_a in spans[pl].find_next('span', class_='attrs').find_all('a'):
                    celebrities.append({
                        'name': celebrity_a.get_text().strip(),
                        'alt': self.__get_url(parse.unquote(celebrity_a['href']), netloc_cat='movie')
                    })
                celebrity_key = 'directors' if pl == '导演' else 'writers' if pl == '编剧' else 'casts'
                subject[celebrity_key] = celebrities
        subject['genres'] = [span.get_text().strip() for span in spans['类型:'].find_all_next('span', property='v:genre')]
        subject['countries'] = [name.strip() for name in str(spans['制片国家/地区:'].next_sibling).split('/')]
        subject['languages'] = [name.strip() for name in str(spans['语言:'].next_sibling).split('/')]
        subject['aka'] = [name.strip() for name in str(spans['又名:'].next_sibling).split(' / ')]
        if '上映日期:' in spans:
            subject['subtype'] = 'movie'
            subject['pubdates'] = [span['content'] for span in spans['上映日期:'].find_all_next('span', property='v:initialReleaseDate')]
            span = spans['片长:'].find_next('span', property='v:runtime')
            subject['durations'] = [span.get_text().strip()]
            if not isinstance(span.next_sibling, bs4.Tag):
                subject['durations'] += [d.strip() for d in str(span.next_sibling).strip('/').split('/')]
            subject['current_season'] = None
            subject['seasons_count'] = None
            subject['episodes_count'] = None
        elif '首播:' in spans:
            subject['subtype'] = 'tv'
            subject['pubdates'] = [span['content'] for span in spans['首播:'].find_all_next('span', property='v:initialReleaseDate')]
            subject['durations'] = [x.strip() for x in str(spans['单集片长:'].next_sibling).split('/')]
            subject['episodes_count'] = str(spans['集数:'].next_sibling).strip()
            if '季数:' in spans:
                next_sibling = spans['季数:'].next_sibling
                if isinstance(next_sibling, bs4.NavigableString):
                    subject['current_season'] = str(next_sibling)
                    subject['seasons_count'] = None
                elif isinstance(next_sibling, bs4.Tag) and next_sibling.name == 'select':
                    subject['current_season'] = next_sibling.find('option', selected='selected').get_text().strip()
                    subject['seasons_count'] = len(next_sibling.find_all('option'))
                else:
                    logger.error('Info of seasons is not specified.')
                    raise ValueError
            else:
                subject['current_season'] = None
                subject['seasons_count'] = None
        else:
            logger.error('Subtype is not specified.')
            raise ValueError

        if '官方网站:' in spans:
            subject['website'] = spans['官方网站:'].find_next('a')['href']
        if 'IMDb链接:' in spans:
            subject['imdb'] = spans['IMDb链接:'].find_next('a')['href']

        return subject

    def movie_subject_photos(self, subject_id, start=0, count=20):
        return self.__get_result('/v2/movie/subject/{id}/photos', {'id': subject_id}, {'start': start, 'count': count})

    def movie_subject_reviews(self, subject_id, start=0, count=20):
        return self.__get_result('/v2/movie/subject/{id}/reviews', {'id': subject_id}, {'start': start, 'count': count})

    def movie_subject_comments(self, subject_id, start=0, count=20):
        return self.__get_result('/v2/movie/subject/{id}/comments', {'id': subject_id}, {'start': start, 'count': count})

    def movie_celebrity(self, celebrity_id):
        return self.__get_result('/v2/movie/celebrity/{id}', {'id': celebrity_id})

    def movie_celebrity_photos(self, celebrity_id, start=0, count=20):
        return self.__get_result('/v2/movie/celebrity/{id}/photos', {'id': celebrity_id}, {'start': start, 'count': count})

    def movie_celebrity_works(self, celebrity_id, start=0, count=20):
        return self.__get_result('/v2/movie/celebrity/{id}/works', {'id': celebrity_id}, {'start': start, 'count': count})

    def movie_top250(self, start=0, count=COUNT):
        return self.__get_result('/v2/movie/top250', query_params={
            'start': start,
            'count': count
        })

    def movie_weekly(self):
        return self.__get_result('/v2/movie/weekly')

    def movie_new_movies(self):
        return self.__get_result('/v2/movie/new_movies')

    def movie_in_theaters(self, start=0, count=COUNT, city='北京'):
        """
        :param city: name or number id of the city
        """
        return self.__get_result('/v2/movie/in_theaters', query_params={
            'start': start,
            'count': count,
            'city': city
        })

    def movie_coming_soon(self, start=0, count=COUNT):
        return self.__get_result('/v2/movie/coming_soon', query_params={
            'start': start,
            'count': count
        })

    def __get_result(self, relative_url, path_params=None, query_params=None):
        url = self.__get_url(path=relative_url, netloc_cat='api', path_params=path_params, query_params=query_params)
        req = request.Request(url, headers=self.__headers, method='GET')
        return json.loads(do_request(req, self.__pause), encoding='utf-8')


class VideoManager:
    VIDEO_SUFFIXES = ('.avi', '.rmvb', '.mp4', '.mkv')
    CHINESE = ['汉语普通话', '粤语', '闽南语', '河南方言', '贵州方言', '贵州独山话']
    PROTOCOLS = ['http', 'ftp', 'ed2k', 'magnet', 'pan', 'torrent']
    standard_kbps = 2500  # kb/s
    JUNK_SITES = ['yutou.tv', '80s.la', '80s.im', 'bt.2tu.cc', 'bofang.cc:']

    def __init__(self, db, cdn, idm_exe='IDMan.exe') -> None:
        register_adapter(list, lambda x: '[%s]' % '_'.join(x))
        register_converter('list', lambda x: x.decode('utf-8').strip('[]').split('_'))
        self.__db = db
        self.cdn = cdn
        self.__idm = IDM(idm_exe, self.cdn)

    @property
    def cdn(self):
        return self.__cdn

    @cdn.setter
    def cdn(self, cdn):
        if not os.path.isdir(cdn):
            cdn = './'
        self.__cdn = cdn

    def __get_connection(self):
        c = connect(self.__db, 30, detect_types=PARSE_DECLTYPES)
        c.row_factory = Row
        c.set_trace_callback(lambda x: logger.info('Execute: %s' % x))
        return c

    def update_my_movies(self, douban: Douban, user_id, cookie, start_date=None):
        """
        Update my collected movies from Douban to database.

        If not exist in db, get full info and insert into db, with archived set to 0.
        If exists, update status and tag_date.

        :param douban: an instance of Douban client
        :param start_date: when tag_date start
        """
        logger.info('Start updating movies.')
        connection = self.__get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT id FROM movies')
        ids = [m['id'] for m in cursor.fetchall()]
        for subject_id, subject in douban.collect_my_movies(user_id, cookie, start_date=start_date).items():
            if int(subject_id) in ids:
                cursor.execute('UPDATE movies SET status=?, tag_date=?, last_update=DATETIME(\'now\') WHERE id = ?',
                               (subject['status'], subject['tag_date'], int(subject_id)))
                if cursor.rowcount != 1:
                    logger.error('Failed to update movie: %s. ROLLBACK!' % subject['title'])
                    connection.rollback()
                else:
                    logger.info('Update movie: %s' % subject['title'])
                    connection.commit()
            else:
                try:
                    subject.update(douban.movie_subject(subject_id))
                except error.HTTPError as e:
                    if e.code == 404:
                        subject.update(douban.movie_subject_with_cookie(subject_id, cookie, subject['title']))
                # default: last_update = now(), archived = 0
                cursor.execute('INSERT INTO movies(id, title, alt, status, tag_date, original_title, aka, subtype, languages, '
                               'year, durations, current_season, episodes_count, seasons_count, last_update, archived) '
                               'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATETIME(\'now\'), 0)',
                               ([subject[key] for key in [
                                   'id', 'title', 'alt', 'status', 'tag_date', 'original_title', 'aka', 'subtype', 'languages',
                                   'year', 'durations', 'current_season', 'episodes_count', 'seasons_count'
                               ]]))
                if cursor.rowcount != 1:
                    logger.error('Failed to Add movie: %s. ROLLBACK!' % subject['title'])
                    connection.rollback()
                else:
                    logger.info('Add movie: %s' % subject['title'])
                    connection.commit()
        logger.info('Finish updating movies, %d movies changed.' % connection.total_changes)
        connection.close()

    def __collect_subject(self, subject, connection, *sites: VideoSearch):
        cursor = connection.cursor()
        subject_id, title, subtype = subject['id'], subject['title'], subject['subtype']
        path, filename = self.__get_location(subject=subject)
        if subtype == 'tv' and os.path.isdir(os.path.join(path, filename)):
            logger.info('File exists for the subject %s: %s' % (title, os.path.join(path, filename)))
            return True
        elif subtype == 'movie' and os.path.isdir(path):
            with os.scandir(path) as sp:
                for f in sp:
                    if f.is_file() and os.path.splitext(f.name)[0] == filename:
                        logger.info('File exists for the subject %s: %s' % (title, os.path.join(path, f.name)))
                        return True

        # search resources
        for site in sites:
            logger.info('Searching %s for %s, %s' % (site.name, title, subject['alt']))
            links, excluded_ones = site.search(subject)

            # filter
            resources = []
            for url, remark in links.items():
                p, u = classify_url(url)
                if p != 'http':
                    continue
                if any([u.find(x) >= 0 for x in self.JUNK_SITES]):
                    continue
                ext = os.path.splitext(u)[1]  # todo get from response
                if ext not in self.VIDEO_SUFFIXES:
                    continue
                resources.append({'url': u, 'ext': ext})
            if len(resources) == 0:
                logger.info('No resources on %s found.' % site.name)
                continue
            if subtype == 'movie':
                for r in resources:
                    code, msg, args = pre_download(r['url'])
                    if code == 200:
                        r['weight'] = self.weight_video_file([int(re.findall(r'\d+', d)[0]) for d in subject['durations']],
                                                             size=args['size'], ext=r['ext'])
                    else:
                        r['weight'] = -1
                chosen = max(resources, key=lambda x: x['weight'])
                if chosen['weight'] < 0:
                    logger.info('No qualified resources.')
                    continue
                os.makedirs(path, exist_ok=True)
                filename += chosen['ext']
                logger.info('Add task of %s, downloading from %s to %s' % (filename, chosen['url'], path))
                self.__idm.add_task(chosen['url'], path, filename)
            else:
                episodes_count = subject['episodes_count']
                for r in resources:
                    t, s = parse.splittype(r['url'])
                    h, p = parse.splithost(s)
                    h = '%s://%s' % (t, h)
                    r['head'], r['path'] = h, p
                urls = [None] * (episodes_count + 1)
                for length, xs in groupby(sorted(resources, key=lambda x: len(x['path'])), key=lambda x: len(x['path'])):
                    for head, ys in groupby(sorted(xs, key=lambda x: x['head']), key=lambda x: x['head']):
                        rs = list(ys)
                        if len(rs) == 1:
                            p0 = rs[0]['path']
                            if os.path.splitext(p0)[0].endswith('%dend' % episodes_count):
                                url0 = rs[0]['head'] + p0
                                c, msg, args = pre_download(url0)
                                if c == 200:
                                    urls[episodes_count] = url0
                            continue
                        commons, ds = cmp_strings([r['path'] for r in rs])
                        for i, c in enumerate(commons[:-1]):
                            ed = re.search(r'\d+$', c)
                            if ed is not None:
                                commons[i] = c[:ed.start()]
                                for d in ds:
                                    d[i] = c[ed.start():] + d[i]
                        for i, c in enumerate(commons[1:]):
                            sd = re.search(r'^\d+', c)
                            if sd is not None:
                                commons[i] = c[sd.end():]
                                for d in ds:
                                    d[i] = d[i] + c[:sd.end()]
                        del_count = 0
                        for i, c in enumerate(commons[1:-1]):
                            if c == '':
                                for d in ds:
                                    d[i] = d[i] + c + d[i + 1]
                                    del d[i + 1 - del_count]
                                del commons[i + 1 - del_count]
                                del_count += 1
                        if any((not d[-1].isdigit() or int(d[-1]) > episodes_count) for d in ds):
                            continue
                        if any((len(d) > 2 or not d[0].isdigit()) for d in ds):
                            continue
                        gs = {}  # format-episodes
                        if any(len(set(d)) > 1 for d in ds):
                            phs = 1
                            for k, es in groupby(sorted(ds, key=itemgetter(0)), key=lambda x: d[0]):
                                es = [d[-1] for d in es]
                                pf = commons[0] + k + '%d'.join(commons[1:])
                                gs[pf] = gs.get(pf, []) + es
                        else:
                            phs = len(ds[0])
                            pf = '%d'.join(commons)
                            gs[pf] = gs.get(pf, []) + [d[0] for d in ds]
                        for pf, es in gs.items():
                            uf = head + pf
                            els = [len(e) for e in es]
                            min_d = min(els)
                            if min_d == max(els):
                                uf = uf.replace('%d', '%%0%dd' % min_d)
                            es = [int(e) for e in es]
                            start, end = min(es), max(es)

                            # compute bounds of episodes
                            code_s, msg, args = pre_download(uf % tuple([1] * phs), pause=3)
                            if code_s == 200:
                                start = 1
                            else:
                                left = self.__compute_limit(2, start, uf, phs, True)
                                if left > start:
                                    continue
                                start = left
                            code_e, msg, args = pre_download(uf % tuple([episodes_count] * phs), pause=3)
                            if code_e == 200:
                                end = episodes_count + 1
                            else:
                                left = self.__compute_limit(end, episodes_count - 1, uf, phs, False)
                                if left <= end:
                                    continue
                                end = left
                            for i in range(start, end):
                                urls[i] = uf % tuple([i] * phs)
                urls = urls[1:]
                empties = [str(i + 1) for i, x in enumerate(urls) if x is None]
                if len(empties) > 0:
                    logger.info('Not enough episodes for %s, total: %d, lacking: %s' % (subject['title'], episodes_count, ', '.join(empties)))
                    continue
                logger.info('Add tasks of %s, %d episodes.' % (subject['title'], episodes_count))
                path = os.path.join(path, filename)
                os.makedirs(path, exist_ok=True)
                episode = 'E%%0%dd%%s' % math.ceil(math.log10(episodes_count + 1))
                for i, url in enumerate(urls):
                    self.__idm.add_task(url, path, episode % ((i + 1), os.path.splitext(url)[1]))
            cursor.execute('UPDATE movies SET archived = 2, location = null, last_update = DATETIME(\'now\')'
                           'WHERE id = ?', (subject_id,))
            if cursor.rowcount != 1:
                logger.error('Failed to update movie: %d. ROLLBACK!' % subject_id)
                connection.rollback()
                continue
            logger.info('Resources searched for %s. Downloading...' % title)
            connection.commit()
            return True
        logger.info('No resources found for %s' % title)
        return False

    def collect_subject(self, subject_id: int, *sites: VideoSearch):
        """
        Search and download resources for subject specified by id. There  steps as commented.
        :param subject_id:
        :return:
        """
        con = self.__get_connection()
        cursor = con.cursor()

        # get base info of the subject
        cursor.execute('SELECT * FROM movies WHERE id = ?', (subject_id,))
        result = cursor.fetchone()
        if result is None:
            logger.info('No subject with id %d' % subject_id)
            return False
        r = self.__collect_subject(dict(result), con, *sites)
        con.close()
        return r

    def collect_subjects(self, no_resources_file='', *sites: VideoSearch):
        con = self.__get_connection()
        cursor = con.cursor()
        cursor.execute('SELECT * FROM movies WHERE archived = 0')
        if os.path.exists(no_resources_file):
            with open(no_resources_file, 'r', encoding='utf-8') as fp:
                no_resources_ids = [int(line.split(', ')[0]) for line in fp.read().strip('\n').split('\n')[1:]]
            no_resources_fp = open(no_resources_file, 'a', encoding='utf-8')
        else:
            no_resources_ids = []
            no_resources_fp = sys.stdout
        results = [dict(x) for x in cursor.fetchall() if x['id'] not in no_resources_ids]
        total, success = len(results), 0
        for i, x in enumerate(results):
            logger.info('Collecting subject: %s, %d/%d.' % (x['title'], i + 1, total))
            if self.__collect_subject(x, con, *sites):
                success += 1
            else:
                no_resources_fp.write('\n%d, %s' % (x['id'], x['title']))
                no_resources_fp.flush()
        logger.info('Finish collecting, total: %d, success: %d, fail: %d.' % (total, success, total - success))
        no_resources_fp.close()
        con.close()
        return success

    def search_resources(self, sites: list, no_resources_file='', protocols=None):
        """
        Search resources of movies which are unarchived or without valid(to_add/downloading/abandoned/done) resources,
        and then add to database.

        Record movies that none resources are found for to a text file if specified, including excluded resources if any.
        :param no_resources_file: file to record movies that nothing is found for, with header: id, title, excluded_resources.
                                Use sys.stdout by default.
        :param sites: instances of class VideoSearch, representing websites to search on
        :param protocols: permitted protocols
        :return:
        """
        logger.info('Start searching resources.')
        connection = self.__get_connection()
        cursor = connection.cursor()
        if os.path.exists(no_resources_file):
            with open(no_resources_file, 'r', encoding='utf-8') as fp:
                no_resources_ids = [int(line.split(', ')[0]) for line in fp.read().strip('\n').split('\n')[1:]]
            no_resources_fp = open(no_resources_file, 'a', encoding='utf-8')
        else:
            no_resources_ids = []
            no_resources_fp = sys.stdout

        # get movies unarchived or without valid(to_add/downloading/abandoned/done) resources
        cursor.execute('SELECT id, title, aka, subtype, alt, year, original_title, current_season, episodes_count '
                       'FROM movies WHERE id NOT IN '
                       '(SELECT movie_id FROM resources WHERE status >= 0 GROUP BY movie_id) AND archived <> 1')
        subjects = [x for x in cursor.fetchall() if x['id'] not in no_resources_ids]
        search_count, site_count, got_count = 0, len(sites), 0
        for i, subject in enumerate(subjects):
            title, subtype = subject['title'], subject['subtype']
            logger.info('Searching %d/%d: %s, %s' % (i + 1, len(subjects), title, subject['alt']))
            resources, excluded_resources = [], []
            for j in range(search_count, search_count + site_count):
                try:
                    site: VideoSearch = sites[j % site_count]
                    links, excluded_ones = site.search(subject)
                except error.HTTPError:
                    continue
                except error.URLError as e:
                    logger.error(e.reason)
                    continue
                resources = self.__url_filter(links, site.name, protocols, subject['subtype'], subject['episodes_count'])
                excluded_resources += excluded_ones
                if len(resources) > 0:
                    got_count += 1
                    search_count = j + 1
                    break
                logger.info('No links left for %s' % title)
            if len(resources) > 0:
                cursor.executemany('INSERT INTO resources(movie_id, protocol, url, filename, ext, size, '
                                   'status, msg, remark, source, last_update) '
                                   'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATETIME(\'now\')) ON CONFLICT DO NOTHING',
                                   [(subject['id'],) + x for x in resources])
                if cursor.rowcount != len(resources):
                    logger.error('Failed to add resources of movie %s. ROLLBACK!' % subject['title'])
                    connection.rollback()
                else:
                    logger.info('%d matched and added, count: %d' % (len(resources), cursor.rowcount))
                    connection.commit()
            else:
                no_resources_fp.write('\n%d, %s, %s' % (subject['id'], title,
                                                        ', '.join([er['name'] + ': ' + er['href'] for er in excluded_resources])))
                no_resources_fp.flush()
        no_resources_fp.close()
        logger.info('Finish searching resources of %d subjects, %d resources added for %d subjects.'
                    % (len(subjects), connection.total_changes, got_count))
        connection.close()

    def __url_filter(self, links, subtype, protocols, episodes_count, site_name=None):
        """
        Filter urls, getting the filename and extension by parsing a url, do pre-request to check its validation and get size of the file
        :param links: a url-remark dict
        :return: list of dict including keys: (protocol, url, filename, extension, size, status, msg, remark, source)
        """
        resources = []
        if len(links) == 0:
            return []
        if protocols is None:
            protocols = self.PROTOCOLS
        if subtype == 'movie':
            for url, remark in links.items():
                p, u = classify_url(url)
                if p not in protocols:
                    continue
                if p == 'http':
                    filename = os.path.basename(u)
                    ext = os.path.splitext(filename)[1]  # todo get from response
                    if ext not in self.VIDEO_SUFFIXES:
                        continue
                    code, msg, args = pre_download(u)
                    if code == 200:
                        resources.append((p, u, filename, ext, args['size'], 0, msg, remark, site_name))
                elif p == 'ed2k':
                    parts = u.split('|')
                    if parts[0] == 'ed2k://' and parts[1] == 'file':
                        filename = parts[2]
                        ext = os.path.split(filename)[1]
                        size = int(parts[3])
                        resources.append((p, u, filename, ext, size, 0, p, remark, site_name))
                elif p == 'ftp':
                    filename = os.path.basename(u)
                    ext = os.path.splitext(filename)[1]
                    if ext in self.VIDEO_SUFFIXES:
                        resources.append((p, u, filename, ext, None, 0, p, remark, site_name))
                elif p == 'pan' or p == 'magnet' or p == 'torrent':
                    resources.append((p, u, None, None, None, 0, p, remark, site_name))
        else:
            urls = {}
            for url, remark in links.items():
                p, u = classify_url(url)
                if p not in protocols:
                    continue
                if p != 'http':
                    continue
                filename = os.path.basename(u)
                ext = os.path.splitext(filename)[1]  # todo get from response
                if ext not in self.VIDEO_SUFFIXES:
                    continue
                urls[u] = (p, filename, ext, remark)

            # group urls according to length, host, and similarity
            singles = []
            url_formats = {}  # 'http...%d.mp4': (start_episode, end_episode, min_digits, max_digits)
            for length, us in groupby(sorted(urls.keys(), key=lambda y: len(y)), key=lambda y: len(y)):
                us = list(us)
                if len(us) == 1:
                    singles.append(us[0])
                    continue
                # by scheme://host
                gs = {}
                for u in us:
                    t, s = parse.splittype(u)
                    h, p = parse.splithost(s)
                    h = '%s://%s' % (t, h)
                    if h in gs:
                        gs[h].append(p)
                    else:
                        gs[h] = [p]

                for h, ps in gs.items():
                    if len(ps) == 1:
                        singles.append(h + ps[0])
                        continue
                    # extract common parts
                    commons, ds = cmp_strings(ps)
                    for i, c in enumerate(commons[:-1]):
                        ed = re.search(r'\d+$', c)
                        if ed is not None:
                            commons[i] = c[:ed.start()]
                            for d in ds:
                                d[i] = c[ed.start():] + d[i]
                    for i, c in enumerate(commons[1:]):
                        sd = re.search(r'^\d+', c)
                        if sd is not None:
                            commons[i] = c[sd.end():]
                            for d in ds:
                                d[i] = d[i] + c[:sd.end()]
                    del_count = 0
                    for i, c in enumerate(commons[1:-1]):
                        if c == '':
                            for d in ds:
                                d[i] = d[i] + c + d[i + 1]
                                del d[i + 1 - del_count]
                            del commons[i + 1 - del_count]
                            del_count += 1
                    if any((not d[-1].isdigit() or int(d[-1]) > episodes_count) for d in ds):
                        continue
                    if any((len(d) > 2 or not d[0].isdigit()) for d in ds):
                        singles.extend([h + p for p in ps])
                        continue
                    if any(len(set(d)) > 1 for d in ds):
                        for k, es in groupby(sorted(ds, key=lambda x: d[0]), key=lambda y: d[0]):
                            es = list(es)
                            episodes = [int(e[1]) for e in es]
                            digits = len(es[0][1])
                            uf = h + commons[0] + k + '%d'.join(commons[1:])
                            if uf not in url_formats:
                                url_formats[uf] = (min(episodes), max(episodes), digits, 1)
                            else:
                                s, e, digits0, phs = url_formats[uf]
                                url_formats[uf] = (min(min(episodes), s), max(max(episodes), e), digits if digits == digits0 else False, 1)
                    else:
                        uf = h + '%d'.join(commons)
                        episodes = [int(d[0]) for d in ds]
                        digits = len(ds[0][0])
                        if uf not in url_formats:
                            url_formats[uf] = (min(episodes), max(episodes), digits, len(commons) - 1)
                        else:
                            s, e, digits0, phs = url_formats[uf]
                            url_formats[uf] = (min(min(episodes), s), max(max(episodes), e), digits if digits == digits0 else False, phs)
            for u in singles:
                code, msg, args = pre_download(u, pause=5)
                if code == 200:
                    resources.append((urls[u][0], u, urls[u][1], urls[u][2], args['size'], 0, 'Unknown Format', urls[u][3], site_name))
            for uf, v in url_formats.items():
                start, end, digits, phs = v
                p = parse.splittype(uf)[0]
                filename = os.path.basename(uf)
                ext = os.path.splitext(filename)[1]
                if digits:
                    uf = uf.replace('%d', '%%0%dd' % digits)

                # compute start and end
                size_sum, size_count = 0, 0
                code_s, msg, args = pre_download(uf % tuple([1] * phs), pause=3)
                if code_s == 200:
                    start = 1
                    size_count += 1
                    size_sum += args['size']
                else:
                    start_l, start_r = 2, start
                    while start_l <= start_r:
                        start_m = (start_l + start_r) >> 1
                        code_s, msg, args = pre_download(uf % tuple([start_m] * phs), pause=10)
                        if code_s == 200:
                            start_r = start_m - 1
                            size_count += 1
                            size_sum += args['size']
                        else:
                            start_l = start_m + 1
                    if start_l > start:
                        continue
                    start = start_l
                # end episode
                code_e, msg, args = pre_download(uf % tuple([episodes_count] * phs), pause=3)
                if code_e == 200:
                    end = episodes_count + 1
                    size_count += 1
                    size_sum += args['size']
                else:
                    end_l, end_r = end, episodes_count - 1
                    while end_l <= end_r:
                        end_m = (end_l + end_r) >> 1
                        code_e, msg, args = pre_download(uf % tuple([end_m] * phs), pause=10)
                        if code_e == 200:
                            end_l = end_m + 1
                            size_count += 1
                            size_sum += args['size']
                        else:
                            end_r = end_m - 1
                    if end_l <= end:
                        continue
                    end = end_l

                resources.append((p, uf, None, ext, round(size_sum / size_count), 0, 'Formatted', '%d-%d-%d' % (start, end, phs), site_name))
        return resources

    def __compute_limit(self, left, right, uf, phs, is_equal):
        while left <= right:
            m = (left + right) >> 1
            code, msg, args = pre_download(uf % tuple([m] * phs), pause=10)
            if code == 200 ^ is_equal:
                left = m + 1
            else:
                right = m - 1
        return left

    def add_tasks(self):
        """
        Choose a url for each subject to add to queue of IDM.

        Compute weight of all urls of a subject, and choose one with the highest weight.
        For tv series, extract common part of urls and fill in numbers to get urls for all episodes of the tv series.
        The url of the first episode will be chosen to do computation as the sames steps as movies do.

        Downloaded files will be separately saved into respective directories named after id.
        """
        logger.info('Start adding download tasks to IDM.')
        connection = self.__get_connection()
        cursor = connection.cursor()

        # movies
        cursor.execute('SELECT r.id, r.movie_id, r.url, m.durations, r.size, r.ext, m.title, m.subtype, '
                       'm.languages, m.year, m.original_title '
                       'FROM resources r LEFT JOIN movies m on r.movie_id = m.id '
                       'WHERE r.status = ? and r.protocol = ? and m.subtype = ? AND m.archived = ? ORDER BY movie_id',
                       (0, 'http', 'movie', 0))
        task_count, unused, unqualified = 0, 0, 0
        for movie_id, resources in groupby([dict(x) for x in cursor.fetchall()], key=lambda x: x['movie_id']):
            resources = list(resources)
            subject = resources[0]
            for r in resources:
                weight = self.weight_video_file([int(re.findall(r'\d+', d)[0]) for d in r['durations']], size=r['size'], ext=r['ext'])
                if weight < 0:
                    r['status'], r['msg'] = -1, 'Unqualified Video File'
                    unqualified += 1
                else:
                    r['weight'] = weight
            resources.sort(key=lambda x: x['weight'] if 'weight' in x else -1, reverse=True)
            for i, r in enumerate(resources):
                if 'weight' in r:
                    if i == 0:
                        r['status'], r['msg'] = 1, 'downloading'
                        path, filename = self.__get_location(subject=subject)
                        os.makedirs(path, exist_ok=True)
                        filename += r['ext']
                        logger.info('Add task of %s, downloading from %s to %s' % (filename, r['url'], path))
                        self.__idm.add_task(r['url'], path, filename)
                        task_count += 1
                    else:
                        unused += 1
            cursor.executemany('UPDATE resources SET status = ?, msg = ?, last_update = DATETIME(\'now\') WHERE id = ?',
                               [(r['status'], r['msg'], r['id']) for r in resources])
            if cursor.rowcount != len(resources):
                logger.error('Failed to update resources of movie %s. ROLLBACK!' % subject['title'])
                connection.rollback()
            else:
                logger.info('Update resources of movie %s, count: %d' % (subject['title'], cursor.rowcount))
                connection.commit()
        logger.info('Finish adding tasks of movies: %d, added: %d, unused: %d, unqualified: %d'
                    % (connection.total_changes, task_count, unused, unqualified))

        # tv
        pass
        cursor.execute('SELECT r.id, r.url, r.movie_id, r.remark, m.episodes_count, m.title '
                       'FROM resources r LEFT JOIN movies m on r.movie_id = m.id '
                       'WHERE r.status = ? and protocol = ? and subtype = ? and msg = ? '
                       'ORDER BY movie_id', (0, 'http', 'tv', 'Formatted'))
        for tv_id, resources in groupby([dict(x) for x in cursor.fetchall()], key=lambda x: x['movie_id']):
            resources = list(resources)
            urls = [None] * (resources[0]['episodes_count'] + 1)
            for r in resources:
                parts = r['remark'].split('-')
                start, end, phs = int(parts[0]), int(parts[1]), int(parts[2])
                for i in range(start, end):
                    urls[i] = r['url'] % tuple([i] * phs)
            urls = urls[1:]
            empties = [str(i + 1) for i, x in enumerate(urls) if x is None]
            if len(empties) > 0:
                logger.info('Not enough episodes for %s, lacking: %s' % (resources[0]['title'], ', '.join(empties)))
                continue
            logger.info('Add tasks of %s, %d episodes.' % (resources[0]['title'], resources[0]['episodes_count']))

        connection.close()

    def archive(self, status=2):
        """
        Archive subjects.
        """
        con = self.__get_connection()
        cursor = con.cursor()
        cursor.execute('SELECT * FROM movies WHERE archived = ?', (status,))
        updates = []
        for subject in cursor.fetchall():
            path, filename = self.__get_location(subject)
            filepath = os.path.join(path, filename)
            if subject['subtype'] == 'tv' and os.path.isdir(filepath):
                if len(os.listdir(filepath)) == subject['episodes_count']:
                    updates.append((filepath, subject['id']))
            if subject['subtype'] == 'movie' and os.path.isdir(path):
                with os.scandir(path) as sp:
                    for f in sp:
                        if f.is_file() and os.path.splitext(f.name)[0] == filename:
                            updates.append((f.path, subject['id']))
        if len(updates) == 0:
            return
        cursor.executemany('UPDATE movies SET archived = 1, location = ?, last_update = DATETIME(\'now\') '
                           'WHERE id = ?', updates)
        if cursor.rowcount != len(updates):
            logger.error('Failed to update locations of subjects. ROLLBACK!')
            con.rollback()
        else:
            logger.info('%d subjects archived.' % len(updates))
            con.commit()
        con.close()

    def weight_video_file(self, movie_durations=None, size=-1, ext=None, video_duration=-1, filepath=''):
        """
        Calculate weight of a file for a movie. Larger the result is, more right the file is.
        Same properties from file have higher priority if file is specified.
        :param movie_durations: Unit: min
        :param size: B
        :param video_duration: Unit: min
        :return percent
        """
        ws = []
        if os.path.isfile(filepath):
            ext = os.path.splitext(filepath)[1]
        if ext is not None:
            if ext not in self.VIDEO_SUFFIXES:
                return -1
            else:
                ws.append(100 * (self.VIDEO_SUFFIXES.index(ext) + 1) / len(self.VIDEO_SUFFIXES))
                if os.path.isfile(filepath):
                    video_duration = VideoFileClip(filepath).duration / 60
                    size = os.path.getsize(filepath)
        if movie_durations is not None:
            if video_duration >= 0:
                for i, movie_duration in enumerate(sorted(movie_durations)):
                    if abs(movie_duration - video_duration) < 1:
                        ws.append(100 * (i + 1) / len(movie_durations))
                        break
                    if i == len(movie_durations) - 1:
                        return -1
                return -1
            if size >= 0:
                target_size = int(sum(movie_durations) / len(movie_durations) * 7680 * self.standard_kbps)
                if size < (target_size >> 1):
                    return -1
                elif size <= target_size:
                    ws.append(100 * (size / target_size))
                elif size <= (target_size << 1):
                    ws.append(100 * (target_size / size))
                else:
                    ws.append(200 * (target_size / size) ** 2)
        return sum(ws) / len(ws)

    def __get_location(self, subject):
        """
        Get location for the subject
        :param subject: required properties: subtype, languages, year, title, original_title
        :return: (dir, name). The name returned doesn't include an extension.
        """
        subtype = 'Movies' if subject['subtype'] == 'movie' else 'TV' if subject['subtype'] == 'tv' else 'Unknown'
        language = subject['languages'][0]
        language = '华语' if language in self.CHINESE else language
        filename = '%d_%s' % (subject['year'], subject['original_title'])
        if subject['title'] != subject['original_title']:
            filename += '_%s' % subject['title']
        # disallowed characters: \/:*?"<>|
        filename = re.sub(r'[\\/:*?"<>|]', '$', filename)
        return os.path.join(self.cdn, subtype, language), filename

    @staticmethod
    def __rename_episode_default(src_name, season_name=None):
        base_name, ext = os.path.splitext(src_name)
        return ((season_name + ' ') if season_name is not None else '') + 'E' + re.findall(r'\d+', src_name)[0].zfill(2) + ext

    @staticmethod
    def __rename_season_default(src_name):
        return 'S' + re.findall(r'\d+', src_name)[0].zfill(2)

    def rename_tv(self, src_dir, relative=True, rename_episode=__rename_episode_default, rename_season=__rename_season_default):
        """
        Rename names of the files in tv series.
        :param src_dir: source directory.
        :param relative: if src_dir is relative path
        :param rename_episode: function to rename each episode with the file name as the argument.
        :param rename_season: function to rename each season if it has more than one seasons.
        """
        if relative:
            src_dir = os.path.join(self.__cdn, src_dir)
        if not os.path.exists(src_dir):
            print("Source directory doesn't exist.")
            return

        for filename in os.listdir(src_dir):
            filepath = os.path.join(src_dir, filename)
            if os.path.isfile(filepath):
                dst_name = rename_episode(src_name=filename)
                dst_path = os.path.join(src_dir, dst_name)
                print("Rename from {} to {}.".format(filepath, dst_path))
                os.rename(filepath, dst_path)
            else:
                dst_season_name = rename_season(src_name=filename)
                for episode_name in os.listdir(filepath):
                    episode_path = os.path.join(filepath, episode_name)
                    dst_episode_name = rename_episode(src_name=episode_name, season_name=dst_season_name)
                    dst_episode_path = os.path.join(filepath, dst_episode_name)
                    print("Rename from {} to {}.".format(episode_path, dst_episode_path))
                    os.rename(episode_path, dst_episode_path)
                dst_season_path = os.path.join(src_dir, dst_season_name)
                print("Rename directory from {} to {}.".format(filepath, dst_season_path))
                os.rename(filepath, dst_season_path)


def cmp_strings(strings: list):
    """
    compare at least 2 strings with same length.
    :return: list of common parts, lists of different parts for string in strings separately
    """
    if strings is None or len(strings) < 2 or any((x is None or len(x) == 0 or len(x) != len(strings[0])) for x in strings):
        raise ValueError
    commons = ['']
    diff = [[] for i in range(len(strings))]
    last_common = True
    first_str: str = strings[0]
    for i in range(len(first_str)):
        if any(x[i] != first_str[i] for x in strings):
            if last_common:
                for d in diff:
                    d.append('')
                last_common = False
            for j, d in enumerate(diff):
                d[-1] += strings[j][i]
        else:
            if not last_common:
                commons.append('')
                last_common = True
            commons[-1] += first_str[i]
    return commons, diff


def separate_srt(src: str):
    """
    Separate the .srt file with two languages to separated files.
    :param src: the path of the source file. Every 4 lines form a segment and segments are split by a space line.
    """
    if os.path.isfile(src) and src.lower().endswith('.srt'):
        root, ext = os.path.splitext(src)
        with open(src, mode='r', encoding='utf-8') as file:
            with open(root + '_1' + ext, 'w', encoding='utf-8') as f1:
                with open(root + '_2' + ext, 'w', encoding='utf-8') as f2:
                    segment = []
                    for line in file.readlines():
                        if line != '\n':
                            segment.append(line)
                        else:
                            if len(segment) != 4:
                                print('Special lines in No. %s' % segment[0])
                            f1.writelines([
                                segment[0], segment[1], segment[2], '\n'
                            ])
                            f2.writelines([
                                segment[0], segment[1], segment[3], '\n'
                            ])
                            segment = []


def classify_url(url: str):
    """
    Classify and decode a url. Optional protocols: pan/ftp/http/ed2k/magnet/torrent/unknown
    :return: (protocol of url, decoded url)
    """
    if url.startswith('thunder://'):
        url = base64.b64decode(url[10:])
        try:
            url = url.decode('utf-8').strip('AAZZ')
        except UnicodeDecodeError as e:
            url = url.decode('gbk').strip('AAZZ')
    url = parse.unquote(url.rstrip('/'))

    if url.startswith('https://pan.baidu.com'):
        return 'pan', url
    if url.endswith('.torrent'):
        return 'torrent', url
    for head in ['ftp', 'http', 'ed2k', 'magnet']:
        if url.startswith(head):
            return head, url
    return 'unknown', url
