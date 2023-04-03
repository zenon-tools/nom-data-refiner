import json
import time
import os
import asyncio
import math
import datetime
from pcs_pool import PcsPool
from utils.market_wrapper import MarketWrapper
from nom_data import NomData


def read_file(file_name):
    f = open(file_name)
    content = json.load(f)
    f.close()
    return content


def write_to_file_as_json(data, file_name):
    with open(file_name, 'w') as outfile:
        json.dump(data, outfile, indent=4)


def write_nom_data_to_file(data, file_name):

    # Convert NoM data to JSON
    json_data = {
        'momentumHeight': data.momentum_height,
        'timestamp': math.trunc(time.time()),
        'nodeVersion': data.node_version,
        'znnPriceUsd': data.znn_price_usd,
        'qsrPriceUsd': data.qsr_price_usd,
        'totalStakedZnn': {
            'weightedAmount': data.total_staked_znn['weighted_amount'],
            'amount':  data.total_staked_znn['amount']
        },
        'avgStakingLockupTimeInDays': data.avg_staking_lockup_time_in_days,
        'totalDelegatedZnn': data.total_delegated_znn,
        'sentinelCount': data.sentinel_count,
        'pillarCount': data.pillar_count,
        'znnSupply': data.znn_supply,
        'qsrSupply': data.qsr_supply,
        'stakingApr': data.staking_apr,
        'delegateApr': data.delegate_apr,
        'lpApr': data.lp_apr,
        'sentinelApr': data.sentinel_apr,
        'pillarAprTop30': data.pillar_apr_top_30,
        'pillarAprNotTop30': data.pillar_apr_not_top_30,
        'yearlyZnnRewardPoolForLps': data.yearly_znn_reward_pool_for_lps,
        'yearlyZnnRewardPoolForSentinels': data.yearly_znn_reward_pool_for_sentinels,
        'yearlyQsrRewardPoolForStakers': data.yearly_qsr_reward_pool_for_stakers,
        'yearlyQsrRewardPoolForLps': data.yearly_qsr_reward_pool_for_lps,
        'yearlyQsrRewardPoolForSentinels': data.yearly_qsr_reward_pool_for_sentinels,
        'yearlyQsrRewardPoolForLpProgram': data.yearly_qsr_reward_pool_for_lp_program,
        'yearlyZnnMomentumRewardPoolForPillarsTop30': data.yearly_znn_momentum_reward_pool_for_pillars_top_30,
        'yearlyZnnMomentumRewardPoolForPillarsNotTop30': data.yearly_znn_momentum_reward_pool_for_pillars_not_top_30,
        'yearlyZnnDelegateRewardPoolForPillars': data.yearly_znn_delegate_reward_pool_for_pillars,
        'lpProgramParticipationRate': data.lp_program_participation_rate
    }

    # Dump data to file
    write_to_file_as_json(json_data, file_name)


def write_pillar_data_to_file(data, file_name):

    # Convert Pillar data to JSON
    json_data = {}
    for pillar in data.pillars:
        json_data[pillar.owner_address] = {
            'name': pillar.name,
            'rank': pillar.rank,
            # 'type': pillar.type,
            # 'ownerAddress': pillar.owner_address,
            # 'producerAddress': pillar.producer_address,
            # 'withdrawAddress': pillar.withdraw_address,
            # 'isRevocable': pillar.is_revocable,
            # 'revokeCooldown': pillar.revoke_cooldown,
            # 'revokeTimestamp': pillar.revoke_timestamp,
            'giveMomentumRewardPercentage': pillar.give_momentum_reward_percentage,
            'giveDelegateRewardPercentage': pillar.give_delegate_reward_percentage,
            'producedMomentums': pillar.produced_momentums,
            'expectedMomentums': pillar.expected_momentums,
            'weight': pillar.weight,
            'epochMomentumRewards': pillar.epoch_momentum_rewards,
            'epochDelegateRewards': pillar.epoch_delegate_rewards,
            'apr': pillar.apr,
            'delegateApr': pillar.delegate_apr,
            # 'timestamp': math.trunc(time.time()),
            # 'momentumHeight': data.momentum_height
        }

    # Dump data to file
    write_to_file_as_json(json_data, file_name)


def write_pcs_pool_data_to_file(data, file_name):

    # Convert PCS data to JSON
    json_data = {
        'timestamp': math.trunc(time.time()),
        'wZnnPriceUsd': data.wznn_price_usd,
        'wBnbPriceUsd': data.wbnb_price_usd,
        'impermanentLossPast7d': data.impermanent_loss,
        'liquidityUsd': data.liquidity_usd,
        'yearlyTradingFeesUsd': data.yearly_trading_fees_usd,
        'cakeLpTotalSupply': data.cake_lp_total_supply
    }

    # Dump data to file
    write_to_file_as_json(json_data, file_name)


