import os
import re


class VideoManager:
    @staticmethod
    def __rename_episode_default(src_name, season_name=None):
        base_name, ext = os.path.splitext(src_name)
        return ((season_name + ' ') if season_name is not None else '') + 'E' + re.findall(r'\d+', src_name)[0].zfill(2) + ext

    @staticmethod
    def __rename_season_default(src_name):
        return 'S' + re.findall(r'\d+', src_name)[0].zfill(2)

    @staticmethod
    def rename_tv(src_dir, rename_episode=__rename_episode_default, rename_season=__rename_season_default):
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

    @staticmethod
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
