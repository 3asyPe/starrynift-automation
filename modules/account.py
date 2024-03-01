import asyncio
import random
import time
from eth_account import Account as EthAccount
from eth_account.messages import encode_defunct
from loguru import logger
from modules.utils import retry
from settings import BNB_RPC, DISABLE_SSL, OPBNB_RPC, REF_LINK, USER_IDS_TO_FOLLOW
from config import DAILY_CLAIM_ABI
import aiohttp

import datetime

from web3 import AsyncWeb3
from web3.middleware import async_geth_poa_middleware
from web3.exceptions import TransactionNotFound


class Account:
    def __init__(self, id: int, key: str, proxy: str, user_agent: str):
        self.headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Host": "api.starrynift.art",
            "Origin": "https://starrynift.art",
            "Referer": "https://starrynift.art/",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": user_agent,
        }

        self.id = id
        self.key = key
        self.proxy = proxy
        self.account = EthAccount.from_key(self.key)
        self.address = self.account.address
        self.user_agent = user_agent

        self.referral_code = REF_LINK.split("=")[1]

        self.w3 = AsyncWeb3(
            AsyncWeb3.AsyncHTTPProvider(BNB_RPC),
            middlewares=[async_geth_poa_middleware],
        )

        self.quests_mapping = {
            "Follow": self.follow_user,
            "Online": self.complete_online_quest,
        }

        self.user_id = None

    async def make_request(self, method, url, **kwargs):
        if DISABLE_SSL:
            kwargs["ssl"] = False

        async with aiohttp.ClientSession(
            headers=self.headers, trust_env=True
        ) as session:
            return await session.request(
                method, url, proxy=f"http://{self.proxy}", **kwargs
            )

    def get_current_date(self, utc=False):
        if utc:
            return datetime.datetime.utcnow().strftime("%Y%m%d")
        return datetime.datetime.now().strftime("%Y-%m-%d")

    def get_utc_timestamp(self):
        return (
            datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            )[:-3]
            + "Z"
        )

    async def wait_until_tx_finished(
        self, hash: str, max_wait_time=480, web3=None
    ) -> None:
        if web3 is None:
            web3 = self.w3

        start_time = time.time()
        while True:
            try:
                receipts = await web3.eth.get_transaction_receipt(hash)
                status = receipts.get("status")
                if status == 1:
                    logger.success(f"[{self.address}] {hash.hex()} successfully!")
                    return receipts["transactionHash"].hex()
                elif status is None:
                    await asyncio.sleep(0.3)
                else:
                    logger.error(
                        f"[{self.id}][{self.address}] {hash.hex()} transaction failed! {receipts}"
                    )
                    return None
            except TransactionNotFound:
                if time.time() - start_time > max_wait_time:
                    logger.error(
                        f"[{self.id}][{self.address}]{hash.hex()} transaction failed!"
                    )
                    return None
                await asyncio.sleep(1)

    async def send_data_tx(
        self, to, from_, data, gas_price=None, gas_limit=None, nonce=None, chain_id=None
    ):
        if chain_id == 56:
            web3 = self.w3
        elif chain_id == 204:
            web3 = AsyncWeb3(
                AsyncWeb3.AsyncHTTPProvider(OPBNB_RPC),
                middlewares=[async_geth_poa_middleware],
            )
        else:
            raise ValueError("Invalid chain id")

        transaction = {
            "to": to,
            "from": from_,
            "data": data,
            "gasPrice": gas_price or web3.to_wei(await web3.eth.gas_price, "gwei"),
            "gas": gas_limit or await web3.eth.estimate_gas({"to": to, "data": data}),
            "nonce": nonce or await web3.eth.get_transaction_count(self.address),
            "chainId": chain_id or await web3.eth.chain_id,
        }

        signed_transaction = web3.eth.account.sign_transaction(transaction, self.key)
        try:
            transaction_hash = await web3.eth.send_raw_transaction(
                signed_transaction.rawTransaction
            )
            tx_hash = await self.wait_until_tx_finished(
                transaction_hash, max_wait_time=480, web3=web3
            )
            if tx_hash is None:
                return False, None
            return True, tx_hash
        except Exception as e:
            logger.error(f"[{self.id}][{self.address}] Error while sending tx | {e}")
            return e, None

    def sign_msg(self, msg):
        return self.w3.eth.account.sign_message(
            (encode_defunct(text=msg)), self.key
        ).signature.hex()

    async def get_login_signature_message(self):
        req = await self.make_request(
            "get",
            f"https://api.starrynift.art/api-v2/starryverse/auth/wallet/challenge?address={self.address}",
        )
        message = (await req.json()).get("message")
        if message is None:
            raise RuntimeError("Error while getting signature message")
        return message

    @retry
    async def get_mint_signature(self):
        response = await self.make_request(
            "post",
            "https://api.starrynift.art/api-v2/citizenship/citizenship-card/sign",
            json={"category": 1},
        )

        if response.status not in (200, 201):
            raise RuntimeError(
                f"Error while getting mint signature message | {await response.text()}"
            )

        return (await response.json()).get("signature")

    @retry
    async def login(self):
        logger.info(f"[{self.id}][{self.address}] Logging in...")

        signature = self.sign_msg(await self.get_login_signature_message())

        response = await self.make_request(
            "post",
            "https://api.starrynift.art/api-v2/starryverse/auth/wallet/evm/login",
            json={
                "address": self.address,
                "signature": signature,
                "referralCode": self.referral_code,
                "referralSource": 0,
            },
        )
        res_json = await response.json()
        auth_token = res_json.get("token")

        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        else:
            raise RuntimeError(f"Error while logging in")

        info = await self.get_current_user_info()
        self.user_id = info["userId"]

        return bool(auth_token)

    async def mint_nft_pass(self):
        logger.info(f"[{self.id}][{self.address}] Minting pass...")

        signature = await self.get_mint_signature()

        status, tx_hash = await self.send_mint_tx(signature)

        if status is True and await self.send_mint_tx_hash(tx_hash):
            logger.success(f"[{self.id}][{self.address}] | Pass minted: {tx_hash}")
            return True

        logger.error(
            f"[{self.id}][{self.address}] | Error while minting pass: {status}"
        )
        return False

    @retry
    async def send_mint_tx(self, signature):
        return await self.send_data_tx(
            to="0xC92Df682A8DC28717C92D7B5832376e6aC15a90D",
            from_=self.address,
            data=f"0xf75e03840000000000000000000000000000000000000000000000000000000000000020000000000000000000000000{self.address[2:]}000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000041{signature[2:]}00000000000000000000000000000000000000000000000000000000000000",
            gas_price=self.w3.to_wei(2, "gwei"),
            gas_limit=210000,
            chain_id=56,
        )

    @retry
    async def check_if_pass_is_minted(self):
        logger.info(
            f"[{self.id}][{self.address}] Checking if pass has already been minted..."
        )

        response = await self.make_request(
            "get",
            f"https://api.starrynift.art/api-v2/citizenship/citizenship-card/check-card-minted?address={self.address}",
        )

        if response.status not in (200, 201):
            raise RuntimeError(
                f"Error while checking if pass is minted | {await response.text()}"
            )

        return (await response.json()).get("isMinted")

    @retry
    async def send_mint_tx_hash(self, tx_hash):
        resp = await self.make_request(
            "post",
            "https://api.starrynift.art/api-v2/webhook/confirm/citizenship/mint",
            json={"txHash": tx_hash},
        )
        if resp.status not in (200, 201) or (await resp.json()).get("ok") != 1:
            raise RuntimeError(
                f"Error while sending mint tx hash | {await resp.text()}"
            )

        return True

    async def daily_claim(self):
        logger.info(f"[{self.id}][{self.address}] Checking in...")

        time_to_claim = await self.get_daily_claim_time()
        if time_to_claim > 0:
            logger.info(
                f"[{self.id}][{self.address}] Next claim in {datetime.timedelta(seconds=time_to_claim)}"
            )
            return

        result = await self.send_daily_tx()
        if result is None:
            logger.error(f"[{self.id}][{self.address}] Failed daily check in")
            return

        status, tx_hash = result

        if status is True and await self.send_daily_tx_hash(tx_hash):
            logger.success(f"[{self.id}][{self.address}] Successfully daily checked in")
        else:
            logger.error(f"[{self.id}][{self.address}] Failed daily check in")

    @retry
    async def send_daily_tx(self):
        status, hash = await self.send_data_tx(
            to="0xE3bA0072d1da98269133852fba1795419D72BaF4",
            from_=self.address,
            data=f"0x9e4cda43",
            gas_price=self.w3.to_wei(2, "gwei"),
            gas_limit=100000,
            chain_id=56,
        )

        if not status:
            raise RuntimeError(f"Error while sending daily tx | {hash}")

        return status, hash

    @retry
    async def send_daily_tx_hash(self, tx_hash):
        resp = await self.make_request(
            "post",
            "https://api.starrynift.art/api-v2/webhook/confirm/daily-checkin/checkin",
            json={"txHash": tx_hash},
        )

        if resp.status not in (200, 201) or (await resp.json()).get("ok") != 1:
            raise RuntimeError(
                f"Error while sending daily tx hash | {await resp.text()}"
            )

        return True

    @retry
    async def get_daily_claim_time(self):
        contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(
                "0xe3ba0072d1da98269133852fba1795419d72baf4"
            ),
            abi=DAILY_CLAIM_ABI,
        )
        return await contract.functions.getTimeUntilNextSignIn(self.address).call()

    async def complete_quests(self):
        quests = await self.get_quests()

        for item in quests:
            quest = item["name"]
            if not item["completed"]:
                logger.info(f"[{self.id}][{self.address}] Completing quest: {quest}")
                try:
                    func = self.quests_mapping.get(quest)
                    if func is None:
                        logger.warning(f"Quest {quest} is not supported")
                        continue
                    result = await func()
                    if result is False:
                        logger.error(
                            f"[{self.id}][{self.address}] {quest} Quest Failed"
                        )
                    else:
                        logger.success(
                            f"[{self.id}][{self.address}] {quest} Quest Completed"
                        )
                except RuntimeError as e:
                    logger.error(
                        f"[{self.id}][{self.address}] {quest} Quest Failed | {e}"
                    )
            else:
                logger.info(
                    f"[{self.id}][{self.address}] {quest} Quest Already Compeleted"
                )

    @retry
    async def get_quests(self):
        response = await self.make_request(
            "get",
            f"https://api.starrynift.art/api-v2/citizenship/citizenship-card/daily-tasks?page=1&page_size=10",
        )

        if response.status not in (200, 201) or "items" not in await response.json():
            raise RuntimeError(f"Error while getting quests | {await response.text()}")

        return (await response.json()).get("items")

    @retry
    async def follow_user(self):
        user_to_follow = None
        for user_id in USER_IDS_TO_FOLLOW:
            info = await self.get_user_info(user_id)
            if info["userId"] != self.user_id and not info["isFollow"]:
                user_to_follow = user_id
                break

        if user_to_follow is None:
            logger.error(
                f"[{self.id}][{self.address}] Already followed all users. Can't complete quest"
            )
            return False

        response = await self.make_request(
            "post",
            "https://api.starrynift.art/api-v2/starryverse/user/follow",
            json={"userId": user_to_follow},
        )

        if response.status not in (200, 201) or (await response.json()).get("ok") != 1:
            raise RuntimeError(f"Error while following user | {await response.text()}")

        return True

    @retry
    async def get_user_info(self, user_id):
        response = await self.make_request(
            "get",
            f"https://api.starrynift.art/api-v2/starryverse/character/user/{user_id}",
        )

        if response.status not in (200, 201):
            raise RuntimeError(
                f"Error while getting user info | {await response.text()}"
            )

        return await response.json()

    @retry
    async def get_current_user_info(self):
        response = await self.make_request(
            "get",
            f"https://api.starrynift.art/api-v2/starryverse/character",
        )

        if response.status not in (200, 201):
            raise RuntimeError(
                f"Error while getting user info | {await response.text()}"
            )

        return await response.json()

    async def complete_online_quest(self):
        logger.info(f"[{self.id}][{self.address}] It would take about 10 minutes...")
        for i in range(21):
            await self.send_ping()
            await asyncio.sleep(30)

        return True

    @retry
    async def send_ping(self):
        response = await self.make_request(
            "get",
            f"https://api.starrynift.art/api-v2/space/online/ping",
        )

        if response.status not in (200, 201):
            raise RuntimeError(f"Error while sending ping | {await response.text()}")

        return True

    async def get_if_already_ruffled_today(self):
        response = await self.make_request(
            "post",
            f"https://api.starrynift.art/api-v2/citizenship/raffle/status",
            json={},
        )

        if response.status not in (200, 201):
            raise RuntimeError(
                f"Error while checking if ruffled today | {await response.text()}"
            )

        return (await response.json()).get("used")

    async def ruffle(self):
        logger.info(f"[{self.id}][{self.address}] Ruffling...")

        await asyncio.sleep(random.randint(3, 10))
        info = await self.get_ruffle_info()
        if info["used"]:
            logger.info(f"[{self.id}][{self.address}] Already used free ruffle today")
            return

        if not info["signature"]:
            logger.error(f"[{self.id}][{self.address}] Daily wasn't completed")
            return
        logger.info(f"[{self.id}][{self.address}] Ruffle xp: {info['xp']}")

        result = await self.send_ruffle_tx(
            xp=info["xp"],
            signature=info["signature"],
            nonce=info["nonce"],
        )
        if result is None:
            logger.error(f"[{self.id}][{self.address}] Ruffle failed")
            return

        status, tx_hash = result

        await self.send_ruffle_hash(tx_hash)

        logger.success(f"[{self.id}][{self.address}] Ruffle success")
        return True

    @retry
    async def send_ruffle_tx(self, xp, nonce, signature):
        data = (
            "0x9fc96c7e"
            "0000000000000000000000000000000000000000000000000000000000000020"
            f"000000000000000000000000{self.address[2:]}"
            f"{format(xp, '064x')}"
            f"{format(int(nonce), '064x')}"
            "0000000000000000000000000000000000000000000000000000000000000080"
            f"0000000000000000000000000000000000000000000000000000000000000041{signature[2:]}"
            "00000000000000000000000000000000000000000000000000000000000000"
        )

        status, tx_hash = await self.send_data_tx(
            to=self.w3.to_checksum_address(
                "0x557764618fc2f4eca692d422ba79c70f237113e6"
            ),
            from_=self.address,
            data=data,
            gas_price=self.w3.to_wei("0.00002", "gwei"),
            gas_limit=100000,
            chain_id=204,
        )
        if not status:
            raise RuntimeError(f"Error while sending ruffle tx | {tx_hash}")

        return status, tx_hash

    @retry
    async def send_ruffle_hash(self, tx_hash):
        response = await self.make_request(
            "post",
            "https://api.starrynift.art/api-v2/webhook/confirm/raffle/mint",
            json={"txHash": tx_hash},
        )

        if response.status not in (200, 201) or (await response.json()).get("ok") != 1:
            raise RuntimeError(
                f"Error while sending ruffle tx hash | {await response.text()}"
            )

        return True

    @retry
    async def get_ruffle_info(self):
        response = await self.make_request(
            "post",
            f"https://api.starrynift.art/api-v2/citizenship/raffle/status",
            json={},
        )

        if response.status not in (200, 201):
            raise RuntimeError(
                f"Error while getting ruffle info | {await response.text()}"
            )

        return await response.json()
