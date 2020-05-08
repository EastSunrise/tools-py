""" Spider for http/https protocols

@Author Kingen
@Date 2020/4/13
"""

import os
import socket
import threading
import time
from subprocess import run, CompletedProcess
from urllib import parse, error
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from selenium import webdriver
from win32com.client import Dispatch

from utils import config

logger = config.get_logger(__name__)

base_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'
}


def do_request(req: Request, pause=0.0, timeout=10, retry=3):
    """
    do request
    :param req: an instance of request.Request
    :return: content of response
    """
    if pause > 0:
        time.sleep(pause)
    logger.info('%s from %s', req.method, req.full_url)
    if req.get_method().upper() == 'POST' and req.data is not None:
        logger.info('Query: ' + parse.unquote(req.data.decode('utf=8')))
    timeout_count = reset_count = no_response_count = refused_count = 0
    while True:
        try:
            with urlopen(req, timeout=timeout) as r:
                return r.read().decode('utf-8')
        except socket.timeout as e:
            logger.error('Timeout!')
            if timeout_count >= retry:
                raise e
            timeout_count += 1
            logger.info('Retry...')
            time.sleep(timeout)
        except error.HTTPError as e:
            logger.error(e)
            raise e
        except error.URLError as e:
            logger.error(e)
            if e.errno is not None:
                raise e
            if e.reason is not None:
                e = e.reason
                if isinstance(e, socket.gaierror):
                    raise e
                if isinstance(e, TimeoutError):
                    if no_response_count >= retry:
                        raise e
                    no_response_count += 1
                    logger.info('Retry...')
                    time.sleep(timeout)
                    continue
                if isinstance(e, ConnectionRefusedError):
                    if refused_count >= retry:
                        raise e
                    refused_count += 1
                    logger.info('Retry...')
                    time.sleep(timeout)
                    continue
            logger.error('Unknown error')
            raise e
        except ConnectionResetError as e:
            logger.error(e)
            if reset_count >= retry:
                raise e
            reset_count += 1
            logger.info('Retry...')
            time.sleep(timeout)


def pre_download(url, pause=0.0, timeout=30, retry=3):
    """
    Do Pre-request a download url
    Get info of response, Content-Length or file size mainly.
    :return: (code, msg, args). Optional code and msg: (200, 'OK')/(1, 'Unknown Content Length')/(408, 'Timeout')
            'args', a dict of info will be returned if code is 200: size(B)
    """
    if pause > 0:
        time.sleep(pause)
    req = Request(quote_url(url), headers=base_headers, method='GET')
    timeout_count = reset_count = no_response_count = refused_count = 0
    while True:
        try:
            logger.info('Pre-GET from %s', req.full_url)
            with urlopen(req, timeout=timeout) as r:
                size = r.getheader('Content-Length')
                if size is None:
                    logger.error('Unknown Content Length')
                    return 1, 'Unknown Content Length', None
                else:
                    return 200, 'OK', {'size': int(size)}
        except socket.timeout:
            logger.error('Timeout')
            if timeout_count >= retry:
                return 408, 'Timeout', None
            timeout_count += 1
            logger.info('Retry...')
            time.sleep(timeout)
        except error.HTTPError as e:
            logger.error(e)
            return e.code, e.reason, None
        except error.URLError as e:
            logger.error(e)
            if e.errno is not None:
                return e.errno, e.strerror, None
            if e.reason is not None:
                e = e.reason
                if isinstance(e, socket.gaierror):
                    return e.errno, e.strerror, None
                if isinstance(e, TimeoutError):
                    if no_response_count >= retry:
                        return e.errno, e.strerror, None
                    no_response_count += 1
                    logger.info('Retry...')
                    time.sleep(timeout)
                    continue
                if isinstance(e, ConnectionRefusedError):
                    if refused_count >= retry:
                        return e.errno, e.strerror, None
                    refused_count += 1
                    logger.info('Retry...')
                    time.sleep(timeout)
                    continue
            logger.error('Unknown error')
            raise e
        except ConnectionResetError as e:
            logger.error(e)
            if reset_count >= retry:
                return e.errno, e.strerror, None
            reset_count += 1
            logger.info('Retry...')
            time.sleep(timeout)


