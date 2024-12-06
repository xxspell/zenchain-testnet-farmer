import asyncio
import traceback
from typing import Dict, Any

import httpx

from core.database.models import Account, Action
from core.services.captcha import solve_recaptcha_v3
from core.services.handlers.base import BaseActionHandler
from core.settings import settings
from core.utils.log import xlogger


class FaucetActionHandler(BaseActionHandler):
    MAX_RETRIES = 8
    RETRY_DELAY = 3

    @classmethod
    async def _execute_action(
            cls,
            account: Account,
            action: Action,
            client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        try:
            additional_headers = {
                "Host": "faucet.zenchain.io",
                "Origin": "https://faucet.zenchain.io",
                "Referer": "https://faucet.zenchain.io/",

            }
            cls.update_client_headers(client, additional_headers)

            user_agent = cls.get_client_header(client, "User-Agent")
            recaptcha_token = await solve_recaptcha_v3(user_agent, settings.app.captcha_website_key_faucet, settings.app.captcha_website_url_faucet)
            message = None
            for attempt in range(1, cls.MAX_RETRIES + 1):
                try:




                    response = await client.post(
                        'https://faucet.zenchain.io/api',
                        json={
                            'address': account.address,
                            'recaptcha': recaptcha_token
                        }
                    )
                    result = response.json()

                    if 'hash' in result and 'dripAmount' in result:
                        return {
                            'status': 'success',
                            'hash': result['hash'],
                            'dripAmount': result['dripAmount']
                        }


                    elif 'error' in result:
                        error_message = result['error']
                        if "daily faucet limit" in error_message.lower():
                            return {
                                'status': 'failed',
                                'message': error_message

                            }
                        else:
                            return {
                                'status': 'failed',
                                'message': f"Unexpected error: {error_message}"
                            }

                    return {
                        'status': 'failed',
                        'message': f"HTTP {response.status_code}: {response.text}"
                    }


                except httpx.RequestError as e:
                    xlogger.error(
                        f"{attempt}/{cls.MAX_RETRIES} failed with exception: {e}"
                    )
                    message = str(e)

                if attempt < cls.MAX_RETRIES:
                    xlogger.info(f"Waiting {cls.RETRY_DELAY} seconds before trying again...")
                    await asyncio.sleep(cls.RETRY_DELAY)

            return {
                'status': 'failed',
                'error': f"Request failed after {cls.MAX_RETRIES} attempts. Message: {message}",
            }



        except Exception as e:
            xlogger.error(traceback.format_exc())
            return {
                'status': 'failed',
                'error': str(e)
            }