def history_list_to_map(l):
    m = {}
    for e in l:
        m[e[0]] = e[1]
    return m


async def update():

    # Get file path
    path = os.path.dirname(os.path.abspath(__file__))

    # Read config
    cfg = read_file(f'{path}/config/config.json')

    # Data store directory
    DATA_STORE_DIR = f'{path}/data_store'

    # Create data store
    if not os.path.exists(DATA_STORE_DIR):
        os.makedirs(DATA_STORE_DIR, exist_ok=True)

    # Check if market cache exists. If not, create fallback data.
    if not os.path.exists(f'{DATA_STORE_DIR}/market_cache.json'):
        write_to_file_as_json(
            {'timestamp': math.trunc(time.time()), 'znn_price_usd': 1.75, 'qsr_price_usd': 0.175, 'bnb_price_usd': 335}, f'{DATA_STORE_DIR}/market_cache.json')

    # Check if market history cache exists. If not, create it.
    if not os.path.exists(f'{DATA_STORE_DIR}/market_history_cache.json'):
        write_to_file_as_json(
            {'znn': {'timestamp': 0, 'usd': [], 'eur': [], 'gbp': [], 'cad': [], 'aud': []}, }, f'{DATA_STORE_DIR}/market_history_cache.json')

    # Get coin prices.
    market = MarketWrapper()
    znn_price = await market.get_price_usd(coin='zenon')
    qsr_price = await market.get_price_usd(coin='quasar')
    bnb_price = await market.get_price_usd(coin='binancecoin')

    # If bad response use cached price data, else cache the new data.
    if znn_price == 0 or bnb_price == 0:
        market_cache = read_file(
            f'{DATA_STORE_DIR}/market_cache.json')
        znn_price = market_cache['znn_price_usd']
        qsr_price = market_cache['qsr_price_usd']
        bnb_price = market_cache['bnb_price_usd']
    else:
        write_to_file_as_json({'timestamp': math.trunc(time.time()), 'znn_price_usd': znn_price, 'qsr_price_usd': qsr_price, 'bnb_price_usd': bnb_price},
                              f'{DATA_STORE_DIR}/market_cache.json')

    # Update price history data
    market_history_cache = read_file(
        f'{DATA_STORE_DIR}/market_history_cache.json')
    refresh_interval_secs = 600  # 10 minutes

    if market_history_cache['znn']['timestamp'] + refresh_interval_secs < math.trunc(time.time()):
        print('Updating market history cache')
        znn_usd = await market.get_price_history(coin='zenon', currency='usd')
        znn_eur = await market.get_price_history(coin='zenon', currency='eur')
        znn_gbp = await market.get_price_history(coin='zenon', currency='gbp')
        znn_cad = await market.get_price_history(coin='zenon', currency='cad')
        znn_aud = await market.get_price_history(coin='zenon', currency='aud')
        if len(znn_usd) > 0 and len(znn_eur) > 0 and len(znn_gbp) > 0 and len(znn_cad) > 0 and len(znn_aud) > 0:
            write_to_file_as_json({'znn': {'timestamp': math.trunc(time.time()), 'usd': history_list_to_map(znn_usd),
                                           'eur': history_list_to_map(znn_eur), 'gbp': history_list_to_map(znn_gbp),
                                           'cad': history_list_to_map(znn_cad), 'aud': history_list_to_map(znn_aud)}, },
                                  f'{DATA_STORE_DIR}/market_history_cache.json')
        else:
            print('Unable to update market history cache')

    # Update PS data
    pcs_pool = PcsPool()
    await pcs_pool.update(DATA_STORE_DIR, znn_price, bnb_price, cfg['bsc_reference_address_cake_lp_balance'], cfg['bitquery_api_key'], cfg['bsc_scan_api_key'])

    # Update NoM data
    nom_data = NomData()
    await nom_data.update(node_url=cfg['node_url_http'],
                          reference_staking_address=cfg['reference_staking_address'],
                          reference_lp_address=cfg['reference_lp_address'],
                          znn_price_usd=znn_price,
                          qsr_price_usd=qsr_price,
                          pcs_pool=pcs_pool)

    # Write PCS data to file
    write_pcs_pool_data_to_file(
        pcs_pool, f'{DATA_STORE_DIR}/pcs_pool_data.json')

    # Write NoM data to file
    write_nom_data_to_file(
        nom_data, f'{DATA_STORE_DIR}/nom_data.json')

    # Write Pillar data to file
    write_pillar_data_to_file(
        nom_data, f'{DATA_STORE_DIR}/pillar_data.json')


async def main():
    while True:
        print(f'{str(datetime.datetime.now())}: Starting')
        await update()
        print(f'{str(datetime.datetime.now())}: Completed')
        time.sleep(10)


if __name__ == '__main__':
    asyncio.run(main())