def quote_url(url: str) -> str:
    """
    Encode the url except the scheme and netloc only when doing a request
    """
    scheme, netloc, path, query, fragment = parse.urlsplit(url)
    return parse.urlunsplit((scheme, netloc, parse.quote(path), parse.quote(query, safe='=&'), parse.quote(fragment)))


def get_soup(req: Request, pause=0.0, timeout=10) -> BeautifulSoup:
    """
    Request and return a soup of the page
    """
    return BeautifulSoup(do_request(req, pause, timeout), 'html.parser')


options = webdriver.ChromeOptions()
options.headless = True
chrome = webdriver.Chrome(options=options, executable_path='chromedriver 81.0.4044.138.exe')


def browser(url):
    logger.info('Get from %s', url)
    chrome.get(url)
    return chrome.page_source


class Downloader:
    """
    A custom downloader for downloading files through urls
    Speed up the process with multi-threads if the file size is larger than self.bound_size
    """

    def __init__(self, cdn, thread_count=4) -> None:
        self.cdn = cdn
        self.bound_size = 1024 * 1024 * 8  # 1MB
        self.thread_count = thread_count

    @property
    def cdn(self):
        return self.__cdn

    @cdn.setter
    def cdn(self, cdn):
        if not os.path.isdir(cdn):
            self.__cdn = './'

    @property
    def bound_size(self):
        return self.__thread_size

    @bound_size.setter
    def bound_size(self, thread_size):
        if thread_size > 0:
            self.__thread_size = thread_size

    @property
    def thread_count(self):
        return self.__thread_count

    @thread_count.setter
    def thread_count(self, thread_count):
        if 1 < thread_count < 20:
            self.__thread_count = thread_count

    def download(self, url, path='', filename=''):
        """
        Download a file by the url
        Use multi threads to download if
        :return: (code, msg)
        """
        if not os.path.isdir(path):
            path = self.cdn
        if filename == '':
            filename = os.path.basename(url.rstrip('/'))
        filepath = os.path.join(path, filename)
        if os.path.isfile(filepath):
            return 409, 'File exists: %s' % filepath
        code, msg, args = pre_download(url)
        if code != 200:
            return code, msg
        total_size = args['size']

        # single thread to download small files
        if total_size <= self.bound_size:
            logger.info('Downloading from %s to %s', url, filepath)
            with open(filepath, 'wb') as fp:
                with urlopen(Request(quote_url(url), headers=base_headers, method='GET')) as r:
                    fp.write(r)
            logger.info('Success downloading: %s', filepath)
            return 200, 'OK'

        thread_size = total_size // self._DownloadThread.block_size + 1
        threads = []
        for i in range(self.thread_count):
            fp = open(filepath, 'wb')
            thread = self._DownloadThread(url, i * thread_size, thread_size, fp)
            threads.append(thread)
            thread.start()

        queue = [(time.time(), 0)] * 10
        total_size_str = self.__size2str(total_size)
        while not all([t.done for t in threads]):
            done_size = sum([t.done_size for t in threads])
            queue.pop(0)
            queue.append((time.time(), done_size))
            current_speed = (queue[-1][1] - queue[0][1]) / (queue[-1][0] - queue[0][0])
            left_time = (total_size - done_size) // current_speed
            print('\rDownloading: %s/s, %.2f%%, %s, %s' % (self.__size2str(current_speed), done_size / total_size, self.__time2str(left_time), total_size_str),
                  end='', flush=True)
            time.sleep(0.1)

    @staticmethod
    def __size2str(size):
        for u in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return '%.2f %s' % (size, u)
            size /= 1024
        return '%.2f TB' % size

    @staticmethod
    def __time2str(seconds):
        m, s = divmod(seconds, 60)
        time_str = '%d s' % s
        if m > 0:
            h, m = divmod(m, 60)
            time_str = '%d min %s' % (m, time_str)
            if h > 0:
                time_str = '%d h %s' % (h, time_str)
        return time_str

    class _DownloadThread(threading.Thread):

        block_size = 1024

        def __init__(self, url, start: int, size: int, fp):
            super().__init__()
            self.__url = url
            self.__fp = fp
            self.__fp.seek(start)
            self.__start = start
            self.__size = size
            self.__done_size = 0

        def run(self) -> None:
            with urlopen(self.__url) as response:
                response.seek(self.__start)
                while self.done < self.__size:
                    block = response.read(self.block_size)
                    if block is None or len(block) == 0:
                        break
                    self.__fp.write(block)
                    self.__done_size += len(block)
                self.__fp.close()

        @property
        def done_size(self):
            return self.__done_size

        @property
        def done(self):
            return self.done_size >= self.__size


