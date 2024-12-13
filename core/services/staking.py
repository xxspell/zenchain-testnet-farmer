import math
from typing import Union

from web3 import AsyncWeb3, Web3

from core.utils.log import xlogger


class ZenchainAsyncStaking:
    def __init__(
            self,
            rpc_url: str,
            private_key: str,
            proxy: str = None
    ):
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url, request_kwargs=dict(proxy=proxy)))

        self.account = self.w3.eth.account.from_key(private_key)
        self.address = self.account.address
        self.private_key = private_key

        self.STAKING_CONTRACT = Web3.to_checksum_address('0x0000000000000000000000000000000000000800')
        self.STAKING_ABI = [
            {
                "inputs": [{"type": "address"}],
                "name": "bonded",
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"type": "uint256", "name": "value"},
                    {"type": "uint8", "name": "dest"}
                ],
                "name": "bond",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"type": "uint256", "name": "value"}],
                "name": "bondExtra",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

        self.contract = self.w3.eth.contract(
            address=self.STAKING_CONTRACT,
            abi=self.STAKING_ABI
        )

    async def get_current_stake(self) -> float:
        """Getting the current steak size"""
        try:
            stake_amount = await self.contract.functions.bonded(self.address).call()
            stake_float =  Web3.from_wei(stake_amount, 'ether')
            if stake_float > 0:
                order = math.floor(math.log10(stake_float))
                return math.floor(stake_float * (10 ** -order)) * (10 ** order)

            return 0.0
        except Exception as e:
            xlogger.error(f"Error receiving steak: {e}")
            return 0.0

    async def get_dynamic_gas_price(self, multiplier = 1) -> int:
        """Getting gas with a little randomness"""
        base_gas_price = await self.w3.eth.gas_price
        return base_gas_price * multiplier

    async def get_wallet_balance(self) -> float:
        """Getting wallet balance in ETH"""
        try:
            balance_wei = await self.w3.eth.get_balance(self.address)
            return Web3.from_wei(balance_wei, 'ether')
        except Exception as e:
            xlogger.error(f"Error getting balance: {e}")
            return 0.0

    async def precise_stake(
            self,
            stake_amount: Union[float, str],
            reward_destination: int = 0
    ):
        try:
            stake_log_message = f"Staking attempt for address {self.address}: "
            wallet_balance = float(await self.get_wallet_balance())
            xlogger.debug(f"Wallet Balance for {self.address}: {wallet_balance} ZXC")
            stake_log_message += f"Wallet Balance={wallet_balance} ZXC, "

            if isinstance(stake_amount, str) and stake_amount.endswith('%'):
                percent = float(stake_amount.rstrip('%')) / 100
                calculated_stake = wallet_balance * percent
                xlogger.debug(
                    f"Stake Calculation for {self.address}: Percentage={percent * 100}%, Amount={calculated_stake} ZXC")
                stake_log_message += f"Stake Calculation=Percentage({percent*100}%), "
            else:
                calculated_stake = float(stake_amount)
                xlogger.debug(f"Stake Calculation for {self.address}: Fixed Amount={calculated_stake} ZXC")
                stake_log_message += f"Stake Calculation=Fixed Amount, "

            current_stake = await self.get_current_stake()
            xlogger.debug(f"Current Stake for {self.address}: {current_stake} ZXC")

            stake_amount_final = calculated_stake
            stake_amount_wei = int(Web3.to_wei(stake_amount_final, 'ether'))
            gas_price = await self.get_dynamic_gas_price(2)
            xlogger.debug(f"Stake Preparation for {self.address}: Amount={stake_amount_final} ZXC, Gas Price={gas_price}")
            stake_log_message += f"Stake Amount={stake_amount_final} ZXC, Gas Price={gas_price}"

            if current_stake == 0:
                stake_log_message += ", Method=Primary Staking"
                xlogger.debug(f"Staking Method for {self.address}: Primary Staking")
                tx = await self.contract.functions.bond(
                    stake_amount_wei,
                    reward_destination
                ).build_transaction({
                    'from': self.address,
                    'nonce': await self.w3.eth.get_transaction_count(self.address),
                    'gas': 1000000,
                    'gasPrice': gas_price
                })
            else:
                stake_log_message += ", Method=Additional Staking"
                xlogger.debug(f"Staking Method for {self.address}: Additional Staking")
                tx = await self.contract.functions.bondExtra(
                    stake_amount_wei
                ).build_transaction({
                    'from': self.address,
                    'nonce': await self.w3.eth.get_transaction_count(self.address),
                    'gas': 1000000,
                    'gasPrice': gas_price
                })

            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)

            xlogger.debug(f"Transaction Details for {self.address}: Hash={tx_hash.hex()}")
            stake_log_message += f", Transaction Hash={tx_hash.hex()}, Status=Success"
            xlogger.info(stake_log_message)

            return receipt

        except Exception as e:
            xlogger.debug(f"Staking Preparation Error for {self.address}: {str(e)}")
            error_message = f"Staking Error for {self.address}: {str(e)}"
            xlogger.error(error_message)

            import traceback
            xlogger.debug(f"Staking Error Traceback for {self.address}:\n{traceback.format_exc()}")

            return None
