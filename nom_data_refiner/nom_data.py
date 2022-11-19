import asyncio
import datetime
import math
from utils.http_wrapper import HttpWrapper


class NomPillar(object):
    def __init__(self,
                 name,
                 rank,
                 type,
                 owner_address,
                 producer_address,
                 withdraw_address,
                 is_revocable,
                 revoke_cooldown,
                 revoke_timestamp,
                 give_momentum_reward_percentage,
                 give_delegate_reward_percentage,
                 produced_momentums,
                 expected_momentums,
                 weight,
                 epoch_momentum_rewards,
                 epoch_delegate_rewards,
                 apr,
                 delegate_apr):
        self.name = name
        self.rank = rank
        self.type = type
        self.owner_address = owner_address
        self.producer_address = producer_address
        self.withdraw_address = withdraw_address
        self.is_revocable = is_revocable
        self.revoke_cooldown = revoke_cooldown
        self.revoke_timestamp = revoke_timestamp
        self.give_momentum_reward_percentage = give_momentum_reward_percentage
        self.give_delegate_reward_percentage = give_delegate_reward_percentage
        self.produced_momentums = produced_momentums
        self.expected_momentums = expected_momentums
        self.weight = weight
        self.epoch_momentum_rewards = epoch_momentum_rewards
        self.epoch_delegate_rewards = epoch_delegate_rewards
        self.apr = apr
        self.delegate_apr = delegate_apr


