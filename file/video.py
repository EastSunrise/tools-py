""" Search and manage video

@Author Kingen
@Date 2020/4/13
"""
import json
import os
import re
import shutil
import sys
from itertools import groupby
from sqlite3 import *
from urllib import request, parse, error

import bs4
from moviepy.video.io.VideoFileClip import VideoFileClip

from file.resource import VideoSearch
from internet.spider import IDM, do_request, get_soup, classify_url, pre_download
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
    VIDEO_SUFFIXES = ('.avi', '.rmvb', '.mkv', '.mp4')
    standard_kbps = 2500  # bytes/s

    def __init__(self, db, cdn, idm_exe='IDMan.exe') -> None:
        register_adapter(list, lambda x: '[%s]' % '_'.join(x))
        register_converter('list', lambda x: x.decode('utf-8').strip('[]').split('_'))
        self.__db = db
        self.cdn = cdn
        temp_dir = os.path.join(self.cdn, '$temp')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        self.__temp_dir = temp_dir
        self.__idm = IDM(idm_exe, temp_dir)

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
        cursor.execute('SELECT id, title, aka, subtype, alt, year, original_title, current_season FROM movies WHERE id NOT IN '
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
                resources = self.__url_filter(links, site.name, protocols)
                excluded_resources += excluded_ones
                if len(resources) > 0:
                    got_count += 1
                    search_count = j + 1
                    break
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

    def __url_filter(self, links, site_name, protocols):
        """
        Filter urls, getting the filename and extension by parsing a url, do pre-request to check its validation and get size of the file
        :param links: a url-remark dict
        :return: list of (protocol, url, filename, extension, size, status, msg, remark, source)
        """
        resources = []
        if protocols is None:
            protocols = ['http', 'ftp', 'ed2k', 'magnet', 'pan']
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
            elif p == 'pan' or p == 'magnet':
                resources.append((p, u, None, None, None, 0, p, remark, site_name))
        return resources

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
        cursor.execute('SELECT r.id, r.movie_id, r.url, m.durations, m.subtype, r.size, r.ext, m.title '
                       'FROM resources r LEFT JOIN movies m on r.movie_id = m.id '
                       'WHERE r.status = ? and protocol = ? ORDER BY movie_id', (0, 'http'))
        task_count, abandoned, unqualified = 0, 0, 0
        for movie_id, resources in groupby([dict(x) for x in cursor.fetchall()], key=lambda x: x['movie_id']):
            resources = list(resources)
            if resources[0]['subtype'] == 'movie':
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
                            path = os.path.join(self.__temp_dir, '%d_%d' % (movie_id, r['id']))
                            if not os.path.isdir(path):
                                os.makedirs(path)
                            logger.info('Add task: %d from %s to %s' % (movie_id, r['url'], path))
                            self.__idm.add_task(r['url'], path)
                            task_count += 1
                        else:
                            r['status'], r['msg'] = 2, 'abandoned'
                            abandoned += 1
                cursor.executemany('UPDATE resources SET status = ?, msg = ? WHERE id = ?',
                                   [(r['status'], r['msg'], r['id']) for r in resources])
                if cursor.rowcount != len(resources):
                    logger.error('Failed to update resources of movie %s. ROLLBACK!' % resources[0]['title'])
                    connection.rollback()
                else:
                    logger.info('Update resources of movie %s, count: %d' % (resources[0]['title'], cursor.rowcount))
                    connection.commit()
            else:
                # group urls according to similarity
                # same scheme and netloc are required
                for length, rs in groupby(resources, key=lambda x: len(x['url'])):
                    pass
                groups = []
                for resource in resources:
                    grouped = False
                    s, o = parse.splittype(resource['url'])
                    n, p = parse.splithost(o)
                    head = s + '://' + n
                    for group in groups:
                        if head != group[0][0]:
                            continue
                        if len(p) != len(group[0][1]):
                            continue
                        first_common, cl, dl1, dl2 = cmp_strings(group[0][1], p)
                        if len(cl) > 3 or any([not x.isdigit() for x in dl1]):
                            continue
                        group.append((head, p, cl, dl1, dl2))
                        grouped = True
                        break
                    if not grouped:
                        groups.append([(head, p, [], [], [])])

        logger.info('Finish adding tasks: %d, added: %d, abandoned: %d, unqualified: %d'
                    % (connection.total_changes, task_count, abandoned, unqualified))
        connection.close()

    def archive(self):
        """
        Collect downloaded resources from $temp to my private video library.
        """
        con = self.__get_connection()
        cursor = con.cursor()
        cursor.execute('SELECT id FROM movies')
        movies = dict([(x['id'], dict(x)) for x in cursor.fetchall()])
        for dirname in os.listdir(self.__temp_dir):
            movie_id, resource_id = tuple(dirname.split('_'))
            movie = movies[int(movie_id)]
            if movie['archived'] == 1:
                logger.warning('Archived already: %s, %s' % (movie['title'], movie_id))
                continue
            dirpath = os.path.join(self.__temp_dir, dirname)
            filenames = os.listdir(dirpath)
            if len(filenames) == 0:
                continue
            if len(filenames) > 1:
                logger.error('Files are on conflict: %s' % movie_id)
                continue
            ext = os.path.splitext(filenames[0])[1]
            src = os.path.join(dirpath, filenames[0])
            filename = '%d_%s' % (movie['year'], movie['original_title'])
            if movie['title'] != movie['original_title']:
                filename += '_%s' % movie['title']
            subtype = 'Movie' if movie['subtype'] == 'movie' else 'TV' if movie['subtype'] == 'tv' else 'Unknown'
            dst_dir = os.path.join(self.cdn, subtype, movie['languages'][0])
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            dst = os.path.join(self.cdn, subtype, movie['languages'][0], filename + ext)
            if os.path.exists(dst):
                logger.warning('Exists: %s' % dst)
                continue

            cursor.execute('UPDATE movies SET archived = ? AND location = ? WHERE archived = ? and id = ?', (1, dst, 0, movie_id))
            if cursor.rowcount != 1:
                logger.error('Failed to archive movie: %s. ROLLBACK!' % movie['title'])
                con.rollback()
                continue
            cursor.execute('UPDATE resources SET status = ? WHERE status = ? AND id = ?', (3, 1, int(resource_id)))
            if cursor.rowcount != 1:
                logger.error('Failed to update status of resource: %s. ROLLBACK!' % resource_id)
                con.rollback()
                continue
            try:
                shutil.move(src, dst)
            except FileExistsError as e:
                logger.error(e)
                con.rollback()
                continue
            os.rmdir(dirpath)
            con.commit()
            logger.info('Movie archived: %s' % movie['title'])
        logger.info('Finish archiving movies: %d' % con.total_changes)
        con.close()

    def weight_video_file(self, movie_durations=None, size=-1, ext=None, video_duration=-1, filepath=''):
        """
        Calculate weight of a file for a movie. Larger the result is, more right the file is.
        Same properties from file have higher priority if file is specified.
        :param movie_durations: Unit: min
        :param size: KB
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
                target_size = sum(movie_durations) / len(movie_durations) * 60 * self.standard_kbps / 8
                if size < target_size / 2:
                    return -1
                elif size > target_size * 2:
                    ws.append(100 * (size / target_size) ** 2)
                else:
                    ratio = size / target_size if size < target_size else target_size / size
                    ws.append(100 * ratio)
        return sum(ws) / len(ws)

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


def cmp_strings(s1, s2):
    """
    compare two strings with same length, at least 1.
    :return: True if first is common, list of common parts, lists of different parts for s1 and s2 separately
    """
    if s1 is None or s2 is None or len(s1) != len(s2) or len(s1) == 0:
        raise ValueError
    cl, dl1, dl2 = [''], [], []
    last_common = True
    for i in range(len(s1)):
        if s1[i] == s2[i]:
            if not last_common:
                cl.append('')
                last_common = True
            cl[-1] += s1[i]
        else:
            if last_common:
                dl1.append('')
                dl2.append('')
                last_common = False
            dl1[-1] += s1[i]
            dl2[-1] += s2[i]
    return s1[0] == s2[0], cl, dl1, dl2


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
