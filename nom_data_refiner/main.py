import json
import time
import os
import asyncio
import math
import datetime
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
        'yearlyZnnMomentumRewardPoolForPillarsTop30': data.yearly_znn_momentum_reward_pool_for_pillars_top_30,
        'yearlyZnnMomentumRewardPoolForPillarsNotTop30': data.yearly_znn_momentum_reward_pool_for_pillars_not_top_30,
        'yearlyZnnDelegateRewardPoolForPillars': data.yearly_znn_delegate_reward_pool_for_pillars,
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


async def main():

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
    if not os.path.exists(f'./{DATA_STORE_DIR}/market_cache.json'):
        write_to_file_as_json(
            {'timestamp': math.trunc(time.time()), 'znn_price_usd': 50, 'qsr_price_usd': 5}, f'{DATA_STORE_DIR}/market_cache.json')

    # Get coin prices. Set QSR price as 1/10th of ZNN until a market is open.
    market = MarketWrapper()
    znn_price = await market.get_price_usd(coin='zenon')
    qsr_price = znn_price / 10

    # If bad response use cached price data, else cache the new data.
    if znn_price == 0:
        market_cache = read_file(
            f'{DATA_STORE_DIR}/market_cache.json')
        znn_price = market_cache['znn_price_usd']
        qsr_price = market_cache['qsr_price_usd']
    else:
        write_to_file_as_json({'timestamp': math.trunc(time.time()), 'znn_price_usd': znn_price, 'qsr_price_usd': qsr_price},
                              f'{DATA_STORE_DIR}/market_cache.json')

    # Update NoM data
    nom_data = NomData()
    await nom_data.update(node_url=cfg['node_url_http'],
                          reference_staking_address=cfg['reference_staking_address'],
                          znn_price_usd=znn_price,
                          qsr_price_usd=qsr_price)

    # Write NoM data to file
    write_nom_data_to_file(
        nom_data, f'{DATA_STORE_DIR}/nom_data.json')

    # Write Pillar data to file
    write_pillar_data_to_file(
        nom_data, f'{DATA_STORE_DIR}/pillar_data.json')

if __name__ == '__main__':
    print(f'{str(datetime.datetime.now())}: Starting')
    asyncio.run(main())
    print(f'{str(datetime.datetime.now())}: Completed')
