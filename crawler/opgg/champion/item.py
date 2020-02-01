import requests
from bs4 import BeautifulSoup


def get_items(champion_name, lane):
    """
    Get recommended items for the champion and the lane.
    :param champion_name:
    :param lane:
    :return: the json file for the recommended items.
    """
    request_url = 'https://www.op.gg/champion/{}/statistics/{}/item'.format(champion_name, lane)
    headers = {
        'Host': 'www.op.gg',
        'Accept-Language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'
    }
    page_text = requests.get(request_url, headers=headers).text
    print(page_text)
    with open('page.html', 'w', encoding='utf-8') as file:
        file.write(page_text)
    soup = BeautifulSoup(page_text, 'html.parser')


if __name__ == '__main__':
    get_items('masteryi', 'jungle')
