import random
import ccxt
from loguru import logger

from settings import (
    BINANCE_API_KEY,
    BINANCE_SECRET_KEY,
    MAX_WITHDRAW,
    MIN_WITHDRAW,
    USE_PROXY_FOR_BINANCE,
)


async def withdraw_from_binance(address, proxy):
    client_params = {
        "apiKey": BINANCE_API_KEY,
        "secret": BINANCE_SECRET_KEY,
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    }

    amount = round(random.uniform(MIN_WITHDRAW, MAX_WITHDRAW), 6)

    if USE_PROXY_FOR_BINANCE:
        client_params["proxies"] = {
            "http": f"http://{proxy}",
        }

    ccxt_client = ccxt.binance(client_params)

    try:
        withdraw = ccxt_client.withdraw(
            code="BNB",
            amount=amount,
            address=address,
            tag=None,
            params={"network": "BEP20"},
        )
        logger.success(
            f"{ccxt_client.name} - {address} | withdraw {amount} BNB to BNB network)"
        )

    except Exception as error:
        logger.error(f"{ccxt_client.name} - {address} | withdraw error : {error}")
