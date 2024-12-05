import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from datetime import datetime, timedelta

from sqlalchemy.orm import selectinload

from core.database.models import ActionType, Action, ActionStatus, Account
from core.services.handlers import ActionHandlerRegistry
from core.utils.log import xlogger


class ActionDependencyManager:
    DEPENDENCIES = {
        ActionType.FAUCET: {
            'required_actions': [ActionType.WAITLIST],
        },
        ActionType.BRIDGE: {
            'required_actions': [
                ActionType.WAITLIST,
                ActionType.FAUCET
            ],
            'time_constraints': {
                ActionType.FAUCET: {
                    'max_age_hours': 23
                }
            }
        }
    }

    @classmethod
    async def can_perform_action(
            cls,
            session: AsyncSession,
            account_id: int,
            action_type: ActionType
    ) -> bool:
        if action_type not in cls.DEPENDENCIES:
            return True

        dependencies = cls.DEPENDENCIES[action_type]

        for required_action in dependencies.get('required_actions', []):
            last_action = await cls._get_last_successful_action(
                session, account_id, required_action
            )

            if not last_action:
                return False

            time_constraints = dependencies.get('time_constraints', {}).get(required_action)
            if time_constraints:
                max_age = time_constraints.get('max_age_hours')
                if max_age:
                    age = datetime.utcnow() - last_action.created_at
                    if age > timedelta(hours=max_age):
                        return False

        return True

    @classmethod
    async def _get_last_successful_action(
            cls,
            session: AsyncSession,
            account_id: int,
            action_type: ActionType
    ):
        query = select(Action).filter(
            Action.account_id == account_id,
            Action.action_type == action_type,
            Action.status == ActionStatus.SUCCESS
        ).order_by(Action.created_at.desc()).limit(1)

        result = await session.execute(query)
        return result.scalar_one_or_none()


class ActionService:
    @classmethod
    async def create_action(
            cls,
            session: AsyncSession,
            account_id: int,
            action_type: ActionType,
            payload: dict = None
    ):
        if not await ActionDependencyManager.can_perform_action(
                session, account_id, action_type
        ):
            raise ValueError(f"Action {action_type} is not allowed")

        action = Action(
            account_id=account_id,
            action_type=action_type,
            status=ActionStatus.PENDING,
            payload=payload or {}
        )

        session.add(action)
        await session.commit()

        return action

    @classmethod
    async def execute_action(
            cls,
            session: AsyncSession,
            account,
            action: Action
    ):
        try:
            handler = ActionHandlerRegistry.get_handler(action.action_type)

            result = await handler.execute(account, action)

            if result['status'] == 'success':
                action.status = ActionStatus.SUCCESS
                action.payload.update(result)
            else:
                action.status = ActionStatus.FAILED
                action.payload['error'] = result.get('error')

            await session.commit()

            return result

        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }


    @classmethod
    async def execute_action_for_all(
            cls,
            session: AsyncSession,
            action_type: ActionType,
            max_concurrent_tasks: int = 10,
    ):
        """
        Performs the specified action for all active accounts with a limit on the number of simultaneously running tasks.
        """
        query = select(Account).filter(Account.active == True).options(selectinload(Account.actions))
        result = await session.execute(query)
        accounts = result.scalars().all()

        if not accounts:
            return {"status": "failed", "error": "No active accounts found"}

        semaphore = asyncio.Semaphore(max_concurrent_tasks)

        async def process_account(account):
            async with semaphore:
                try:
                    action = await cls.create_action(
                        session=session,
                        account_id=account.id,
                        action_type=action_type,
                    )
                    result = await cls.execute_action(session, account, action)
                    return {account.email: result}
                except Exception as e:
                    xlogger.error(e)
                    return {account.email: {"status": "failed", "error": str(e)}}

        tasks = [process_account(account) for account in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results