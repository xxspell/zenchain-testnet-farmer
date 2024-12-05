import json
from abc import ABC, abstractmethod
from typing import Dict, Any

import httpx

from core.database.models import Account, Action
from core.utils.log import xlogger


class BaseActionHandler:
    @classmethod
    @abstractmethod
    async def execute(
            cls,
            account: Account,
            action: Action
    ) -> Dict[str, Any]:
        try:

            if isinstance(account.headers, str):
                try:
                    headers = json.loads(account.headers.replace("'", '"'))
                except json.JSONDecodeError as e:
                    xlogger.error(f"Invalid JSON in headers: {e}")
                    headers = {}
            elif isinstance(account.headers, dict):
                headers = account.headers
            else:
                headers = {}
                xlogger.critical("Headers format not recognized, using empty headers.")
            async with httpx.AsyncClient(
                    proxy=account.proxy,
                    headers=headers,
                    timeout=httpx.Timeout(30.0, connect=10.0)
            ) as client:
                return await cls._execute_action(
                    account,
                    action,
                    client
                )

        except Exception as e:
            xlogger.error(e)
            return {
                'status': 'failed',
                'error': str(e)
            }

    @classmethod
    def get_client_header(cls, client: httpx.AsyncClient, header_name: str) -> str:
        """
        Returns the value of a specific client header.
        """
        return client.headers.get(header_name, "")


    @classmethod
    def update_client_headers(cls, client: httpx.AsyncClient, additional_headers: Dict[str, Any]) -> None:
        """
        Updates client headers.
        """
        client.headers.update(additional_headers)