class Thunder:
    """
    Call local Thunder COM object to add_task resources by using apis of win32com
    Version of Thunder needs to 9/X.
    """

    def __init__(self) -> None:
        self.__client = Dispatch('ThunderAgent.Agent64.1')

    @property
    def client(self):
        return self.__client

    def add_task(self, url, filename, refer_url=''):
        """
        add add_task task
        :param filename: basename of target file. It will be completed automatically if an extension isn't included.
            This is valid only when popping up a add_task panel.
        :param refer_url: netloc referred to
        :return:
        """
        self.__client.addTask(url, filename, '', '', refer_url, -1, 0, -1)

    def commit_tasks(self):
        """
        It is configurable in the Settings whether to pop up a add_task panel.
        """
        return self.__client.commitTasks()

    def cancel_tasks(self):
        """
        cancel all tasks added by self.add_task()
        """
        self.__client.cancelTasks()

    # todo following methods are unvalidated
    def get_info(self, info_name):
        """
        :param info_name: 'ThunderExists'/'ThunderRunning'/'ThunderVersion'/'PlatformVersion'
        :return:
        """
        return self.__client.getInfo(info_name)

    def get_info_struct(self):
        """
        :return: struct data of info including those in self.get_info()
        """
        self.__client.getInfoStruct()

    def invoke(self):
        return self.__client.Invoke()

    def release(self):
        return self.__client.release

    def get_task_info(self, url, info_name):
        """
        get info of specific task in the list
        :param info_name: optional values are as follows:
            'Exists':  if url exists in the list, 'true'/'false'
            'Path': save directory, ending with path separator, commonly '\'
            'FileName':
            'FileSize': 0 for unknown size
            'CompletedSize':
            'Percent': progress, %.1f, 70.0 for example
            'Status': running/stopped/failed/success/creatingfile/connecting
        :return:
        """
        return self.__client.getTaskInfo(url, info_name)

    def get_task_info_struct(self):
        """
        :return:
        """
        return self.__client.getTaskInfoStruct()

    def execute_command(self):
        return self.__client.excuteCommand()

    def add_ref(self):
        return self.__client.addRef()


class IDM:
    """
    Use local IDM to add_task resources by calling command lines.
    """

    def __init__(self, client_path, default_path='') -> None:
        self.__client = client_path  # full path is required if not added to environment paths of system
        self.default_path = default_path

    @property
    def default_path(self):
        return self.__default_path

    @default_path.setter
    def default_path(self, path):
        if not os.path.isdir(path):
            path = './'
        self.__default_path = path

    def add_task(self, url, path='', filename='', silent=False, queue=True):
        """
        :param url: only http/https
        :param path: local path to save the file. self.default_path will be used if specific path doesn't exist.
        :param filename: local file name. Basename will be truncated if filename contains '/'
        :param silent: whether to turn on the silent mode when IDM does't ask any questions.
                    When it occurs to duplicate urls, there is a warning dialog if silent is False.
                    Otherwise, add a duplicate task whose downloaded file will replace the former one.
        :param queue: whether to add this to add_task queue and not to start downloading automatically
        :return:
        """
        commands = [self.__client, '/d', quote_url(url)]
        if not os.path.isdir(path):
            path = self.default_path
        if path is not None:
            commands += ['/p', path]
        if filename != '':
            filename = os.path.basename(filename)
            root, ext = os.path.splitext(filename)
            if ext == '':
                ext = os.path.splitext(url)[1]
            commands += ['/f', root + ext]
        if silent:
            commands.append('/n')
        if queue:
            commands.append('/a')
        return self.__capture_output(run(commands, capture_output=True, timeout=30, check=True))

    def start_queue(self):
        return self.__capture_output(run([self.__client, '/s']))

    @staticmethod
    def __capture_output(cp: CompletedProcess):
        if cp.stdout != b'':
            logger.info(cp.stdout)
        if cp.returncode != 0:
            logger.error('Error command: %s', ' '.join(cp.args))
            logger.error(cp.stderr)
        return cp.returncode
