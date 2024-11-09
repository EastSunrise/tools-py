#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
APIs of Weixin.

@Author Kingen
"""
import json
import os
from datetime import datetime, timedelta

from requests import Response

import common
from internet import BaseSite

log = common.get_logger()


class ApiException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(self.message)  # Call the base class constructor

    def __str__(self):
        return f"Error {self.code}: {self.message}"


class WeixinApi(BaseSite):
    def __init__(self, appid, secret):
        super().__init__('https://api.weixin.qq.com/', name='Weixin', headers={})
        self.__appid = appid
        self.__secret = secret
        self.__access_token = None
        self.__expires_at = datetime(1970, 1, 1)

    def __get_access_token(self) -> str:
        if self.__expires_at < datetime.now() + timedelta(minutes=5):
            params = {
                'grant_type': 'client_credential',
                'appid': self.__appid,
                'secret': self.__secret,
            }
            body = self.get_json('/cgi-bin/token', params)
            self.__access_token = body['access_token']
            self.__expires_at = datetime.now() + timedelta(seconds=body['expires_in'])
        return self.__access_token

    def _do_get(self, path, params=None):
        if params is None:
            params = {}
        if path != '/cgi-bin/token':
            params['access_token'] = self.__get_access_token()
        return super()._do_get(path, params)

    def _do_request(self, path, method='POST', query=None, **kwargs) -> Response:
        if query is None:
            query = {}
        query['access_token'] = self.__get_access_token()
        return super()._do_request(path, method, query, **kwargs)

    def __handle_error(self, body):
        if 'errcode' in body and body['errcode'] != 0:
            ex = ApiException(body['errcode'], body['errmsg'])
            log.error('%s', ex)
            raise ex
        return body

    def post_json(self, path, query=None, cache=False, retry=False, **kwargs):
        body = super().post_json(path, query, cache, retry, **kwargs)
        return self.__handle_error(body)

    def get_json(self, path, params=None, cache=False, retry=False):
        body = super().get_json(path, params, cache, retry)
        return self.__handle_error(body)

    def add_draft(self, title, content, thumb_media_id, author=None, digest=None, content_source_url=None, need_open_comment=1,
                  only_fans_can_comment=0, pic_crop_235_1=None, pic_crop_1_1=None):
        """
        Creates a draft.
        @return: the media id of created draft
        """
        draft = {
            'title': title,
            'content': content,
            'thumb_media_id': thumb_media_id,
            'author': author,
            'digest': digest,
            'content_source_url': content_source_url,
            'need_open_comment': need_open_comment,
            'only_fans_can_comment': only_fans_can_comment,
            'pic_crop_235_1': pic_crop_235_1,
            'pic_crop_1_1': pic_crop_1_1
        }
        payload = json.dumps({'articles': [draft]}, ensure_ascii=False).encode('utf-8')
        body = self.post_json('/cgi-bin/draft/add', data=payload)
        log.debug('Created draft: %s', body)
        return body['media_id']

    def add_material(self, media_type, filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)
        with open(filepath, 'rb') as fp:
            body = self.post_json(f'/cgi-bin/material/add_material?type={media_type}', files={'media': fp})
            log.debug('Added material: %s', body)
            return body['media_id'], body['url']
