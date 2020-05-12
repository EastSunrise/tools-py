""" Search and manage video resources

@Author Kingen
@Date 2020/4/13
"""
import base64
import math
import os
import re
import sys
from itertools import groupby
from operator import itemgetter
from sqlite3 import register_converter, register_adapter, connect, Row, PARSE_DECLTYPES, OperationalError
from urllib import parse, error

from pymediainfo import MediaInfo

from file import base
from internet.douban import Douban
from internet.spider import IDM, pre_download, Thunder
from utils import config
from utils.common import cmp_strings

logger = config.get_logger(__name__)

VIDEO_SUFFIXES = ('.avi', '.rmvb', '.mp4', '.mkv')
standard_kbps = 2500  # kb/s


class VideoManager:
    CHINESE = ['汉语普通话', '普通话', '粤语', '闽南语', '河南方言', '贵州方言', '贵州独山话']
    PROTOCOLS = ['http', 'ftp', 'ed2k', 'magnet', 'pan', 'torrent']
    JUNK_SITES = ['yutou.tv', '80s.la', '80s.im', '2tu.cc', 'bofang.cc:', 'dl.y80s.net', '80s.bz']

    def __init__(self, db, cdn, idm_exe='IDMan.exe') -> None:
        register_adapter(list, lambda x: '[%s]' % '_'.join(x))
        register_converter('list', lambda x: [] if x.decode('utf-8') == '[]' else x.decode('utf-8').strip('[]').split('_'))
        self.__db = db
        self.cdn = cdn
        self.__idm = IDM(idm_exe, self.cdn)
        self.__thunder = Thunder()
        self.__temp_dir = os.path.join(self.cdn, 'Temp')
        c = connect(self.__db, 30, detect_types=PARSE_DECLTYPES)
        c.row_factory = Row
        c.set_trace_callback(lambda x: logger.info('Execute: %s', x))
        self.__con = c

    @property
    def cdn(self):
        return self.__cdn

    @cdn.setter
    def cdn(self, cdn):
        if not os.path.isdir(cdn):
            cdn = './'
        self.__cdn = cdn

    def close(self):
        self.__con.close()

    def update_movie(self, subject_id, douban: Douban, cookie):
        subject_src = self.__get_subject(id=subject_id)
        try:
            subject = douban.movie_subject(subject_id)
        except error.HTTPError as e:
            if e.code == 404:
                subject = douban.movie_subject_with_cookie(subject_id, cookie, subject_src['title'])
            else:
                raise e
        for k, v in subject_src.items():
            if k in subject and str(v) != str(subject[k]):
                logger.info('Update %s: from %s to %s', k, str(v), str(subject[k]))
                subject_src[k] = subject[k]
        del subject_src['id']
        del subject_src['last_update']
        self.__update_subject(subject_id, **subject_src)

    def update_my_movies(self, douban: Douban, user_id, cookie, start_date=None):
        """
        Update my collected movies from Douban to database.

        If not exist in db, get full info and insert into db, with archived set to 0.
        If exists, update status and tag_date.

        :param douban: an instance of Douban client
        :param start_date: when tag_date start
        """
        logger.info('Start updating movies')
        ids = [m['id'] for m in self.__get_subjects()]
        cursor = self.__con.cursor()
        added_count = 0
        for subject_id, subject in douban.collect_my_movies(user_id, cookie, start_date=start_date).items():
            subject_id = int(subject_id)
            try:
                subject.update(douban.movie_subject(subject_id))
            except error.HTTPError as e:
                if e.code == 404:
                    subject.update(douban.movie_subject_with_cookie(subject_id, cookie, subject['title']))
                else:
                    raise e
            subject['title'] = remove_redundant_spaces(subject['title'])
            subject['original_title'] = remove_redundant_spaces(subject['original_title'])
            remove_redundant_spaces(subject['aka'])

            if subject_id in ids:
                self.__update_subject(subject_id, **subject)
            else:
                # default: last_update = now(), archived = 0
                cursor.execute('INSERT INTO movies(id, title, alt, status, tag_date, original_title, aka, subtype, languages, '
                               'year, durations, current_season, episodes_count, seasons_count, last_update, archived) '
                               'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATETIME(\'now\'), 0)',
                               ([subject[key] for key in [
                                   'id', 'title', 'alt', 'status', 'tag_date', 'original_title', 'aka', 'subtype', 'languages',
                                   'year', 'durations', 'current_season', 'episodes_count', 'seasons_count'
                               ]]))
                if cursor.rowcount != 1:
                    logger.error('Failed to Add movie: %s. ROLLBACK!', subject['title'])
                    self.__con.rollback()
                else:
                    logger.info('Add movie: %s', subject['title'])
                    self.__con.commit()
                    added_count += 1
        logger.info('Finish updating movies, %d movies added', added_count)

    def __collect_subject(self, subject, sites, **kwargs):
        subject_id, title, subtype = subject['id'], subject['title'], subject['subtype']
        path, filename = self.__get_location(subject)
        archived = self.__archived(subject)
        logger.info('Collecting subject: %s, %s', title, subject['alt'])
        if archived:
            logger.info('File exists for the subject %s: %s', title, archived)
            return True

        manual = False if 'manual' not in kwargs else kwargs['manual']
        # movie
        if subtype == 'movie':
            links = {'http': set(), 'ed2k': set(), 'pan': set(), 'ftp': set(), 'magnet': set(), 'torrent': set(), 'unknown': set()}
            for site in sorted(sites, key=lambda x: x.priority):
                for url, remark in site.search(subject, manual).items():
                    p, u = classify_url(url)
                    if any([u.find(x) >= 0 for x in self.JUNK_SITES]):
                        continue
                    filename, ext, size = None, None, -1
                    if p == 'http':
                        filename = os.path.basename(u)
                        ext = os.path.splitext(filename)[1]
                        code, msg, args = pre_download(u)
                        if code == 200:
                            size = args['size']
                    elif p == 'ftp':
                        filename = os.path.basename(u)
                        ext = os.path.splitext(filename)[1]
                    elif p == 'ed2k':
                        filename = u.split('|')[2]
                        ext = os.path.splitext(filename)[1]
                        size = int(u.split('|')[3])
                    if weight_video(ext, subject['durations'], size) < 0:
                        continue
                    links[p].add((u, filename, ext))

            url_count = 0
            for u, filename, ext in links['http']:
                logger.info('Add IDM task of %s, downloading from %s to the temporary dir', title, u)
                self.__idm.add_task(u, self.__temp_dir, '%d_%s_http_%d_%s' % (subject_id, title, url_count, filename))
                url_count += 1
            for p in ['ed2k', 'ftp']:
                for u, filename, ext in links[p]:
                    logger.info('Add Thunder task of %s, downloading from %s to the temporary dir', title, u)
                    self.__thunder.add_task(u, '%d_%s_%s_%d_%s' % (subject_id, title, p, url_count, filename))
                    url_count += 1
            self.__thunder.commit_tasks()

            if url_count == 0:
                logger.warning('No resources found for: %s', title)
                return False
            self.__update_subject(subject_id, archived=3)
        else:
            episodes_count = subject['episodes_count']
            links = {'http': set(), 'ed2k': set(), 'pan': set(), 'ftp': set(), 'magnet': set(), 'torrent': set(), 'unknown': set()}
            for site in sorted(sites, key=lambda x: x.priority):
                for url, remark in site.search(subject).items():
                    p, u = classify_url(url)
                    if any([u.find(x) >= 0 for x in self.JUNK_SITES]):
                        continue
                    ext = None
                    if p == 'http':
                        ext = os.path.splitext(u)[1]
                    elif p == 'ftp':
                        ext = os.path.splitext(u)[1]
                    elif p == 'ed2k':
                        ext = os.path.splitext(u.split('|')[2])[1]
                    if weight_video(ext) < 0:
                        continue
                    links[p].add((u, ext))
            urls = self.__extract_tv_urls(links['http'], episodes_count)
            empties = [str(i + 1) for i, x in enumerate(urls) if x is None]
            if len(empties) > 0:
                logger.info('Not enough episodes for %s, total: %d, lacking: %s',
                            subject['title'], episodes_count, ', '.join(empties))
                return False
            logger.info('Add IDM tasks of %s, %d episodes', title, episodes_count)
            os.makedirs(path, exist_ok=True)
            episode = 'E%%0%dd%%s' % math.ceil(math.log10(episodes_count + 1))
            for i, url in enumerate(urls):
                self.__idm.add_task(url, path, episode % ((i + 1), os.path.splitext(url)[1]))
            url_count = episodes_count
            self.__update_subject(subject_id, archived=2)

        logger.info('Tasks added: %d for %s. Downloading...', url_count, title)
        return True

    def __extract_tv_urls(self, http_resources, episodes_count):
        for r in http_resources:
            t, s = parse.splittype(r['url'])
            h, p = parse.splithost(s)
            h = '%s://%s' % (t, h)
            r['head'], r['path'] = h, p
        urls = [None] * (episodes_count + 1)
        for length, xs in groupby(sorted(http_resources, key=lambda x: len(x['path'])), key=lambda x: len(x['path'])):
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
        return urls[1:]

    def collect_subjects(self, sites, no_resources_file='', status=0, count=10):
        if os.path.exists(no_resources_file):
            with open(no_resources_file, 'r', encoding='utf-8') as fp:
                no_resources_ids = [int(line.split(', ')[0]) for line in fp.read().strip('\n').split('\n')[1:]]
            no_resources_fp = open(no_resources_file, 'a', encoding='utf-8')
        else:
            no_resources_ids = []
            no_resources_fp = sys.stdout
        results = [x for x in self.__get_subjects(archived=status) if x['id'] not in no_resources_ids][:count]
        total, success = len(results), 0
        for i, x in enumerate(results):
            logger.info('Collecting subjects: %d/%d', i + 1, total)
            if self.__collect_subject(x, sites):
                success += 1
            else:
                no_resources_fp.write('\n%d, %s' % (x['id'], x['title']))
                no_resources_fp.flush()
        logger.info('Finish collecting, total: %d, success: %d, fail: %d', total, success, total - success)
        no_resources_fp.close()
        return success

    def collect_subject(self, subject_id: int, sites, **kwargs):
        """
        Search and download resources for subject specified by id. There  steps as commented.
        :param subject_id:
        :return:
        """
        result = self.__get_subject(id=subject_id)
        if result is None:
            logger.info('No subject with id %d', subject_id)
            return False
        r = self.__collect_subject(result, sites, **kwargs)
        return r

    def archive(self, all_downloaded=False):
        """
        Archive subjects. Query subjects with specific status and then archive those have responding located files under the cdn.
        """
        subjects = self.__get_subjects()
        archived_count = update_count = unarchived_count = fail_downloading = 0

        for subject in subjects:
            archived = self.__archived(subject)
            subject_id = subject['id']
            if archived:
                if subject['subtype'] == 'movie':
                    if weight_video_file(archived, subject['durations']) < 0:
                        logger.info('Delete unqualified video file: %s, %s', archived, subject['alt'])
                        base.del_to_recycle(archived)
                if subject['archived'] != 1:
                    self.__update_subject(subject_id, archived=1, location=archived)
                    archived_count += 1
                elif subject['location'] != archived:
                    self.__update_subject(subject_id, location=archived)
                    update_count += 1
                else:
                    pass
            elif subject['archived'] == 1:
                self.__update_subject(subject_id, ignore_none=False, archived=0, location=None)
                unarchived_count += 1
            elif all_downloaded and subject['archived'] in (2, 3):
                self.__update_subject(subject_id, archived=4)
                fail_downloading += 1

        logger.info('Archive subjects: %d added, %d updated, %d unarchived, %d failed downloading',
                    archived_count, update_count, unarchived_count, fail_downloading)

        locations = [x['location'] for x in self.__get_subjects()]
        for subtype in ['Movies', 'TV']:
            subtype_path = os.path.join(self.cdn, subtype)
            for language in os.listdir(subtype_path):
                language_path = os.path.join(subtype_path, language)
                for filename in os.listdir(language_path):
                    filepath = os.path.join(language_path, filename)
                    if filepath not in locations:
                        logger.info('Dislocated: %s', filepath)

    def archive_temp(self):
        """
        After finishing IDM tasks
        :return:
        """
        archived = 0
        for subject_id, names in groupby(sorted(os.listdir(self.__temp_dir)), key=lambda x: int(x.split('_')[0])):
            paths = [os.path.join(self.__temp_dir, x) for x in names]
            video_paths = [x for x in paths if os.path.splitext(x)[1] in VIDEO_SUFFIXES]
            if len(video_paths) == 0:
                continue
            subject = self.__get_subject(id=subject_id)
            weights = []
            for path in video_paths:
                weight = weight_video_file(path, subject['durations'])
                weights.append((path, weight))
                logger.info('Weight file: %s, %.2f', path, weight)
            chosen = max(weights, key=lambda x: x[1])
            if len(video_paths) < len(paths):
                if chosen[1] < 90:
                    continue
            else:
                if chosen[1] < 0:
                    logger.warning('No qualified video file: %s', subject['title'])
                    continue
            # copy, delete
            src = chosen[0]
            ext = os.path.splitext(src)[1]
            path, filename = self.__get_location(subject)
            dst = os.path.join(path, filename + ext)
            code = base.copy(src, dst)
            if code != 0 and code != 1:
                raise IOError
            archived += 1
            logger.info('Finished: %s', filename)
            for path in paths:
                code, msg = base.del_to_recycle(path)
                if code != 0:
                    logger.error('Failed to delete file: %s, %s', path, msg)
        logger.info('Finish archiving: %d success', archived)

    @staticmethod
    def __compute_limit(left, right, uf, phs, is_equal):
        while left <= right:
            m = (left + right) >> 1
            code, msg, args = pre_download(uf % tuple([m] * phs), pause=10)
            if code == 200 ^ is_equal:
                left = m + 1
            else:
                right = m - 1
        return left

    def __archived(self, subject):
        """
        :return: False if not archived, otherwise, filepath.
        """
        path, filename = self.__get_location(subject)
        filepath = os.path.join(path, filename)
        if subject['subtype'] == 'tv' and os.path.isdir(filepath):
            if len([x for x in os.listdir(filepath) if re.match(r'E\d+', x)]) == subject['episodes_count']:
                return filepath
        if subject['subtype'] == 'movie' and os.path.isdir(path):
            with os.scandir(path) as sp:
                for f in sp:
                    if f.is_file() and os.path.splitext(f.name)[0] == filename:
                        return f.path
        return False

    def __get_subjects(self, **params):
        cursor = self.__con.cursor()
        if not params or len(params) == 0:
            cursor.execute('SELECT * FROM movies')
        else:
            cursor.execute('SELECT * FROM movies WHERE %s' % (' AND '.join(['%s = :%s' % (k, k) for k in params])), params)
        results = [dict(x) for x in cursor.fetchall()]
        return results

    def __get_subject(self, **params):
        results = self.__get_subjects(**params)
        if len(results) == 0:
            return None
        return results[0]

    def __update_subject(self, item_id: int, ignore_none=True, **kwargs):
        params = {}
        for k, v in kwargs.items():
            if k in ['title', 'alt', 'status', 'tag_date', 'original_title', 'aka', 'subtype', 'languages', 'year', 'durations',
                     'current_season', 'episodes_count', 'seasons_count', 'archived', 'location', 'source'] \
                    and (not ignore_none or (ignore_none and v is not None)):
                params[k] = v
        if not params or len(params) == 0:
            raise ValueError('No params to update')
        cursor = self.__con.cursor()
        cursor.execute('UPDATE movies SET last_update=DATETIME(\'now\'), %s WHERE id = %d'
                       % (', '.join(['%s = :%s' % (k, k) for k in params]), item_id), params)
        if cursor.rowcount != 1:
            logger.error('Failed to update movie: %d', item_id)
            self.__con.rollback()
            raise OperationalError('Failed to update')
        self.__con.commit()
        return True

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