class NomData(object):

    # Constants
    DAYS_PER_MONTH = 30
    HOURS_PER_MONTH = 24 * 30
    MONTHS_PER_YEAR = 12
    DAYS_PER_YEAR = 12 * 30
    EPOCH_LENGTH_IN_DAYS = 1
    QSR_REWARD_SHARE_FOR_STAKERS = 0.5
    QSR_REWARD_SHARE_FOR_SENTINELS = 0.25
    ZNN_REWARD_SHARE_FOR_SENTINELS = 0.13
    QSR_REWARD_SHARE_FOR_LPS = 0.25
    ZNN_REWARD_SHARE_FOR_LPS = 0.13
    ZNN_REWARD_SHARE_FOR_PILLAR_DELEGATES = 0.24
    ZNN_REWARD_SHARE_FOR_PILLAR_MOMENTUMS = 0.5
    SENTINEL_COLLATERAL_ZNN = 5000
    SENTINEL_COLLATERAL_QSR = 50000
    PILLAR_COLLATERAL_ZNN = 15000
    PILLAR_COLLATERAL_QSR = 150000
    DECIMALS = 100000000
    MOMENTUMS_PER_HOUR = 360
    ZNN_ZTS_ID = 'zts1znnxxxxxxxxxxxxx9z4ulx'
    QSR_ZTS_ID = 'zts1qsrxxxxxxxxxxxxxmrhjll'
    TOTAL_MOMENTUMS_PER_DAY = 8640
    STAKING_CONTRACT_ADDRESS = 'z1qxemdeddedxstakexxxxxxxxxxxxxxxxjv8v62'

    # Daily reward emissions
    DAILY_ZNN_REWARDS_BY_MONTH = [
        14400, 8640, 7200, 10080, 7200, 5760, 10080, 5760, 4320, 10080, 4320, 4320
    ]
    DAILY_QSR_REWARDS_BY_MONTH = [
        20000, 20000, 20000, 20000, 15000, 15000, 15000, 5000, 5000, 5000, 5000,
        5000
    ]

    # Pancakeswap pool data
    pcs_pool = None

    # A reference staking address is used to calculate the network's total weighted stake.
    # It's assumed that the reference address is staking with a lockup period of 12 months.
    reference_staking_address = ''
    reference_staking_reward_previous_epoch = 0
    reference_staking_amount = 0
    reference_weighted_staking_amount = 0
    avg_staking_lockup_time_in_days = 0

    reference_lp_address = ''
    lp_program_participation_rate = 0

    momentum_height = 0
    node_version = ''
    momentum_month = 0

    total_expected_daily_momentums_top_30 = 0
    total_expected_daily_momentums_not_top_30 = 0

    total_staked_znn = {
        'amount': 0,
        'weighted_amount': 0
    }
    total_delegated_znn = 0
    total_delegated_znn_top_30 = 0
    total_delegated_znn_not_top_30 = 0
    sentinel_count = 0
    pillar_count = 0

    sentinel_value_usd = 0
    pillar_value_usd = 0

    znn_supply = 0
    qsr_supply = 0

    staking_apr = 0
    delegate_apr = 0
    lp_apr = 0
    sentinel_apr = 0
    pillar_apr_top_30 = 0
    pillar_apr_not_top_30 = 0

    avg_pillars_momentum_reward_share_top_30 = 0
    avg_pillars_momentum_reward_share_not_top_30 = 0
    avg_pillars_delegate_reward_share_top_30 = 0
    avg_pillars_delegate_reward_share_not_top_30 = 0

    pillar_data_cache = {}
    pillars = []

    yearly_znn_reward_pool_for_lps = 0
    yearly_znn_reward_pool_for_sentinels = 0
    yearly_znn_momentum_reward_pool_for_pillars_top_30 = 0
    yearly_znn_momentum_reward_pool_for_pillars_not_top_30 = 0
    yearly_znn_delegate_reward_pool_for_pillars = 0

    yearly_qsr_reward_pool_for_stakers = 0
    yearly_qsr_reward_pool_for_lps = 0
    yearly_qsr_reward_pool_for_sentinels = 0
    yearly_qsr_reward_pool_for_lp_program = 0

    yearly_usd_reward_pool_for_lp_program = 0
    daily_qsr_reward_pool_for_lp_program = 0

    async def update(self, node_url, reference_staking_address, reference_lp_address, znn_price_usd, qsr_price_usd, pcs_pool):
        self.node_url = node_url
        self.znn_price_usd = znn_price_usd
        self.qsr_price_usd = qsr_price_usd
        self.reference_staking_address = reference_staking_address
        self.reference_lp_address = reference_lp_address
        self.pcs_pool = pcs_pool

        # Update data from the node
        await asyncio.gather(
            self.__update_height(),
            self.__update_node_version(),
            self.__update_znn_supply(),
            self.__update_qsr_supply(),
            self.__update_total_staked_znn(),
            self.__update_reference_staking_data(),
            self.__update_sentinel_data(),
            self.__update_pillar_data())

        # Update expected momentums for top 30 Pillars and for non top 30 Pillars
        self.__update_total_expected_momentums_for_pillars()

        # Update the yearly reward pools based on current reward emissions rate
        self.__update_current_yearly_reward_pools()

        # Update staking data
        self.__update_staking_data()

        # Update LP program participation rate
        await self.__update_lp_program_participation_rate()

        # Update APRs (LP not implemented yet)
        self.__update_staking_apr()
        self.__update_lp_apr()
        self.__update_sentinel_apr()
        self.__update_pillar_apr_top_30()
        self.__update_pillar_apr_not_top_30()

        # Update the Pillar stats
        self.__update_pillars()

        # Update delegate APR after Pillars have been updated
        self.__update_delegate_apr()

    def __create_request(self, method, params=[]):
        return {'jsonrpc': '2.0', 'id': 1,
                'method': method, 'params': params}

    def __get_current_yearly_znn_rewards(self):
        month = self.__get_current_epoch_month()
        month = month if month < 12 else 11
        return self.DAILY_ZNN_REWARDS_BY_MONTH[month] * self.DAYS_PER_MONTH * self.MONTHS_PER_YEAR

    def __get_current_yearly_qsr_rewards(self):
        month = self.__get_current_epoch_month()
        month = month if month < 12 else 11
        return self.DAILY_QSR_REWARDS_BY_MONTH[month] * self.DAYS_PER_MONTH * self.MONTHS_PER_YEAR

    def __get_current_epoch_month(self):
        genesis = datetime.datetime(
            year=2021, month=11, day=24, hour=12, tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        epoch = (now - genesis).days
        for i in range(0, 1000):
            if epoch < self.DAYS_PER_MONTH * (i + 1):
                return i
        return 0

    def __get_pillar_count_top_30(self):
        return 30 if self.pillar_count >= 30 else self.pillar_count

    def __get_pillar_count_not_top_30(self):
        return 0 if self.pillar_count < 30 else self.pillar_count - 30

    async def __update_height(self):
        r = await HttpWrapper.post(self.node_url, self.__create_request('ledger.getFrontierMomentum'))
        try:
            self.momentum_height = r['result']['height']
        except KeyError:
            print('Error: __update_height')

    async def __update_node_version(self):
        r = await HttpWrapper.post(self.node_url, self.__create_request('stats.processInfo'))
        try:
            self.node_version = r['result']['version']
        except KeyError:
            print('Error: __update_node_version')

    async def __update_znn_supply(self):
        r = await HttpWrapper.post(self.node_url, self.__create_request('embedded.token.getByZts', [
            self.ZNN_ZTS_ID
        ]))
        try:
            self.znn_supply = r['result']['totalSupply']
        except KeyError:
            print('Error: __update_znn_supply')

    async def __update_qsr_supply(self):
        r = await HttpWrapper.post(self.node_url, self.__create_request('embedded.token.getByZts', [
            self.QSR_ZTS_ID
        ]))
        try:
            self.qsr_supply = r['result']['totalSupply']
        except KeyError:
            print('Error: __update_qsr_supply')

    async def __update_total_staked_znn(self):
        r = await HttpWrapper.post(self.node_url, self.__create_request('ledger.getAccountInfoByAddress', [
            self.STAKING_CONTRACT_ADDRESS
        ]))
        try:
            self.total_staked_znn['amount'] = r['result']['balanceInfoMap'][self.ZNN_ZTS_ID]['balance'] / self.DECIMALS
        except KeyError:
            print('Error: __update_total_staked_znn')

    async def __update_reference_staking_data(self):
        if len(self.reference_staking_address) == 0:
            return

        r = await HttpWrapper.post(self.node_url, self.__create_request('embedded.stake.getFrontierRewardByPage', [
            self.reference_staking_address, 0, 1
        ]))
        try:
            if r['result']['count'] > 0:
                self.reference_staking_reward_previous_epoch = r[
                    'result']['list'][0]['qsrAmount'] / self.DECIMALS
        except KeyError:
            print('Error: __update_reference_staking_data')

        r = await HttpWrapper.post(self.node_url, self.__create_request('embedded.stake.getEntriesByAddress', [
            self.reference_staking_address, 0, 1
        ]))
        try:
            if r['result']['count'] > 0:
                self.reference_staking_amount = r['result']['list'][0]['amount'] / self.DECIMALS
                self.reference_weighted_staking_amount = r['result'][
                    'list'][0]['weightedAmount'] / self.DECIMALS
        except KeyError:
            print('Error: __update_reference_staking_data')

    async def __update_sentinel_data(self):
        r = await HttpWrapper.post(self.node_url, self.__create_request('embedded.sentinel.getAllActive', [0, 1000]))
        try:
            # Update sentinel count and value
            self.sentinel_count = r['result']['count']
            self.sentinel_value_usd = self.SENTINEL_COLLATERAL_ZNN * \
                self.znn_price_usd + self.SENTINEL_COLLATERAL_QSR * self.qsr_price_usd
        except KeyError:
            print('Error: __update_sentinel_data')

    async def __update_pillar_data(self):
        r = await HttpWrapper.post(self.node_url, self.__create_request('embedded.pillar.getAll', [0, 1000]))
        try:
            # Update Pillar data cache for later use
            self.pillar_data_cache = r

            # Update Pillar count and value
            self.pillar_count = r['result']['count']
            self.pillar_value_usd = self.PILLAR_COLLATERAL_ZNN * \
                self.znn_price_usd + self.PILLAR_COLLATERAL_QSR * self.qsr_price_usd

            # Reset variables
            self.total_delegated_znn = 0
            self.total_delegated_znn_top_30 = 0
            self.total_delegated_znn_not_top_30 = 0
            self.avg_pillars_momentum_reward_share_top_30 = 0
            self.avg_pillars_momentum_reward_share_not_top_30 = 0
            self.avg_pillars_delegate_reward_share_top_30 = 0
            self.avg_pillars_delegate_reward_share_not_top_30 = 0
            self.pillars = []

            total_momentum_reward_share_top_30 = 0
            total_momentum_reward_share_not_top_30 = 0
            total_delegate_reward_share_top_30 = 0
            total_delegate_reward_share_not_top_30 = 0

            # Loop through the Pillars
            for p_data in r['result']['list']:

                # Add to total delegated
                self.total_delegated_znn = self.total_delegated_znn + \
                    p_data['weight'] / self.DECIMALS
                if p_data['rank'] < 30:
                    self.total_delegated_znn_top_30 = self.total_delegated_znn_top_30 + \
                        p_data['weight'] / self.DECIMALS
                else:
                    self.total_delegated_znn_not_top_30 = self.total_delegated_znn_not_top_30 + \
                        p_data['weight'] / self.DECIMALS

                # Add to total reward share rates (used to calculate averages)
                if p_data['rank'] < 30:
                    total_momentum_reward_share_top_30 = total_momentum_reward_share_top_30 + \
                        p_data['giveMomentumRewardPercentage'] / 100
                    total_delegate_reward_share_top_30 = total_delegate_reward_share_top_30 + \
                        p_data['giveDelegateRewardPercentage'] / 100
                else:
                    total_momentum_reward_share_not_top_30 = total_momentum_reward_share_not_top_30 + \
                        p_data['giveMomentumRewardPercentage'] / 100
                    total_delegate_reward_share_not_top_30 = total_delegate_reward_share_not_top_30 + \
                        p_data['giveDelegateRewardPercentage'] / 100

            # Update avg momentum and delegate reward sharing rates for top 30
            pillar_count_top_30 = self.__get_pillar_count_top_30()
            if pillar_count_top_30 > 0:
                self.avg_pillars_momentum_reward_share_top_30 = total_momentum_reward_share_top_30 / \
                    pillar_count_top_30
                self.avg_pillars_delegate_reward_share_top_30 = total_delegate_reward_share_top_30 / \
                    pillar_count_top_30
            else:
                self.avg_pillars_momentum_reward_share_top_30 = 0
                self.avg_pillars_delegate_reward_share_top_30 = 0

            # Update avg momentum and delegate reward sharing rates for not top 30
            pillar_count_not_top_30 = self.__get_pillar_count_not_top_30()
            if pillar_count_not_top_30 > 0:
                self.avg_pillars_momentum_reward_share_not_top_30 = total_momentum_reward_share_not_top_30 / \
                    pillar_count_not_top_30
                self.avg_pillars_delegate_reward_share_not_top_30 = total_delegate_reward_share_not_top_30 / \
                    pillar_count_not_top_30
            else:
                self.avg_pillars_momentum_reward_share_not_top_30 = 0
                self.avg_pillars_delegate_reward_share_not_top_30 = 0

        except KeyError:
            print('Error: __update_pillar_data')

    def __update_staking_data(self):
        # Calculations based on https://github.com/zenon-network/go-zenon/blob/1baa7c4e057da4f2708a970b4fedf70a8de77fbe/vm/embedded/implementation/stake.go

        rewards_per_epoch = (self.__get_current_yearly_qsr_rewards(
        ) * self.QSR_REWARD_SHARE_FOR_STAKERS) / (self.DAYS_PER_YEAR * self.EPOCH_LENGTH_IN_DAYS)

        # If no reference staking address is provided use a guesstimation to calculate total weighted stake.
        if len(self.reference_staking_address) == 0 or self.reference_staking_reward_previous_epoch == 0:
            estimated_avg_staking_lockup_time_in_months = 3
            self.total_staked_znn['weighted_amount'] = (
                (9 + estimated_avg_staking_lockup_time_in_months) * self.total_staked_znn['amount']) / 10

            self.avg_staking_lockup_time_in_days = estimated_avg_staking_lockup_time_in_months * \
                self.DAYS_PER_MONTH

        else:
            self.total_staked_znn['weighted_amount'] = (
                rewards_per_epoch * self.reference_weighted_staking_amount) / self.reference_staking_reward_previous_epoch

            self.avg_staking_lockup_time_in_days = round(
                (((self.total_staked_znn['weighted_amount'] * 10) / self.total_staked_znn['amount']) - 9) * self.DAYS_PER_MONTH)

    def __update_total_expected_momentums_for_pillars(self):
        # Group B size (includes half of the top 30 pillars and all non top 30 pillars)
        group_b_size = self.pillar_count - 15

        # Momentum allocations for group A (15 Pillars from top 30) and group B (all the remaining Pillars not in group A)
        momentums_allocated_for_group_a = self.TOTAL_MOMENTUMS_PER_DAY * 0.5
        momentums_allocated_for_group_b = self.TOTAL_MOMENTUMS_PER_DAY * 0.5

        self.total_expected_daily_momentums_top_30 = momentums_allocated_for_group_a + \
            momentums_allocated_for_group_b * (15 / group_b_size)
        self.total_expected_daily_momentums_not_top_30 = momentums_allocated_for_group_b * \
            ((group_b_size - 15) / group_b_size)

    def __update_current_yearly_reward_pools(self):
        total_yearly_znn_rewards = self.__get_current_yearly_znn_rewards()
        total_yearly_qsr_rewards = self.__get_current_yearly_qsr_rewards()

        self.yearly_znn_reward_pool_for_lps = total_yearly_znn_rewards * \
            self.ZNN_REWARD_SHARE_FOR_LPS
        self.yearly_znn_reward_pool_for_sentinels = total_yearly_znn_rewards * \
            self.ZNN_REWARD_SHARE_FOR_SENTINELS

        self.yearly_znn_momentum_reward_pool_for_pillars_top_30 = self.__get_yearly_momentum_rewards_top_30()
        self.yearly_znn_momentum_reward_pool_for_pillars_not_top_30 = self.__get_yearly_momentum_rewards_not_top_30()
        self.yearly_znn_delegate_reward_pool_for_pillars = total_yearly_znn_rewards * \
            self.ZNN_REWARD_SHARE_FOR_PILLAR_DELEGATES

        self.yearly_qsr_reward_pool_for_stakers = total_yearly_qsr_rewards * \
            self.QSR_REWARD_SHARE_FOR_STAKERS
        self.yearly_qsr_reward_pool_for_lps = total_yearly_qsr_rewards * \
            self.QSR_REWARD_SHARE_FOR_LPS
        self.yearly_qsr_reward_pool_for_sentinels = total_yearly_qsr_rewards * \
            self.QSR_REWARD_SHARE_FOR_SENTINELS

        # LP reward program
        reward_multiplier = 1
        if self.pcs_pool.wbnb_reserve >= 3000 and self.pcs_pool.wbnb_reserve < 4500:
            reward_multiplier = 3
        elif self.pcs_pool.wbnb_reserve >= 2000 and self.pcs_pool.wbnb_reserve < 10000:
            reward_multiplier = math.floor(self.pcs_pool.wbnb_reserve / 1000)
        elif self.pcs_pool.wbnb_reserve >= 10000:
            reward_multiplier = 10

        self.daily_qsr_reward_pool_for_lp_program = reward_multiplier * 1800

        self.yearly_usd_reward_pool_for_lp_program = self.daily_qsr_reward_pool_for_lp_program * self.qsr_price_usd * self.DAYS_PER_YEAR
        self.yearly_qsr_reward_pool_for_lp_program = self.daily_qsr_reward_pool_for_lp_program * self.DAYS_PER_YEAR


    async def __update_lp_program_participation_rate(self):
        lp_program_address = 'z1qqw8f3qxx9zg92xgckqdpfws3dw07d26afsj74'
        qsr_standard = 'zts1qsrxxxxxxxxxxxxxmrhjll'
        reward = 0
        r = await HttpWrapper.post(self.node_url, self.__create_request('ledger.getUnreceivedBlocksByAddress', [self.reference_lp_address, 0, 1]))
        if len(r['result']['list']) > 0 and r['result']['list'][0]['tokenStandard'] == qsr_standard and r['result']['list'][0]['address'] == lp_program_address:
            reward = r['result']['list'][0]['amount'] / self.DECIMALS

        if reward == 0:
            r = await HttpWrapper.post(self.node_url, self.__create_request('ledger.getAccountBlocksByPage', [self.reference_lp_address, 0, 10]))
            if len(r['result']['list']) > 0:
                for block in r['result']['list']:
                    if (len(block['pairedAccountBlock']) > 0) and block['pairedAccountBlock']['tokenStandard'] == qsr_standard and block['pairedAccountBlock']['address'] == lp_program_address:
                        reward = block['pairedAccountBlock']['amount'] / self.DECIMALS
                        break            
        
        reward_share = reward / self.daily_qsr_reward_pool_for_lp_program

        self.lp_program_participation_rate = self.pcs_pool.reference_address_reward_share / reward_share if reward_share > 0 else 1
        print('LP participation rate: ' + str(self.lp_program_participation_rate))

    def __update_staking_apr(self):
        reward_pool_in_usd = self.yearly_qsr_reward_pool_for_stakers * self.qsr_price_usd
        total_staked_value_in_usd = self.total_staked_znn['amount'] * \
            self.znn_price_usd
        self.staking_apr = reward_pool_in_usd / total_staked_value_in_usd * \
            100 if total_staked_value_in_usd > 0 else 0

    def __update_delegate_apr(self):
        total_apr = 0
        sharing_pillars_count = 0
        for pillar in self.pillars:
            # Only include Pillars that have over 0% delegate APR and a weight of at least 10k ZNN
            if pillar.delegate_apr > 0 and pillar.weight / self.DECIMALS >= 10000:
                total_apr = total_apr + pillar.delegate_apr
                sharing_pillars_count = sharing_pillars_count + 1
        self.delegate_apr = total_apr / \
            sharing_pillars_count if sharing_pillars_count > 0 else 0

    def __update_lp_apr(self):
        # total_rewards_usd = self.yearly_znn_reward_pool_for_lps * self.znn_price_usd + \
        #     self.yearly_qsr_reward_pool_for_lps * self.qsr_price_usd
        # total_rewards_usd = total_rewards_usd + self.pcs_pool.yearly_trading_fees_usd

        if self.pcs_pool.liquidity_usd > 0:
            self.lp_apr = (self.yearly_usd_reward_pool_for_lp_program + self.pcs_pool.yearly_trading_fees_usd * self.lp_program_participation_rate) / \
                (self.pcs_pool.liquidity_usd * self.lp_program_participation_rate) * 100
        else:
            self.lp_apr = 0

    def __update_sentinel_apr(self):
        total_rewards_usd = self.yearly_znn_reward_pool_for_sentinels * self.znn_price_usd + \
            self.yearly_qsr_reward_pool_for_sentinels * self.qsr_price_usd
        if self.sentinel_count > 0 and self.sentinel_value_usd > 0:
            self.sentinel_apr = total_rewards_usd / \
                self.sentinel_count / self.sentinel_value_usd * 100
        else:
            self.sentinel_apr = 0

    def __update_pillar_apr_top_30(self):
        # Calculate average yearly momentum rewards per Pillar
        yearly_momentum_rewards = self.__get_yearly_momentum_rewards_top_30()
        yearly_momentum_rewards = yearly_momentum_rewards * \
            (1 - self.avg_pillars_momentum_reward_share_top_30)

        # Calculate yearly delegate rewards
        total_yearly_delegate_rewards = self.__get_current_yearly_znn_rewards() * \
            self.ZNN_REWARD_SHARE_FOR_PILLAR_DELEGATES
        delegate_rewards_share = self.total_delegated_znn_top_30 / self.total_delegated_znn
        yearly_delegate_rewards = total_yearly_delegate_rewards * delegate_rewards_share
        yearly_delegate_rewards = yearly_delegate_rewards * \
            (1 - self.avg_pillars_delegate_reward_share_top_30)

        # Calculate APR
        pillar_count_top_30 = self.__get_pillar_count_top_30()
        total_rewards_usd = yearly_momentum_rewards * self.znn_price_usd + \
            yearly_delegate_rewards * self.znn_price_usd
        if pillar_count_top_30 > 0 and self.pillar_value_usd > 0:
            self.pillar_apr_top_30 = total_rewards_usd / \
                pillar_count_top_30 / self.pillar_value_usd * 100
        else:
            self.pillar_apr_top_30 = 0

    def __update_pillar_apr_not_top_30(self):
        # Calculate average yearly momentum rewards per Pillar
        yearly_momentum_rewards = self.__get_yearly_momentum_rewards_not_top_30()
        yearly_momentum_rewards = yearly_momentum_rewards * \
            (1 - self.avg_pillars_momentum_reward_share_not_top_30)

        # Calculate yearly delegate rewards
        total_yearly_delegate_rewards = self.__get_current_yearly_znn_rewards() * \
            self.ZNN_REWARD_SHARE_FOR_PILLAR_DELEGATES
        delegate_rewards_share = self.total_delegated_znn_not_top_30 / \
            self.total_delegated_znn
        yearly_delegate_rewards = total_yearly_delegate_rewards * delegate_rewards_share
        yearly_delegate_rewards = yearly_delegate_rewards * \
            (1 - self.avg_pillars_delegate_reward_share_not_top_30)

        # Calculate APR
        pillar_count_not_top_30 = self.__get_pillar_count_not_top_30()
        total_rewards_usd = yearly_momentum_rewards * self.znn_price_usd + \
            yearly_delegate_rewards * self.znn_price_usd
        if pillar_count_not_top_30 > 0 and self.pillar_value_usd > 0:
            self.pillar_apr_not_top_30 = total_rewards_usd / \
                pillar_count_not_top_30 / self.pillar_value_usd * 100
        else:
            self.pillar_apr_not_top_30 = 0

    def __update_pillars(self):
        self.pillars = []

        # Loop through the Pillars
        for p_data in self.pillar_data_cache['result']['list']:
            pillar_count_top_30 = self.__get_pillar_count_top_30()
            pillar_count_not_top_30 = self.__get_pillar_count_not_top_30()

            produced = p_data['currentStats']['producedMomentums']
            expected = p_data['currentStats']['expectedMomentums']

            # Use a reward multiplier based on produced / expected momentums. Allow a tolerance of 2 momentums.
            # TODO: Some better implementation could be used.
            if expected - produced > 2 and expected > 0:
                momentum_reward_multiplier = produced / expected
            else:
                momentum_reward_multiplier = 1

            # Calculate yearly momentum rewards for Pillar based on currently produced momentums
            if p_data['rank'] < 30 and pillar_count_top_30 > 0:

                # Calculate the daily expected momentums for a top 30 Pillar
                daily_expected_momentums_per_pillar = self.total_expected_daily_momentums_top_30 / \
                    pillar_count_top_30

                # Calculate the Pillar's yearly momentum rewards based on current stats
                yearly_momentum_rewards = self.__get_yearly_momentum_rewards_top_30(
                ) * ((daily_expected_momentums_per_pillar * momentum_reward_multiplier) / self.total_expected_daily_momentums_top_30)

            # Same for not top 30 Pillars
            elif pillar_count_not_top_30 > 0:

                # Calculate the daily expected momentums for a non top 30 Pillar
                daily_expected_momentums_per_pillar = self.total_expected_daily_momentums_not_top_30 / \
                    pillar_count_not_top_30

                # Calculate the Pillar's yearly momentum rewards based on current stats
                yearly_momentum_rewards = self.__get_yearly_momentum_rewards_not_top_30(
                ) * ((daily_expected_momentums_per_pillar * momentum_reward_multiplier) / self.total_expected_daily_momentums_not_top_30)

            else:
                yearly_momentum_rewards = 0

            # Calculate yearly delegate rewards for Pillar based on current weight
            if self.total_delegated_znn > 0:
                yearly_delegate_rewards = (
                    p_data['weight'] / self.DECIMALS / self.total_delegated_znn) * self.__get_current_yearly_znn_rewards() * self.ZNN_REWARD_SHARE_FOR_PILLAR_DELEGATES
            else:
                yearly_delegate_rewards = 0

            # Get Pillar stats
            momentum_reward_sharing = p_data['giveMomentumRewardPercentage'] / 100
            delegate_reward_sharing = p_data['giveDelegateRewardPercentage'] / 100
            delegated_znn = p_data['weight'] / self.DECIMALS

            # Calculate the Pillar's APR
            p_apr = self.__get_single_pillar_apr(
                yearly_momentum_rewards, yearly_delegate_rewards, momentum_reward_sharing, delegate_reward_sharing)

            # Calculate the Pillar's delegate APR
            d_apr = self.__get_single_pillar_delegate_apr(
                yearly_momentum_rewards, yearly_delegate_rewards, momentum_reward_sharing, delegate_reward_sharing, delegated_znn)

            # Get rewards for current epoch
            epoch_momentum_rewards = yearly_momentum_rewards / \
                self.DAYS_PER_YEAR * self.EPOCH_LENGTH_IN_DAYS
            epoch_delegate_rewards = yearly_delegate_rewards / \
                self.DAYS_PER_YEAR * self.EPOCH_LENGTH_IN_DAYS

            # Create Pillar object
            self.pillars.append(
                NomPillar(
                    p_data['name'],
                    p_data['rank'],
                    p_data['type'],
                    p_data['ownerAddress'],
                    p_data['producerAddress'],
                    p_data['withdrawAddress'],
                    p_data['isRevocable'],
                    p_data['revokeCooldown'],
                    p_data['revokeTimestamp'],
                    p_data['giveMomentumRewardPercentage'],
                    p_data['giveDelegateRewardPercentage'],
                    p_data['currentStats']['producedMomentums'],
                    p_data['currentStats']['expectedMomentums'],
                    p_data['weight'],
                    epoch_momentum_rewards,
                    epoch_delegate_rewards,
                    p_apr * 100,
                    d_apr * 100))

    def __get_single_pillar_apr(self, yearly_momentum_rewards, yearly_delegate_rewards, momentum_reward_sharing, delegate_reward_sharing):
        rewards_value_usd = yearly_momentum_rewards * \
            (1 - momentum_reward_sharing) * self.znn_price_usd + \
            yearly_delegate_rewards * \
            (1 - delegate_reward_sharing) * self.znn_price_usd
        return rewards_value_usd / self.pillar_value_usd if self.pillar_value_usd > 0 else 0

    def __get_single_pillar_delegate_apr(self, yearly_momentum_rewards, yearly_delegate_rewards, momentum_reward_sharing, delegate_reward_sharing, delegated_znn):
        rewards_value_znn = yearly_momentum_rewards * momentum_reward_sharing + \
            yearly_delegate_rewards * delegate_reward_sharing
        return rewards_value_znn / delegated_znn if delegated_znn > 0 else 0

    def __get_yearly_momentum_rewards_top_30(self):
        total_yearly_momentum_rewards = self.__get_current_yearly_znn_rewards() * \
            self.ZNN_REWARD_SHARE_FOR_PILLAR_MOMENTUMS
        momentum_rewards_share = self.total_expected_daily_momentums_top_30 / \
            self.TOTAL_MOMENTUMS_PER_DAY
        return total_yearly_momentum_rewards * momentum_rewards_share

    def __get_yearly_momentum_rewards_not_top_30(self):
        total_yearly_momentum_rewards = self.__get_current_yearly_znn_rewards() * \
            self.ZNN_REWARD_SHARE_FOR_PILLAR_MOMENTUMS
        momentum_rewards_share = self.total_expected_daily_momentums_not_top_30 / \
            self.TOTAL_MOMENTUMS_PER_DAY
        return total_yearly_momentum_rewards * momentum_rewards_share
