import random
import traceback
from typing import Dict, Any

import httpx

from core.database.models import Account, Action
from core.services.handlers.base import BaseActionHandler
from core.services.staking import ZenchainAsyncStaking
from core.utils.log import xlogger


class StakeActionHandler(BaseActionHandler):
    RPC_URL = 'https://zenchain-testnet.api.onfinality.io/public'

    @classmethod
    async def _execute_action(
            cls,
            account: Account,
            action: Action,
            client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        try:
            staker = ZenchainAsyncStaking(
                rpc_url=cls.RPC_URL,
                private_key=account.private_key,
                proxy=account.proxy,
            )
            random_perc = random.uniform(40, 77)
            result = await staker.precise_stake(
                stake_amount=f'{random_perc}%',
                reward_destination=0
            )

            if result and result.get('status') == 1:
                xlogger.info(f"Success execute stake. TX: {result.get('transactionHash', '').hex()}")
                return {
                    'status': 'success',
                    'transaction_hash': result.get('transactionHash', '').hex(),
                    'block_number': result.get('blockNumber', 0),
                    'gas_used': result.get('gasUsed', 0),
                    'effective_gas_price': result.get('effectiveGasPrice', 0)
                }
            else:
                return {
                    'status': 'failed',
                    'error': f"Staking transaction failed. Raw result: {result}"
                }

        except Exception as e:
            xlogger.error(traceback.format_exc())
            return {
                'status': 'failed',
                'error': str(e)
            }