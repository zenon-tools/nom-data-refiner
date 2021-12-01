import requests
import json


class HttpWrapper(object):

    @staticmethod
    async def get(url):
        response = requests.get(
            url,)
        return json.loads(response.text)

    @staticmethod
    async def post(url, data, headers={
        'Content-type': 'application/json',
    }):
        response = requests.post(
            url, headers=headers, json=data)
        return json.loads(response.text)
