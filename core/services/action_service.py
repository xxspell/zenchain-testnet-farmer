import asyncio
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from datetime import datetime, timedelta

from sqlalchemy.orm import selectinload

from core.database.connect import AsyncSessionLocal
from core.database.models import ActionType, Action, ActionStatus, Account
from core.services.handlers import ActionHandlerRegistry
from core.settings import settings
from core.utils.log import xlogger


class ActionDependencyManager:
    DEPENDENCIES = {
        ActionType.FAUCET: {
            'required_actions': [ActionType.WAITLIST],
        },
        ActionType.STAKE: {
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
    async def get_missing_dependencies(
            cls,
            session: AsyncSession,
            account_id: int,
            action_type: ActionType
    ) -> list:
        xlogger.debug(f"Getting missing dependencies for {action_type}")

        if action_type not in cls.DEPENDENCIES:
            return []

        dependencies = cls.DEPENDENCIES[action_type]
        missing_dependencies = []

        for required_action in dependencies.get('required_actions', []):
            xlogger.debug(f"Checking dependency: {required_action}")

            last_action = await cls._get_last_successful_action(
                session, account_id, required_action
            )

            if last_action:
                time_constraints = dependencies.get('time_constraints', {}).get(required_action)
                if time_constraints:
                    max_age = time_constraints.get('max_age_hours')
                    if max_age:
                        age = datetime.utcnow() - last_action.created_at
                        xlogger.debug(f"Last {required_action} was {age} ago, max allowed {max_age} hours")

                        if age > timedelta(hours=max_age):
                            missing_dependencies.append(required_action)
            else:
                missing_dependencies.append(required_action)

        return missing_dependencies

    @classmethod
    async def can_perform_action(
            cls,
            session: AsyncSession,
            account_id: int,
            action_type: ActionType
    ) -> bool:
        xlogger.debug(f"Checking if action {action_type} is allowed for account {account_id}")

        if action_type not in cls.DEPENDENCIES:
            xlogger.debug(f"No dependencies for {action_type}, allowing action")
            return True

        dependencies = cls.DEPENDENCIES[action_type]

        for required_action in dependencies.get('required_actions', []):
            xlogger.debug(f"Checking required action: {required_action}")

            last_action = await cls._get_last_successful_action(
                session, account_id, required_action
            )

            if not last_action:
                xlogger.debug(f"No successful {required_action} found")
                return False

            time_constraints = dependencies.get('time_constraints', {}).get(required_action)
            if time_constraints:
                max_age = time_constraints.get('max_age_hours')
                if max_age:
                    age = datetime.utcnow() - last_action.created_at
                    xlogger.debug(f"Last {required_action} was {age} ago, max allowed {max_age} hours")

                    if age > timedelta(hours=max_age):
                        xlogger.debug(f"Action {required_action} is too old")
                        return False

        xlogger.debug(f"All dependencies for {action_type} are satisfied")
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
        last_action = result.scalar_one_or_none()

        if last_action:
            xlogger.debug(f"Last successful {action_type} action:")
            xlogger.debug(f"ID: {last_action.id}")
            xlogger.debug(f"Created At: {last_action.created_at}")
            xlogger.debug(f"Time since last action: {datetime.utcnow() - last_action.created_at}")
        else:
            xlogger.warning(f"No successful {action_type} action found")
        return last_action


class ActionService:
    @classmethod
    async def create_action(
            cls,
            session: AsyncSession,
            account_id: int,
            action_type: ActionType,
            payload: dict = None
    ):
        xlogger.debug(f"Attempting to create action {action_type} for account {account_id}")

        try:
            can_perform = await ActionDependencyManager.can_perform_action(
                session, account_id, action_type
            )
        except Exception as e:
            xlogger.error(f"Error checking action permissions: {e}")
            raise

        if not can_perform:
            xlogger.warning(f"Action {action_type} is not allowed for account {account_id}")
            raise ValueError(f"Action {action_type} is not allowed")

        action = Action(
            account_id=account_id,
            action_type=action_type,
            status=ActionStatus.PENDING,
            payload=payload or {}
        )

        session.add(action)
        await session.commit()

        xlogger.debug(f"Action {action_type} created for account {account_id}")
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
        query = select(Account).filter(Account.active == True).options(selectinload(Account.actions))
        result = await session.execute(query)
        accounts = result.scalars().all()

        if not accounts:
            return {"status": "failed", "error": "No active accounts found"}

        semaphore = asyncio.Semaphore(max_concurrent_tasks)

        async def process_account(account):
            async with AsyncSessionLocal() as new_session:
                xlogger.log_prefix_var.set(f"{action_type}-{account.id} | ")
                initial_delay = random.uniform(0, max_concurrent_tasks * 10)
                xlogger.debug(f"Delaying account {account.email} processing by {initial_delay:.2f} seconds")
                await asyncio.sleep(initial_delay)

                async with semaphore:
                    try:
                        missing_dependencies = await ActionDependencyManager.get_missing_dependencies(
                            new_session, account.id, action_type
                        )


                        for dep_action_type in missing_dependencies:
                            xlogger.debug(f"Processing missing dependency {dep_action_type} for account {account.email}")

                            try:
                                dep_action = await cls.create_action(
                                    session=new_session,
                                    account_id=account.id,
                                    action_type=dep_action_type,
                                )
                                delay_env = settings.env.delay_between_dependency_executions
                                delay = random.uniform(delay_env[0], delay_env[1])
                                xlogger.debug(f"Waiting {delay:.2f} seconds before {dep_action_type}")
                                await asyncio.sleep(delay)

                                result = await cls.execute_action(new_session, account, dep_action)

                                if result.get('status') != 'success':
                                    xlogger.warning(f"Dependency {dep_action_type} failed: {result}")
                                    return {account.email: result}

                            except Exception as e:
                                xlogger.error(f"Error processing dependency {dep_action_type}: {e}")
                                return {account.email: {"status": "failed", "error": str(e)}}

                        action = await cls.create_action(
                            session=new_session,
                            account_id=account.id,
                            action_type=action_type,
                        )

                        delay_env = settings.env.delay_between_dependency_executions
                        delay = random.uniform(delay_env[0], delay_env[1])
                        xlogger.debug(f"Waiting {delay:.2f} seconds before main action {action_type}")
                        await asyncio.sleep(delay)

                        result = await cls.execute_action(new_session, account, action)
                        return {account.email: result}

                    except Exception as e:
                        await session.rollback()
                        xlogger.error(f"Error processing account {account.email}: {e}")
                        return {account.email: {"status": "failed", "error": str(e)}}

        tasks = [process_account(account) for account in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results
