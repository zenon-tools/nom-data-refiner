from utils.http_wrapper import HttpWrapper

class MarketWrapper(object):
    BASE_URL = 'https://api.coingecko.com/api/v3'

    async def get_price_usd(self, coin):
        r = await HttpWrapper.get(f'{self.BASE_URL}/coins/{coin}')
        try:
            return r['market_data']['current_price']['usd']
        except Exception as e:
            print(f'get_price_usd: {str(e)}')
            return 0

    async def get_price_history(self, coin, currency):
        r = await HttpWrapper.get(f'{self.BASE_URL}/coins/{coin}/market_chart?vs_currency={currency}&days=max&interval=daily')
        try:
            return r['prices']
        except Exception as e:
            print(f'get_price_history: {str(e)}')
            return []