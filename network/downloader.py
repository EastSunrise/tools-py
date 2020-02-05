from urllib import request
from urllib.request import Request, urlopen, ProxyHandler


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
            print("retrieving url... %s" % url)
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
