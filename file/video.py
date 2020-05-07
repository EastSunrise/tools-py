""" Search and manage video resources

@Author Kingen
@Date 2020/4/13
"""
import base64
import math
import os
import re
import shutil
import sys
from itertools import groupby
from operator import itemgetter
from sqlite3 import register_converter, register_adapter, connect, Row, PARSE_DECLTYPES
from urllib import parse, error

from moviepy.video.io.VideoFileClip import VideoFileClip

from file import base
from internet.douban import Douban
from internet.spider import IDM, pre_download, Thunder
from utils import config
from utils.common import cmp_strings

logger = config.get_logger(__name__)

VIDEO_SUFFIXES = ('.avi', '.rmvb', '.mp4', '.mkv')
standard_kbps = 2500  # kb/s


# todo get extension from response
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

    @property
    def cdn(self):
        return self.__cdn

    @cdn.setter
    def cdn(self, cdn):
        if not os.path.isdir(cdn):
            cdn = './'
        self.__cdn = cdn

    def update_my_movies(self, douban: Douban, user_id, cookie, start_date=None):
        """
        Update my collected movies from Douban to database.

        If not exist in db, get full info and insert into db, with archived set to 0.
        If exists, update status and tag_date.

        :param douban: an instance of Douban client
        :param start_date: when tag_date start
        """
        logger.info('Start updating movies')
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
                subject['title'] = remove_redundant_spaces(subject['title'])
                subject['original_title'] = remove_redundant_spaces(subject['original_title'])
                remove_redundant_spaces(subject['aka'])
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
        logger.info('Finish updating movies, %d movies changed' % connection.total_changes)
        connection.close()

    def collect_subjects(self, sites, no_resources_file='', thunder=None, status=0):
        con = self.__get_connection()
        cursor = con.cursor()
        cursor.execute('SELECT * FROM movies WHERE archived = ?', (status,))
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
            logger.info('Collecting subjects: %d/%d' % (i + 1, total))
            if self.__collect_subject(x, con, sites, thunder):
                success += 1
            else:
                no_resources_fp.write('\n%d, %s' % (x['id'], x['title']))
                no_resources_fp.flush()
        logger.info('Finish collecting, total: %d, success: %d, fail: %d' % (total, success, total - success))
        no_resources_fp.close()
        con.close()
        return success

    def collect_subject(self, subject_id: int, sites, thunder=None):
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
        r = self.__collect_subject(dict(result), con, sites, thunder)
        con.close()
        return r

    def archive(self, all_downloaded=False):
        """
        Archive subjects. Query subjects with specific status and then archive those have responding located files under the cdn.
        """
        con = self.__get_connection()
        cursor = con.cursor()
        cursor.execute('SELECT * FROM movies')
        updates = []
        archived_count = update_count = unarchived_count = fail_downloading = 0
        subjects = cursor.fetchall()

        for subject in subjects:
            archived = self.__archived(subject)
            if archived:
                if subject['archived'] != 1:
                    updates.append((1, archived, subject['id']))
                    archived_count += 1
                elif subject['location'] != archived:
                    updates.append((1, archived, subject['id']))
                    update_count += 1
            elif subject['archived'] == 1:
                updates.append((0, None, subject['id']))
                unarchived_count += 1
            elif all_downloaded and subject['archived'] == 2:
                updates.append((0, None, subject['id']))
                fail_downloading += 1
        if len(updates) > 0:
            cursor.executemany('UPDATE movies SET archived = ?, location = ?, last_update = DATETIME(\'now\') '
                               'WHERE id = ?', updates)
            if cursor.rowcount != len(updates):
                logger.error('Failed to update locations of subjects. ROLLBACK!')
                con.rollback()
            else:
                logger.info('Archive subjects: %d added, %d updated, %d unarchived, %d failed downloading'
                            % (archived_count, update_count, unarchived_count, fail_downloading))
                con.commit()

        locations = [x['location'] for x in subjects] + [x[1] for x in updates]
        for subtype in ['Movies', 'TV']:
            subtype_path = os.path.join(self.cdn, subtype)
            for language in os.listdir(subtype_path):
                language_path = os.path.join(subtype_path, language)
                for filename in os.listdir(language_path):
                    filepath = os.path.join(language_path, filename)
                    if filepath not in locations:
                        logger.info('Dislocated: %s' % filepath)
        con.close()

    def archive_temp(self):
        con = self.__get_connection()
        cursor = con.cursor()
        archived = 0
        for name in os.listdir(os.path.join(self.cdn, 'Temp')):
            basename, ext = os.path.splitext(name)
            if ext in ['.xltd', '.cfg']:
                continue
            subject_id = int(basename.split('_')[0])
            cursor.execute('SELECT * FROM movies WHERE id = ?', (subject_id,))
            path, filename = self.__get_location(cursor.fetchone())
            dst = os.path.join(path, filename + ext)
            cursor.execute('UPDATE movies SET archived = ?, location = ?, last_update = DATETIME(\'now\') '
                           'WHERE id = ?', (1, dst, subject_id))
            if cursor.rowcount != 1:
                logger.error('Failed to update: %d. ROLLBACK!' % subject_id)
                con.rollback()
                continue
            src = os.path.join(self.cdn, 'Temp', name)
            if os.path.exists(dst):
                logger.warning('Exists: %s' % dst)
                con.rollback()
                continue
            os.makedirs(path, exist_ok=True)
            src_md5 = base.get_md5(src)
            logger.info('Copy file from %s to %s' % (src, dst))
            dst = shutil.copy2(src, dst)
            if base.get_md5(dst) != src_md5:
                logger.error('File corrupted while copying')
                os.remove(dst)
                con.rollback()
                continue
            os.remove(src)
            con.commit()
            archived += 1
            logger.info('Archived: %s' % filename)
        logger.info('Finish archiving: %d success' % archived)
        con.close()

    def __collect_subject(self, subject, connection, sites, thunder: Thunder = None):
        cursor = connection.cursor()
        subject_id, title, subtype = subject['id'], subject['title'], subject['subtype']
        path, filename = self.__get_location(subject)
        archived = self.__archived(subject)
        logger.info('Collecting subject: %s' % subject['title'])
        if archived:
            logger.info('File exists for the subject %s: %s' % (title, archived))
            return True

        # search http_resources
        for site in sites:
            logger.info('Searching: %s, for %s, %s' % (site.name, title, subject['alt']))
            links = site.search(subject)

            # filter
            http_resources, ed2k_resources = [], []
            other_resources = {'pan': [], 'ftp': [], 'magnet': [], 'torrent': [], 'unknown': []}
            for url, remark in links.items():
                p, u = classify_url(url)
                if any([u.find(x) >= 0 for x in self.JUNK_SITES]):
                    continue
                if p == 'http':
                    ext = os.path.splitext(u)[1]
                    if ext in VIDEO_SUFFIXES:
                        http_resources.append({'url': u, 'ext': ext})
                elif p == 'ed2k':
                    parts = u.split('|')
                    ext = os.path.splitext(parts[2])[1]
                    if ext in VIDEO_SUFFIXES:
                        ed2k_resources.append({'url': u, 'ext': ext, 'size': int(parts[3])})
                else:
                    logger.info('Excluded link: %s' % u)
                    other_resources[p].append(u)
            if subtype == 'movie':
                flag = False
                durations = [int(re.findall(r'\d+', d)[0]) for d in subject['durations']]
                if len(http_resources) > 0:
                    for r in http_resources:
                        code, msg, args = pre_download(r['url'])
                        if code == 200:
                            r['weight'] = weight_video(r['ext'], durations, args['size'])
                        else:
                            r['weight'] = -1
                    chosen = max(http_resources, key=lambda x: x['weight'])
                    if chosen['weight'] > 0:
                        os.makedirs(path, exist_ok=True)
                        filename += chosen['ext']
                        logger.info('Add IDM task of %s, downloading from %s to %s' % (filename, chosen['url'], path))
                        self.__idm.add_task(chosen['url'], path, filename)
                        flag = True
                if not flag and thunder and len(ed2k_resources) > 0:
                    for r in ed2k_resources:
                        r['weight'] = weight_video(r['ext'], durations, r['size'])
                    chosen = max(ed2k_resources, key=lambda x: x['weight'])
                    if chosen['weight'] > 0:
                        os.makedirs(path, exist_ok=True)
                        dst_name = '%d_%s%s' % (subject_id, title, chosen['ext'])
                        logger.info('Add Thunder task of %s, downloading from %s to temp dir' % (title, chosen['url']))
                        thunder.add_task(chosen['url'], dst_name)
                        thunder.commit_tasks()
                        flag = True
                if not flag:
                    continue
            else:
                if len(http_resources) == 0:
                    logger.info('No http links found on %s' % site.name)
                    continue
                episodes_count = subject['episodes_count']
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
                urls = urls[1:]
                empties = [str(i + 1) for i, x in enumerate(urls) if x is None]
                if len(empties) > 0:
                    logger.info('Not enough episodes for %s, total: %d, lacking: %s'
                                % (subject['title'], episodes_count, ', '.join(empties)))
                    continue
                logger.info('Add IDM tasks of %s, %d episodes' % (subject['title'], episodes_count))
                path = os.path.join(path, filename)
                os.makedirs(path, exist_ok=True)
                episode = 'E%%0%dd%%s' % math.ceil(math.log10(episodes_count + 1))
                for i, url in enumerate(urls):
                    self.__idm.add_task(url, path, episode % ((i + 1), os.path.splitext(url)[1]))
            cursor.execute('UPDATE movies SET archived = 2, last_update = DATETIME(\'now\')'
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

    def __get_connection(self):
        c = connect(self.__db, 30, detect_types=PARSE_DECLTYPES)
        c.row_factory = Row
        c.set_trace_callback(lambda x: logger.info('Execute: %s' % x))
        return c

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
            string[i] = re.sub(r'\s+', '', s.strip())
        return string
    raise ValueError


def weight_video_file(filepath, movie_durations=None):
    """
    Read related arguments from a file.
    """
    if not os.path.isfile(filepath):
        raise ValueError
    ext = os.path.splitext(filepath)[1]
    duration = VideoFileClip(filepath).duration / 60
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

    :param movie_durations: Unit: min
    :param size: Unit: B
    :param file_duration: Unit: min
    :return ratio * 100
    """
    ws = []
    if ext is not None:
        if ext not in VIDEO_SUFFIXES:
            return -1
        else:
            ws.append(100 * (VIDEO_SUFFIXES.index(ext) + 1) / len(VIDEO_SUFFIXES))
    if movie_durations is not None:
        if file_duration >= 0:
            for i, movie_duration in enumerate(sorted(movie_durations)):
                if abs(movie_duration - file_duration) < 1:
                    ws.append(100 * (i + 1) / len(movie_durations))
                    break
                if i == len(movie_durations) - 1:
                    return -1
            return -1
        if size >= 0:
            target_size = int(sum(movie_durations) / len(movie_durations) * 7680 * standard_kbps)
            if size < (target_size >> 1):
                return -1
            elif size <= target_size:
                ws.append(100 * (size / target_size))
            elif size <= (target_size << 1):
                ws.append(100 * (target_size / size))
            else:
                ws.append(200 * (target_size / size) ** 2)
    return sum(ws) / len(ws)


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

    if url.startswith('https://pan.baidu.com'):
        return 'pan', url
    if url.endswith('.torrent'):
        return 'torrent', url
    for head in ['ftp', 'http', 'ed2k', 'magnet']:
        if url.startswith(head):
            return head, url
    return 'unknown', url
