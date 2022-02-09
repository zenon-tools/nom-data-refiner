import requests
import json


class HttpWrapper(object):

    @staticmethod
    async def get(url):
        try:
            response = requests.get(
                url, timeout=10)
            return json.loads(response.text) if response.status_code == 200 else {}
        except requests.ReadTimeout as e:
            print(f'Request timeout: {e}')
            return {}

    @staticmethod
    async def post(url, data, headers={
        'Content-type': 'application/json',
    }):
        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=15)
            return json.loads(response.text) if response.status_code == 200 else {}
        except requests.ReadTimeout as e:
            print(f'Request timeout: {e}')
            return {}
