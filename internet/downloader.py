import base64
import os
from urllib import request
from urllib.request import Request, urlopen, ProxyHandler


def download_image(url, dst_dir, dst_name='example', fmt='.jpg'):
    """
    Download an image from the specific url to target directory.
    :param url:
    :param dst_dir:
    :param dst_name:
    :param fmt:
    :return:
    """
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/66.0.3359.139 Safari/537.36'}
    response = urlopen(Request(url, headers=header))
    if response.getcode() == 200:
        dst_path = os.path.join(dst_dir, dst_name + fmt)
        with open(dst_path, "wb") as f:
            print('Downloading to {} from {}'.format(dst_path, url))
            f.write(response.read())
        return dst_path
    return False


def transfer_thunder(thunder_url):
    """
    Transfer the url of thunder to format of 'http'
    :param thunder_url:
    :return:
    """
    return base64.b64decode(thunder_url.lstrip('thunder://')).decode('GB2312').strip('AAZZ')


class Downloader:
    fiddler_proxy = {'HTTPS': '127.0.0.1:10001'}
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/66.0.3359.139 Safari/537.36'}

    def __init__(self, charset='UTF-8') -> None:
        self.charset = charset

    def crawl(self, url):
        """
        return content by url.
        return empty string if response raise an HTTPError (not found, 500...)
        """
        try:
            print("Retrieving url... %s" % url)
            req = Request(url, headers=Downloader.header)

            response = urlopen(req, timeout=1)

            if response.url != req.full_url:
                return response.url
            return response.read().decode(self.charset)
        except Exception as e:
            print("error %s: %s" % (url, e))
            return ''

    @staticmethod
    def crawl_proxy(url, proxy):
        """
        通过代理爬取网页
        :param url:
        :param proxy: 代理map
        :return:
        """
        try:
            proxy_handler = ProxyHandler(proxy)
            opener = request.build_opener(proxy_handler)
            req = request.Request(url, headers=Downloader.header)
            response = opener.open(req)
            if response.url != req.full_url:
                return response.url
            return response.read().decode(req)
        except Exception as e:
            print("error %s: %s" % (url, e))
            return ''
