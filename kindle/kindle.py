import tkinter.filedialog as filedialog
from utils.global_log import LOGGER
import os
import file.file_util as file_util
import utils.const as const


class Kindle(object):
    def __init__(self):
        self.__content_dir = "E:\\Document\\My Kindle Content"
        self.COPIED_FLAG = 'COPIED'

    def collect_azw(self):
        dst_dir = filedialog.askdirectory(initialdir='E:/Desktop')
        if not dst_dir:
            LOGGER.info("Haven't choose a directory.")
            return False
        for root, subdir_list, file_name_list in os.walk(self.__content_dir):
            for file_name in file_name_list:
                if file_name.endswith('.azw') and not os.path.exists(os.path.join(root, self.COPIED_FLAG)):
                    if file_util.copy_file(os.path.join(root, file_name), dst_dir) != -1:
                        f = open(os.path.join(root, self.COPIED_FLAG), 'w')
                        f.close()


if __name__ == '__main__':
    Kindle().collect_azw()
