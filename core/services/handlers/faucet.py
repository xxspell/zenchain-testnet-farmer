from core.services.handlers.base import BaseActionHandler


class FaucetActionHandler(BaseActionHandler):
    @classmethod
    async def execute(cls, account, action):
        try:
           pass

        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }



