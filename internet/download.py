#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Customized downloader.

@Author Kingen
"""
import logging
import os
import socket
import threading
import time
from urllib import parse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from win32com.client import Dispatch

from internet import base_headers


class Thunder:
    """
    Calls local Thunder COM object to add_task resources by using apis of win32com
    Version of Thunder needs to 9/X.
    """

    def __init__(self) -> None:
        self.__client = Dispatch('ThunderAgent.Agent64.1')

    def add_task(self, url, filename, refer_url=''):
        """
        Adds add_task task
        @param url:
        @param filename: basename of target file. It will be completed automatically if an extension isn't included.
            This is valid only when popping up a add_task panel.
        @param refer_url: netloc referred to
        @return:
        """
        self.__client.addTask(url, filename, '', '', refer_url, -1, 0, -1)

    def commit_tasks(self):
        """
        It is configurable in the Settings whether to pop up a add_task panel.
        """
        return self.__client.commitTasks()

    def cancel_tasks(self):
        """
        Cancels all tasks added by self.add_task()
        """
        self.__client.cancelTasks()


def quote_url(url: str) -> str:
    """
    Encode the url except the scheme and netloc only when doing a request
    """
    scheme, netloc, path, query, fragment = parse.urlsplit(url)
    return parse.urlunsplit((scheme, netloc, parse.quote(path), parse.quote(query, safe='=&'), parse.quote(fragment)))


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
            logging.info('Pre-GET from %s', req.full_url)
            with urlopen(req, timeout=timeout) as r:
                size = r.getheader('Content-Length')
                if size is None:
                    logging.error('Unknown Content Length')
                    return 1, 'Unknown Content Length', None
                else:
                    return 200, 'OK', {'size': int(size)}
        except socket.timeout:
            logging.error('Timeout')
            if timeout_count >= retry:
                return 408, 'Timeout', None
            timeout_count += 1
            logging.info('Retry...')
            time.sleep(timeout)
        except HTTPError as e:
            logging.error(e)
            return e.code, e.reason, None
        except URLError as e:
            logging.error(e)
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
                    logging.info('Retry...')
                    time.sleep(timeout)
                    continue
                if isinstance(e, ConnectionRefusedError):
                    if refused_count >= retry:
                        return e.errno, e.strerror, None
                    refused_count += 1
                    logging.info('Retry...')
                    time.sleep(timeout)
                    continue
            logging.error('Unknown error')
            raise e
        except ConnectionResetError as e:
            logging.error(e)
            if reset_count >= retry:
                return e.errno, e.strerror, None
            reset_count += 1
            logging.info('Retry...')
            time.sleep(timeout)


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
        else:
            self.__cdn = cdn

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

    def download(self, url, path='', filename='', multi_thread=False):
        """
        Download a file from the url
        @param multi_thread:
        @param filename:
        @param path:
        @param url: unquoted
        @return: (code, msg)
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

        # download small files
        if total_size <= self.bound_size:
            logging.info('Downloading from %s to %s', url, filepath)
            with open(filepath, 'wb') as fp:
                with urlopen(Request(quote_url(url), headers=base_headers, method='GET')) as r:
                    fp.write(r)
            logging.info('Success downloading: %s', filepath)
            return 200, 'OK'

        # single thread
        if not multi_thread:
            logging.info('Downloading from %s to %s', url, filepath)
            with open(filepath, 'wb') as fp:
                with urlopen(Request(quote_url(url), headers=base_headers, method='GET')) as r:
                    done_size = 0
                    while True:
                        block = r.read(self._DownloadThread.block_size)
                        if block is None or len(block) == 0:
                            break
                        fp.write(block)
                        done_size += len(block)
                        print('\rDownloading: %.2f%%, %s/%s' % (done_size / total_size, self.__size2str(done_size), self.__size2str(total_size)), end='', flush=True)
            logging.info('Success downloading: %s', filepath)
            return 200, 'OK'

        # todo too slowly
        thread_size = total_size // self._DownloadThread.block_size + 1
        threads = []
        for i in range(self.thread_count):
            fp = open(filepath, 'wb')
            thread = self._DownloadThread(url, i * thread_size, thread_size, fp)
            threads.append(thread)
            thread.start()

        queue = [(time.time(), 0)] * 10
        time.sleep(0.1)
        total_size_str = self.__size2str(total_size)
        while not all([t.done for t in threads]):
            done_size = sum([t.done_size for t in threads])
            queue.pop(0)
            queue.append((time.time(), done_size))
            current_speed = (queue[-1][1] - queue[0][1]) / (queue[-1][0] - queue[0][0])
            left_time_str = self.__time2str((total_size - done_size) // current_speed) if current_speed != 0 else 'No limit'
            print('\rDownloading: %s/s, %.2f%%, %s, %s, %s' % (self.__size2str(current_speed), done_size / total_size, left_time_str, self.__size2str(done_size), total_size_str),
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

        block_size = 4096  # 4KB

        def __init__(self, url, start: int, size: int, fp):
            super().__init__()
            self.__req = Request(quote_url(url), headers={
                'Range': 'bytes=%d-%d' % (start, start + size),
                **base_headers
            }, method='GET')
            self.__fp = fp
            self.__fp.seek(start)
            self.__start = start
            self.__size = size
            self.__done_size = 0

        def run(self) -> None:
            with urlopen(self.__req) as response:
                if response.code == 206:
                    while not self.done:
                        block = response.read(self.block_size)
                        if block is None or len(block) == 0:
                            break
                        self.__fp.write(block)
                        self.__done_size += len(block)
                    self.__fp.close()
                else:
                    logging.warning('No support for Range')

        @property
        def done_size(self):
            return self.__done_size

        @property
        def done(self):
            return self.done_size >= self.__size