def remove_redundant_spaces(string):
    if isinstance(string, str):
        return re.sub(r'\s+', ' ', string.strip())
    if isinstance(string, list) or isinstance(string, tuple):
        for i, s in enumerate(string):
            string[i] = re.sub(r'\s+', ' ', s.strip())
        return string
    raise ValueError


def weight_video_file(filepath, movie_durations=None):
    """
    Read related arguments from a file.
    """
    if not os.path.isfile(filepath):
        raise ValueError
    ext = os.path.splitext(filepath)[1]
    duration = get_duration(filepath) // 1000
    size = os.path.getsize(filepath)
    return weight_video(ext, movie_durations, size, duration)


def weight_video(ext=None, movie_durations=None, size=-1, file_duration=-1):
    """
    Calculate weight of a file for a movie. Larger the result is, higher quality the file has.
    Properties read from the file have higher priority than those specified by arguments.

    Whose extension is not in VIDEO_SUFFIXES will be excluded directly.

    If duration of the movie isn't given, size and duration will be invalid. Otherwise, follow below rules.
    Actual duration of the file has to be within 1 minutes compared to give duration.
    Size of the file will be compared to standard size computed based on given duration of the movie and standard kbps.
    The file will be excluded if its size is less than half of the standard size.

    The file is a good one if weight is over 90.

    :param movie_durations: Unit: minute
    :param size: Unit: B
    :param file_duration: Unit: second
    :return ratio * 100
    """
    ws = []
    if ext is not None:
        if ext not in VIDEO_SUFFIXES:
            return -1
        else:
            if ext in ('.mp4', '.mkv'):
                ws.append(100)
            else:
                ws.append(50)
    if len(movie_durations) > 0:
        durations = [int(re.findall(r'\d+', d)[0]) for d in movie_durations]
        if file_duration >= 0:
            for i, duration in enumerate(sorted(durations)):
                if abs(duration * 60 - file_duration) < 60:
                    ws.append(100 * (i + 1) / len(durations))
                    break
                if i == len(durations) - 1:
                    logger.warning('Error durations: %.2f, %s', file_duration / 60, ','.join([str(x) for x in movie_durations]))
                    return -1
        if size >= 0:
            target_size = int(sum(durations) / len(durations) * 7680 * standard_kbps)
            if size < (target_size // 2):
                logger.warning('Too small file: %s, request: %s', print_size(size), print_size(target_size))
                return -1
            elif size <= target_size:
                ws.append(100 * (size / target_size))
            elif size <= (target_size * 2):
                ws.append(100 * (target_size / size))
            else:
                ws.append(200 * (target_size / size) ** 2)
    if len(ws) == 0:
        return 0
    return sum(ws) / len(ws)


def print_size(size):
    """
    :param size: Unit B
    """
    for u in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return '%.2f %s' % (size, u)
        size /= 1024
    return '%.2f TB' % size


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
                                logger.info('Special lines in No. %s', segment[0])
                            f1.writelines([
                                segment[0], segment[1], segment[2], '\n'
                            ])
                            f2.writelines([
                                segment[0], segment[1], segment[3], '\n'
                            ])
                            segment = []


def classify_url(url: str):
    """
    Classify and decode a url. Optional protocols: http/ed2k/pan/ftp/magnet/torrent/unknown

    Structure of urls:
    ed2k: ed2k://|file|<file name>|<size of file, Unit: B>|<hash of file>|/
    magnet:

    :return: (protocol of url, decoded url)
    """
    if url.startswith('thunder://'):
        url = base64.b64decode(url[10:])
        try:
            url = url.decode('utf-8').strip('AAZZ')
        except UnicodeDecodeError:
            url = url.decode('gbk').strip('AAZZ')
    url = parse.unquote(url.rstrip('/'))

    if 'pan.baidu.com' in url:
        return 'pan', url
    if url.endswith('.torrent'):
        return 'torrent', url
    for head in ['ftp', 'http', 'ed2k', 'magnet']:
        if url.startswith(head):
            return head, url
    return 'unknown', url


def get_duration(filepath):
    media_info = MediaInfo.parse(filepath)
    tracks = dict([(x.track_type, x) for x in media_info.tracks])
    d = tracks['General'].duration
    if isinstance(d, int):
        return d
    d = tracks['Video'].duration
    if isinstance(d, int):
        return d
    raise ValueError('Duration Not Found')
