import os
import re


def separate_srt(src: str):
    """
    Separate the .srt file with two languages to single language.
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


def remove_duplicate_songs(src_dir, print_keep=False):
    """
    Remove the duplicate songs with the same name and different format under the source directory.
    The priority of formats: mp3 > flac
    """
    songs = {}
    files = os.listdir(src_dir)
    files.sort()
    for name in files:
        file = MusicFile(src_dir, name)
        path = file.get_path()
        if os.path.isfile(path):
            if not file.is_type():
                print('Not music file: {}'.format(path))
                continue

            title = file.get_title()
            if title in songs:
                song = songs[title]
                path0 = song.get_path()
                if file < song:
                    print('Remove file: {}'.format(path))
                    os.remove(path)
                elif file > song:
                    print('Replace file: {}'.format(path0))
                    os.remove(path0)
                else:
                    print('Duplicate file: {}'.format(path))
            else:
                songs[title] = file
                if file.get_order() > 0 or print_keep:
                    print('Keep file: {}'.format(path))


class TypeFile:
    def __init__(self, src_dir, name, suffixes) -> None:
        title, ext = os.path.splitext(name)
        self.__order = 0
        if re.match(r'.*\(\d\)$', title):
            self.__title = title[0:-3]
            self.__order = int(title[-2:-1])
        else:
            self.__title = title
        self.__ext_index = -1
        if ext in suffixes:
            self.__ext_index = suffixes.index(ext)
        self.__path = os.path.join(src_dir, name)

    def get_title(self):
        return self.__title

    def is_type(self):
        return self.__ext_index >= 0

    def get_path(self):
        return self.__path

    def __gt__(self, other):
        if not isinstance(other, TypeFile):
            raise TypeError()
        if self.__ext_index == other.__ext_index:
            return self.__order < other.__order
        return self.__ext_index > other.__ext_index

    def __lt__(self, other):
        if not isinstance(other, TypeFile):
            raise TypeError()
        return other.__gt__(self)

    def get_order(self):
        return self.__order


class MusicFile(TypeFile):
    def __init__(self, src_dir, name) -> None:
        super().__init__(src_dir, name, ['.mp3', '.flac', '.wav'])


def rename_episode_default(episode_name):
    base_name, ext = os.path.splitext(episode_name)
    return 'E' + re.findall(r'\d+', base_name)[0].zfill(2) + ext


def rename_season_default(season_name):
    return 'S' + re.findall(r'\d+', season_name)[0].zfill(2)


def rename_tv(src_dir, rename_episode=rename_episode_default, rename_season=rename_season_default):
    """
    Rename names of the files in tv series.
    :param src_dir: source directory.
    :param rename_episode: function to rename each episode with the file name as the argument.
    :param rename_season: function to rename each season if it has more than one seasons.
    """
    if not os.path.exists(src_dir):
        print("Source directory doesn't exist.")
        return

    for filename in os.listdir(src_dir):
        filepath = os.path.join(src_dir, filename)
        if os.path.isfile(filepath):
            dst_name = rename_episode(filename)
            dst_path = os.path.join(src_dir, dst_name)
            print("Rename from {} to {}.".format(filepath, dst_path))
            os.rename(filepath, dst_path)
        else:
            dst_season_name = rename_season(filename)
            for episode_name in os.listdir(filepath):
                episode_path = os.path.join(filepath, episode_name)
                dst_episode_name = rename_episode(episode_name)
                dst_episode_path = os.path.join(filepath, dst_episode_name)
                print("Rename from {} to {}.".format(episode_path, dst_episode_path))
                os.rename(episode_path, dst_episode_path)
            dst_season_path = os.path.join(filepath, dst_season_name)
            print("Rename directory from {} to {}.".format(filepath, dst_season_path))
            os.rename(filepath, dst_season_path)
