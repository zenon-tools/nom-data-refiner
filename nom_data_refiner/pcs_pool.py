import asyncio
import math
import json
import time

from datetime import datetime, timezone, timedelta
from utils.http_wrapper import HttpWrapper


class PcsPool(object):

    # Constants
    BITQUERY_API_URL = 'https://graphql.bitquery.io'
    BSC_SCAN_API_URL = 'https://api.bscscan.com/api'

    POOL_ADDRESS = '0xe6b03fcb16daf3462ddfb8b0afb3f0e87d38d884'
    WBNB_ADDRESS = '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
    WZNN_ADDRESS = '0x84b174628911896a3b87Fa6980D05Dbc2eE74836'
    POOL_REWARD_FEE_SHARE = 0.0017
    MOVING_AVERAGE_LENGTH_IN_DAYS = 7
    DAYS_PER_YEAR = 12 * 30

    wznn_reserve = 0
    wbnb_reserve = 0
    wznn_price_usd = 0
    wbnb_price_usd = 0
    liquidity_usd = 0
    weekly_volume_usd = 0
    yearly_trading_fees_usd = 0
    impermanent_loss = 0
    cake_lp_total_supply = 0

    reference_cake_lp_balance = 0
    reference_address_reward_share = 0

    bitquery_api_key = ''
    bsc_scan_api_key = ''

    data_store_dir = ''

    async def update(self, data_store_dir, znn_price_usd, bnb_price_usd, reference_cake_lp_balance, bitquery_api_key, bsc_scan_api_key):
        self.data_store_dir = data_store_dir
        self.wznn_price_usd = znn_price_usd
        self.wbnb_price_usd = bnb_price_usd
        self.bitquery_api_key = bitquery_api_key
        self.bsc_scan_api_key = bsc_scan_api_key
        self.reference_cake_lp_balance = reference_cake_lp_balance
        await self.__update_pool_balances()
        await self.__update_cake_lp()
        await self.__update_pcs_pool_data()

    async def __update_pool_balances(self):
        file = f'{self.data_store_dir}/pool_balances_cache.json'
        r = self.__read_file(file)
        timestamp = math.trunc(time.time())

        if r is None or len(r['wbnb_data']) == 0 or len(r['wznn_data']) == 0 or r['timestamp'] + 590 < timestamp:
            r_wbnb = await HttpWrapper.get(f'{self.BSC_SCAN_API_URL}?module=account&action=tokenbalance&contractaddress={self.WBNB_ADDRESS}&address={self.POOL_ADDRESS}&tag=latest&apikey={self.bsc_scan_api_key}')
            r_wznn = await HttpWrapper.get(f'{self.BSC_SCAN_API_URL}?module=account&action=tokenbalance&contractaddress={self.WZNN_ADDRESS}&address={self.POOL_ADDRESS}&tag=latest&apikey={self.bsc_scan_api_key}')

            if 'result' in r_wbnb and 'result' in r_wznn:
                self.__write_to_file_as_json(
                    {'wbnb_data': r_wbnb, 'wznn_data': r_wznn, 'timestamp': timestamp}, file)
                print('Refreshed pool balances data')
            else:
                r_wbnb = r['wbnb_data']
                r_wznn = r['wznn_data']
                print('Refresh failed. Used pool balances cache')
        else:
            r_wbnb = r['wbnb_data']
            r_wznn = r['wznn_data']
            print('Used pool balances cache')

        try:
            self.wbnb_reserve = float(r_wbnb['result']) / 1000000000000000000
            self.wznn_reserve = float(r_wznn['result']) / 100000000
            self.liquidity_usd = self.wznn_reserve * self.wznn_price_usd + \
                self.wbnb_reserve * self.wbnb_price_usd

        except KeyError:
            print('Error: __update_pool_balances')

    async def __update_cake_lp(self):
        file = f'{self.data_store_dir}/cake_lp_supply_cache.json'
        r = self.__read_file(file)
        timestamp = math.trunc(time.time())

        if r is None or len(r['data']) == 0 or r['timestamp'] + 590 < timestamp:
            r = await HttpWrapper.get(f'{self.BSC_SCAN_API_URL}?module=stats&action=tokensupply&contractaddress={self.POOL_ADDRESS}&apikey={self.bsc_scan_api_key}')

            if 'result' in r:
                self.__write_to_file_as_json(
                    {'data': r, 'timestamp': timestamp}, file)
                print('Refreshed Cake LP supply data')
            else:
                r = r['data']
                print('Refresh failed. Used Cake LP supply cache')
        else:
            r = r['data']
            print('Used Cake LP supply cache')

        try:
            self.cake_lp_total_supply = float(
                r['result']) / 1000000000000000000
        except KeyError:
            print('Error: __update_cake_lp')

        self.reference_address_reward_share = self.reference_cake_lp_balance / self.cake_lp_total_supply

    async def __update_pcs_pool_data(self):
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=self.MOVING_AVERAGE_LENGTH_IN_DAYS)
        week_ago = week_ago.strftime('%Y-%m-%dT%H:%M:%SZ')

        trades_query_params = f'dexTrades(options: {{ desc: "date.date" }} time: {{ since: "{week_ago}" }} smartContractAddress: {{ is: "{self.POOL_ADDRESS}" }})'
        trades_query_subfields = '{ date { date(format: "%y-%m-%d") } tradeAmount(in:USD) }'
        balances_query_params = f'address(address: {{ is: "{self.POOL_ADDRESS}" }} )'
        balances_query_subfields = '{ balances { currency { symbol } value } }'
        start_reserves_query_params = f'startReserves: smartContractEvents(smartContractAddress: {{ is: "{self.POOL_ADDRESS}" }}  options: {{ limit: 1, asc: "block.height" }} smartContractEvent: {{ is: "Sync" }} time: {{ since: "{week_ago}" }} )'
        start_reserves_query_subfields = '{ arguments { value argument } block { height } }'
        end_reserves_query_params = f'endReserves: smartContractEvents(smartContractAddress: {{ is: "{self.POOL_ADDRESS}" }}  options: {{ limit: 1, desc: "block.height" }} smartContractEvent: {{ is: "Sync" }} )'
        end_reserves_query_subfields = '{ arguments { value argument } block { height } }'

        body = {
            'query': '{ ethereum(network: bsc) {' + trades_query_params + ' ' + trades_query_subfields + ' '
            + balances_query_params + ' ' + balances_query_subfields
            + start_reserves_query_params + ' ' + start_reserves_query_subfields
            + end_reserves_query_params + ' ' + end_reserves_query_subfields
            + '} }'}

        file = f'{self.data_store_dir}/pcs_pool_data_cache.json'
        data = self.__read_file(file)
        timestamp = math.trunc(time.time())

        if data is None or data['timestamp'] + 590 < timestamp:
            r = await HttpWrapper.post(self.BITQUERY_API_URL, body, headers={
                'Content-type': 'application/json',
                'X-API-KEY': self.bitquery_api_key
            })
            if 'data' in r:
                self.__write_to_file_as_json(
                    {'data': r, 'timestamp': timestamp}, file)
                print('Refreshed data PCS pool data')
                data = r
            else:
                data = data['data']
                print('Refresh failed. Used PCS pool data cache')
        else:
            data = data['data']
            print('Used PCS pool data cache')

        try:
            self.weekly_volume_usd = 0
            for day_data in data['data']['ethereum']['dexTrades']:
                self.weekly_volume_usd = self.weekly_volume_usd + \
                    float(day_data['tradeAmount'])

            wznn_reserve_end = float(
                data['data']['ethereum']['endReserves'][0]['arguments'][0]['value']) / 100000000
            wbnb_reserve_end = float(
                data['data']['ethereum']['endReserves'][0]['arguments'][1]['value']) / 1000000000000000000
            wznn_reserve_start = float(
                data['data']['ethereum']['startReserves'][0]['arguments'][0]['value']) / 100000000
            wbnb_reserve_start = float(
                data['data']['ethereum']['startReserves'][0]['arguments'][1]['value']) / 1000000000000000000

            # Use liquidity from BSC Scan for now
            # self.liquidity_usd = self.wznn_reserve * self.wznn_price_usd + \
            #     self.wbnb_reserve * self.wbnb_price_usd

            self.yearly_trading_fees_usd = self.weekly_volume_usd * \
                self.POOL_REWARD_FEE_SHARE / self.MOVING_AVERAGE_LENGTH_IN_DAYS * self.DAYS_PER_YEAR

            self.impermanent_loss = self.__calculate_impermanent_loss(
                wznn_reserve_start, wbnb_reserve_start, wznn_reserve_end, wbnb_reserve_end)

        except KeyError:
            print('Error: __update_pcs_pool_data')

    def __calculate_impermanent_loss(self, token_reserve_start, base_reserve_start, token_reserve_end, base_reserve_end):
        end_price_ratio = base_reserve_end / token_reserve_end
        product_constant = base_reserve_start * token_reserve_start
        hold_strategy = (token_reserve_start *
                         end_price_ratio) + base_reserve_start
        lp_strategy = ((math.sqrt(product_constant / end_price_ratio)) *
                       end_price_ratio) + math.sqrt(product_constant * end_price_ratio)
        impermanent_loss = (hold_strategy - lp_strategy) / hold_strategy * 100
        return impermanent_loss

    def __read_file(self, file_name):
        try:
            f = open(file_name)
            content = json.load(f)
            f.close()
            return content
        except:
            return None

    def __write_to_file_as_json(self, data, file_name):
        with open(file_name, 'w') as outfile:
            json.dump(data, outfile, indent=4)
