from web3 import Web3
from eth_account import Account

from core.utils.log import xlogger


def get_address_from_private_key(private_key: str) -> str:
    """
    Retrieves the wallet address from the private key

    :param private_key: Private key (with or without 0x prefix)
    :return: Wallet address
    """

    if not private_key.startswith('0x'):
        private_key = '0x' + private_key

    try:
        account = Account.from_key(private_key)

        address = Web3.to_checksum_address(account.address)

        return address
    except Exception as e:
        xlogger.debug(f"Error extracting address from private key: {str(e)}")
        return None