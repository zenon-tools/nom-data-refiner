import asyncio
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
        self.apr = apr
        self.delegate_apr = delegate_apr


class NomData(object):

    # Constants
    DAYS_PER_MONTH = 30
    HOURS_PER_MONTH = 24 * 30
    MONTHS_PER_YEAR = 12
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

    # Daily reward emissions
    DAILY_ZNN_REWARDS_BY_MONTH = [
        14400, 8640, 7200, 10080, 7200, 5760, 10080, 5760, 4320, 10080, 4320, 4320
    ]
    DAILY_QSR_REWARDS_BY_MONTH = [
        20000, 20000, 20000, 20000, 15000, 15000, 15000, 5000, 5000, 5000, 5000,
        5000
    ]

    momentum_height = 0
    node_version = ''
    momentum_month = 0

    # Total staked amount will have to be indexed separately
    total_staked_znn = {
        'momentum_height': 0,
        'amount': 0
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

    pillars_produced_momentums_top_30 = 0
    pillars_produced_momentums_not_top_30 = 0

    avg_pillars_momentum_reward_share_top_30 = 0
    avg_pillars_momentum_reward_share_not_top_30 = 0
    avg_pillars_delegate_reward_share_top_30 = 0
    avg_pillars_delegate_reward_share_not_top_30 = 0

    pillar_data_cache = {}
    pillars = []

    async def update(self, node_url, znn_price_usd, qsr_price_usd):
        self.node_url = node_url
        self.znn_price_usd = znn_price_usd
        self.qsr_price_usd = qsr_price_usd

        # Update data from the node
        await asyncio.gather(
            self.__update_height(),
            self.__update_node_version(),
            self.__update_znn_supply(),
            self.__update_qsr_supply(),
            self.__update_sentinel_data(),
            self.__update_pillar_data())

        # Update APRs (LP and staking not implemented yet)
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
        month = self.__get_momentum_month(self.momentum_height)
        return self.DAILY_ZNN_REWARDS_BY_MONTH[month] * self.DAYS_PER_MONTH * self.MONTHS_PER_YEAR

    def __get_current_yearly_qsr_rewards(self):
        month = self.__get_momentum_month(self.momentum_height)
        return self.DAILY_QSR_REWARDS_BY_MONTH[month] * self.DAYS_PER_MONTH * self.MONTHS_PER_YEAR

    def __get_momentum_month(self, height):
        momentums_per_month = self.HOURS_PER_MONTH * self.MOMENTUMS_PER_HOUR
        for i in range(0, 12):
            if height < momentums_per_month * (i + 1):
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
            self.pillars_produced_momentums_top_30 = 0
            self.pillars_produced_momentums_not_top_30 = 0
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

                # Add to total produced momentums
                if p_data['rank'] < 30:
                    self.pillars_produced_momentums_top_30 = self.pillars_produced_momentums_top_30 + \
                        p_data['currentStats']['producedMomentums']
                else:
                    self.pillars_produced_momentums_not_top_30 = self.pillars_produced_momentums_not_top_30 + \
                        p_data['currentStats']['producedMomentums']

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

    def __update_delegate_apr(self):
        total_apr = 0
        sharing_pillars_count = 0
        for pillar in self.pillars:
            # Only include Pillars that have over 0% delegate APR
            if pillar.delegate_apr > 0:
                total_apr = total_apr + pillar.apr
                sharing_pillars_count = sharing_pillars_count + 1
        self.delegate_apr = total_apr / \
            sharing_pillars_count if sharing_pillars_count > 0 else 0

    def __update_sentinel_apr(self):
        yearly_znn_rewards = self.__get_current_yearly_znn_rewards() * \
            self.ZNN_REWARD_SHARE_FOR_SENTINELS
        yearly_qsr_rewards = self.__get_current_yearly_qsr_rewards() * \
            self.QSR_REWARD_SHARE_FOR_SENTINELS
        total_rewards_usd = yearly_znn_rewards * self.znn_price_usd + \
            yearly_qsr_rewards * self.qsr_price_usd
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

            # Calculate yearly momentum rewards for Pillar based on currently produced momentums
            if p_data['rank'] < 30 and pillar_count_top_30 > 0:

                # Use a reward multiplier based on produced / expected momentums
                momentum_reward_multiplier = p_data['currentStats']['producedMomentums'] / \
                    p_data['currentStats']['expectedMomentums']

                # Assume the expected momentums even out for all Pillars -> use a produced momentums average
                avg_produced_momentums = self.pillars_produced_momentums_top_30 / pillar_count_top_30

                # Calculate the Pillar's yearly momentum rewards based on current stats
                yearly_momentum_rewards = self.__get_yearly_momentum_rewards_top_30(
                ) * ((avg_produced_momentums * momentum_reward_multiplier) / self.pillars_produced_momentums_top_30)

            # Same for not top 30 Pillars
            elif pillar_count_not_top_30 > 0:

                # Use a reward multiplier based on produced / expected momentums
                # TODO: Needs a better implementation as the multiplier will effect the rewards too much at the start of an epoch
                momentum_reward_multiplier = p_data['currentStats']['producedMomentums'] / \
                    p_data['currentStats']['expectedMomentums'] if p_data['currentStats']['expectedMomentums'] > 0 else 0

                # Assume the expected momentums even out for all Pillars -> use a produced momentums average
                avg_produced_momentums = self.pillars_produced_momentums_not_top_30 / \
                    pillar_count_not_top_30

                # Calculate the Pillar's yearly momentum rewards based on current stats
                yearly_momentum_rewards = self.__get_yearly_momentum_rewards_not_top_30(
                ) * ((avg_produced_momentums * momentum_reward_multiplier) / self.pillars_produced_momentums_not_top_30)

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
        total_momentums_produced = self.pillars_produced_momentums_top_30 + \
            self.pillars_produced_momentums_not_top_30
        momentum_rewards_share = self.pillars_produced_momentums_top_30 / \
            total_momentums_produced if total_momentums_produced > 0 else 0
        return total_yearly_momentum_rewards * momentum_rewards_share

    def __get_yearly_momentum_rewards_not_top_30(self):
        total_yearly_momentum_rewards = self.__get_current_yearly_znn_rewards() * \
            self.ZNN_REWARD_SHARE_FOR_PILLAR_MOMENTUMS
        total_momentums_produced = self.pillars_produced_momentums_top_30 + \
            self.pillars_produced_momentums_not_top_30
        momentum_rewards_share = self.pillars_produced_momentums_not_top_30 / \
            total_momentums_produced if total_momentums_produced > 0 else 0
        return total_yearly_momentum_rewards * momentum_rewards_share
