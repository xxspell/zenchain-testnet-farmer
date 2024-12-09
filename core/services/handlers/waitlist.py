import asyncio
import traceback
from typing import Dict, Any

import httpx

from core.database.models import Account, Action
from core.services.captcha import solve_recaptcha_v2
from core.services.handlers.base import BaseActionHandler
from core.settings import settings
from core.utils.log import xlogger


class WaitlistActionHandler(BaseActionHandler):
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
                "Host": "www.zenchain.io",
                "Origin": "https://www.zenchain.io",
                "Referer": "https://www.zenchain.io/waitlist",

            }
            cls.update_client_headers(client, additional_headers)

            user_agent = cls.get_client_header(client, "User-Agent")
            recaptcha_token = await solve_recaptcha_v2(user_agent, settings.app.captcha_website_key_waitlist, settings.app.captcha_website_url_waitlist, False)
            message = None
            for attempt in range(1, cls.MAX_RETRIES + 1):
                try:
                    response = await client.post(
                        'https://www.zenchain.io/api/waitlist',
                        json={
                            'address': account.address,
                            'email': account.email,
                            'recaptchaToken': recaptcha_token
                        }
                    )
                    result = response.json()

                    message = result.get('message')

                    if "Successfully added to waitlist" in message:
                        xlogger.info(f"Success execute waitlist")
                        return {
                            'status': 'success',
                            'message': message
                        }

                    else:
                        return {
                            'status': 'failed',
                            'message': f"HTTP {response.status_code}: {message}"
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