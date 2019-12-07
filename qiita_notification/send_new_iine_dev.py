import json
import os
from math import ceil
from typing import List, Dict, Any, Union, Tuple
import json
from urllib.request import Request
from urllib import request, parse, error
from http.client import HTTPResponse


class Response():
    """Http Response Object"""

    def __init__(self, res: HTTPResponse):
        self.body = self._json(res)
        self.status_code = self._status_code(res)
        self.headers = self._headers(res)

    def _json(self, res: HTTPResponse):
        return json.loads(res.read())

    def _status_code(self, res: HTTPResponse) -> int:
        return res.status

    def _headers(self, res: HTTPResponse) -> Dict[str, str]:
        return dict(res.getheaders())


def req_get(url: str, headers=None, params=None) -> Response:
    """get request. simplified request function of Requests
    :return: Response object
    """
    if params:
        url = '{}?{}'.format(url, parse.urlencode(params))

    req = Request(url, headers=headers, method='GET')

    with request.urlopen(req) as res:
        response = Response(res)
    return response


def req_post(url: str, data: Dict[str, Any], headers=None, params=None) -> Response:
    """post request. simplified request function of Requests
    :return: Response object
    """
    if headers.get('Content-Type') == 'application/x-www-form-urlencoded':
        encoded_data = parse.urlencode(data).encode()

    else:
        encoded_data = json.dumps(data).encode()

    req = Request(url, data=encoded_data, headers=headers, method='POST')

    with request.urlopen(req) as res:
        response = Response(res)
    return response


def serialize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """serialize data of Dynamo DB Stream
    :return:
    """
    if record.get('eventName') != 'MODIFY':
        return {}

    past = record.get('dynamodb', {}).get('OldImage')
    past_iine = int(past.get('iine', {}).get('N', 0))
    ids = past.get('ids', {}).get('S', '')

    new = record.get('dynamodb', {}).get('NewImage')
    title = new.get('title', {}).get('S', '')
    return {
        'ids': ids,
        'title': title,
        'past_iine': past_iine
    }


def serialize_response_name(response: Response, num: int, title: str) -> Dict[str, Any]:
    """serialize iine data of Qiita API v2
    :param response:
    :return:
    """
    size = len(response.body) - num
    if size <= 0:
        users: List[str] = []

    new_iine = response.body[:size]
    users = [
        resp.get('user', {}).get('id') for resp in new_iine
    ]
    return {
        'title': title,
        'users': users
    }


def get_new_iine(item: Dict[str, Any], token: str) -> Dict[str, Any]:
    """HTTP request to Qiita API v2
    :params:
    :return: 
    """
    headers = {'Authorization': 'Bearer {}'.format(token)}
    ids = item.get('ids', '')
    past_iine = item.get('past_iine', 0)
    url = f'https://qiita.com/api/v2/items/{ids}/likes'

    response = req_get(url, headers=headers)
    title: str = item.get('title', '')
    resp = serialize_response_name(response, past_iine, title)
    return resp


def deserialize_response_name(response: Dict[str, Any], max_length=20) -> str:
    """deserialize text for LINE Notify
    :param max_length: max sentence length
    :return:
    """
    names = ", ".join(response.get('users', []))
    title = response.get('title', '')
    title = f"{title}" if len(title) <= max_length else f"{title[:max_length]}..."
    return f"\n{names}が「{title}」にいいねしました。"


def send_notification(message: str, token: str):
    """send notification by LINE notify"""
    url = 'https://notify-api.line.me/api/notify'

    headers = {
        'Authorization': 'Bearer {}'.format(token),
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    msg = {
        'message': message
    }
    response = req_post(url, data=msg, headers=headers)
    return response.body


def lambda_handler(event, context):
    """main handler for Lambda"""
    qiita_token = os.environ["QIITA_TOKEN"]
    line_token = os.environ["LINE_TOKEN"]

    records = event.get('Records', [])
    for record in records:
        serialized_data = serialize_record(record)
        if not serialized_data:
            continue
        new_iines = get_new_iine(serialized_data, qiita_token)
        if len(new_iines.get('users')) == 0:
            continue
        send_notification(deserialize_response_name(new_iines), line_token)

    return {
        'statusCode': 200,
    }
