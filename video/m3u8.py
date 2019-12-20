#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description download *.m3u8
@Module m3u8

@Author Kingen
@Date 2019/12/20
@Version 1.0
"""
import datetime
import os
import time

import requests
from bs4 import BeautifulSoup
from pip._vendor import requests
from selenium import webdriver

HOST = 'wx.exectas9.cn'
TS_URL_FORMAT = 'https://v3.szjal.cn/{}'


def chrome(url):
    browser = webdriver.Chrome()
    browser.get(url)
    print(browser.page_source)
    soup = BeautifulSoup(browser.page_source, features='html.parser')


def get_url(url, headers=None):
    if headers is None:
        headers = {}
    print('Request {}'.format(url))
    home_page = requests.get(url, headers=headers).text
    print(home_page)
    return home_page


def get_episode(episode):
    headers = {
        # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
        # 'Accept-Encoding': 'gzip, deflate',
        # 'Accept-Language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8',
        # 'Cache-Control': 'max-age=0',
        # 'Connection': 'keep-alive',
        # 'Host': HOST,
        # 'Referer': 'http://{}/index.php/vod/play/id/132794/sid/1/nid/{}.html'.format(HOST, episode + 1),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36'
    }
    url = 'http://{}/index.php/vod/play/id/132794/sid/1/nid/{}.html'.format(HOST, episode)
    return get_url(url, headers)


def download():
    root_path = 'D:\\Downloads\\qingyunian'
    for root, dirs, files in os.walk(root_path):
        for file_name in files:
            ts_urls = []
            filepath = os.path.join(root, file_name)
            name, suffix = os.path.splitext(file_name)
            dest_path = os.path.join(root, name + '.ts')
            if os.path.exists(dest_path):
                print('%s exists. Download next.' % dest_path)
                continue

            with open(filepath, "r") as file:
                for line in file.readlines():
                    if line.endswith(".ts\n"):
                        ts_urls.append(TS_URL_FORMAT.format(line.strip("\n")))

            ts_paths = []
            ts_dir = os.path.join(root, name)
            if not os.path.exists(ts_dir):
                os.mkdir(ts_dir)
            for i in range(len(ts_urls)):
                ts_path = os.path.join(ts_dir, "{}.ts".format(i))
                ts_paths.append(ts_path)
                ts_url = ts_urls[i]

                if os.path.exists(ts_path):
                    print('%s exits. Try next.' % ts_path)
                    continue

                print("Downloading from %s to %s" % (ts_url, ts_path))
                time.sleep(0.1)
                start = datetime.datetime.now().replace(microsecond=0)
                try:
                    response = requests.get(headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36'
                    }, url=ts_url, stream=True, verify=False)
                except Exception as e:
                    print("Exception：%s" % e.args)
                    return

                with open(ts_path, "wb+") as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)

                end = datetime.datetime.now().replace(microsecond=0)
                print("Cost：%s s." % (end - start))

            with open(dest_path, 'wb+') as dest_file:
                for ts_path in ts_paths:
                    dest_file.write(open(ts_path, 'rb').read())


if __name__ == '__main__':
    download()
