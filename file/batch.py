import os
import re


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


def rename_tv(src_dir, episode_index, season_index=-1, rename_func=None):
    """
    Rename names of the files in tv series.
    :param src_dir:
    :param episode_index: index starting with.
    :param season_index: index starting with, default -1 if it only has one season.
    :param rename_func: custom function to rename the file, with the source file name as the argument.
    """
    if not os.path.exists(src_dir):
        print("Source directory doesn't exist.")

    if season_index >= 0:
        for src_season_name in os.listdir(src_dir):
            src_season_path = os.path.join(src_dir, src_season_name)
            if os.path.isdir(src_season_path):
                rename_tv(src_season_path, episode_index, -1)
                dst_season_name = 'S' + find_num(src_season_name, season_index)
                dst_season_path = os.path.join(src_dir, dst_season_name)
                print("Rename from {} to {}.".format(src_season_path, dst_season_path))
                os.rename(src_season_path, dst_season_path)
    else:
        for src_full_name in os.listdir(src_dir):
            src_file_path = os.path.join(src_dir, src_full_name)
            if os.path.isfile(src_file_path):
                src_file_name, file_ext = os.path.splitext(src_full_name)
                if rename_func is None:
                    dst_file_name = 'E' + find_num(src_file_name, episode_index) + file_ext
                else:
                    dst_file_name = rename_func(src_file_name) + file_ext
                dst_file_path = os.path.join(src_dir, dst_file_name)
                print("Rename from {} to {}.".format(src_file_path, dst_file_path))
                os.rename(src_file_path, dst_file_path)


def find_num(src_str: str, index) -> str:
    return re.findall(r'\d+', src_str)[index].zfill(2)


if __name__ == '__main__':
    remove_duplicate_songs('G:/Music')
