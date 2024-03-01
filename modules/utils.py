import asyncio
import random
import traceback
from loguru import logger

from settings import MAX_SLEEP, MIN_SLEEP, RETRIES


async def sleep(account=None):
    sleep_time = random.randint(MIN_SLEEP, MAX_SLEEP)
    if account:
        logger.info(
            f"[{account.id}][{account.address}] Sleeping for {sleep_time} seconds"
        )
    else:
        logger.info(f"Sleeping for {sleep_time} seconds")
    await asyncio.sleep(sleep_time)


def retry(func):
    async def wrapper(*args, **kwargs):
        retries = 0
        while retries <= RETRIES:
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                traceback.print_exc()
                retries += 1
                logger.error(f"Error | {e}")
                if retries <= RETRIES:
                    logger.info(f"Retrying... {retries}/{RETRIES}")
                    await sleep()

    return wrapper
