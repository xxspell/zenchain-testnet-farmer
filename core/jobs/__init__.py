import asyncio
import time
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.database.connect import AsyncSessionLocal
from core.database.models import ActionType
from core.services.action_service import ActionService
from core.utils.log import xlogger


async def perform_stake_for_all(session: AsyncSession):
    action_service = ActionService()
    results = await action_service.execute_action_for_all(session, ActionType.STAKE, max_concurrent_tasks=5)

    for result in results:
        print(result)


async def main_loop():
    while True:
        start_time = datetime.now()
        xlogger.info(f"Starting stake job at {start_time}")

        try:
            async with AsyncSessionLocal() as session:
                await perform_stake_for_all(session)
        except Exception as e:
            xlogger.error(f"Error in stake job: {e}")

        end_time = datetime.now()
        execution_time = end_time - start_time
        xlogger.info(f"Stake job completed. Execution time: {execution_time}")


        next_run_delay = 23 * 3600
        xlogger.info(f"Waiting {next_run_delay / 3600:.2f} hours until next run")

        await asyncio.sleep(next_run_delay)

