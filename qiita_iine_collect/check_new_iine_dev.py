import os
from math import ceil
from typing import List, Dict, Any, Union, Tuple
import json
from urllib.request import Request
from urllib import request, parse, error
from http.client import HTTPResponse
import boto3
from botocore.exceptions import ClientError


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


def req_get(url, headers=None, params=None) -> Response:
    """get request. simplified request function of Requests
    :return: Response object
    """
    if params:
        url = '{}?{}'.format(url, parse.urlencode(params))

    req = Request(url, headers=headers, method='GET')

    with request.urlopen(req) as res:
        response = Response(res)
    return response


def serialize_response(response: Response) -> List[Dict[str, Any]]:
    """serialize response of Qiita API v2
    :param response:
    :return:
    """
    keys = ['id', 'title', 'likes_count']
    return [
        {f: resp.get(f) for f in keys} for resp in response.body
    ]


def get_item(url: str, headers: Dict[str, str], **param) -> List[Dict[str, Any]]:
    """get a item by Qiita API v2 and return the list of serialized response (dictionary)"""
    response = req_get(url, headers=headers, params=param)
    return serialize_response(response)


def get_items(token: str, per_page=1, url='https://qiita.com/api/v2/authenticated_user/items') -> List[Dict[str, Any]]:
    """ページネーションして認証ユーザの全ての記事を取得する
    :return: 記事のリスト
    """
    headers = {'Authorization': 'Bearer {}'.format(token)}

    response: Response = req_get(url, headers=headers, params={'page': 1, 'per_page': per_page})
    items = serialize_response(response)
    tot_count = int(response.headers['Total-Count'])
    tot_pages = ceil(tot_count / per_page)
    if tot_pages <= 1:
        return items

    for page in range(2, tot_pages + 1):
        items += get_item(url, headers, page=page, per_page=per_page)
    return items


def update_logs(items: List[Dict[str, Any]]):
    """Update the number of iine in Dynamo DB
    If item ID do not exist in Dynamo DB, insert them in it
    """
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('iine_qiita_logs')

    for item in items:
        ids = item.get('id')
        title = item.get('title')
        iine = item.get('likes_count')

        try:
            response = table.update_item(
                Key={
                    'ids': ids
                },
                UpdateExpression="set iine = :newiine, title = :title",
                ConditionExpression="attribute_not_exists(ids) or iine <> :newiine",
                ExpressionAttributeValues={
                    ":newiine": iine,
                    ":title": title
                },
            )
        except ClientError as e:
            if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                print(e.response['Error']['Message'])
            else:
                raise


def main(client, content):
    """this is handler function for Lambda"""
    qiita_token: str = os.environ['QIITA_TOKEN']
    url: str = os.environ['QIITA_URL']
    per_page = int(os.environ['PER_PAGE'])

    items: List[Dict[str, Any]] = get_items(qiita_token, per_page=per_page, url=url)
    update_logs(items)
    return {
        'statusCode': 200
    }
