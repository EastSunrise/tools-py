""" Search and manage video resources

@Author Kingen
@Date 2020/4/13
"""
import os
import re
from sqlite3 import register_converter, register_adapter, connect, Row, PARSE_DECLTYPES, OperationalError

from internet.spider import IDM, pre_download, Thunder
from utils import config

logger = config.get_logger(__name__)

VIDEO_SUFFIXES = ('.avi', '.rmvb', '.mp4', '.mkv')
standard_kbps = 2500  # kb/s


class VideoManager:
    CHINESE = ['汉语普通话', '普通话', '粤语', '闽南语', '河南方言', '贵州方言', '贵州独山话']
    PROTOCOLS = ['http', 'ftp', 'ed2k', 'magnet', 'pan', 'torrent']
    JUNK_SITES = ['yutou.tv', '80s.la', '80s.im', '2tu.cc', 'bofang.cc:', 'dl.y80s.net', '80s.bz', 'xubo.cc']

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
        self.__con.interrupt()
        self.__con.close()

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


class BadVideoFileError(OSError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
