
from .faucet import FaucetActionHandler
from .waitlist import WaitlistActionHandler
from ...database.models import ActionType


class ActionHandlerRegistry:
    _handlers = {
        ActionType.FAUCET: FaucetActionHandler,
        ActionType.WAITLIST: WaitlistActionHandler,
    }

    @classmethod
    def get_handler(cls, action_type: ActionType):
        handler = cls._handlers.get(action_type)
        if not handler:
            raise ValueError(f"No handler for action type {action_type}")
        return handler
