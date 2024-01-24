import asyncio
import json
import random
from loguru import logger
from fake_useragent import UserAgent
from modules.account import Account
from modules.generate_wallets import generate_wallets
from modules.withdraw_from_binance import withdraw_from_binance
from settings import SHUFFLE_ACCOUNTS, THREADS
from config import CACHED_USER_AGENTS
from modules.utils import sleep


class Executor:
    def __init__(self, wallets: list[str], proxies: list[str]):
        self.accounts = self._load_accounts(wallets, proxies)

    async def generate_wallets(self):
        await generate_wallets()

    async def withdraw_from_binance(self):
        for i, account in enumerate(self.accounts, start=1):
            await withdraw_from_binance(address=account.address, proxy=account.proxy)

            if i != len(self.accounts):
                await sleep(account.address)

    async def run_starrynift(self):
        groups = self._generate_groups()

        tasks = []
        for id, group in enumerate(groups):
            tasks.append(
                asyncio.create_task(
                    self._run_starrynift(group, id),
                    name=f"group - {id}",
                )
            )

        await asyncio.gather(*tasks)

    async def _run_starrynift(self, group: list[Account], group_id: int):
        for i, account in enumerate(group):
            if i != 0 or group_id != 0:
                await sleep(account)

            logger.info(f"Running #{account.id} account: {account.address}")
            if await account.login():
                if not await account.check_if_pass_is_minted():
                    if not await account.mint_nft_pass():
                        continue

                await account.daily_claim()
                await account.complete_quests()

    async def get_accounts_stats(self):
        stats = {}
        for i, account in enumerate(self.accounts, start=1):
            logger.info(f"[{account.id}][{account.address}] Getting stats...")
            if await account.login():
                info = await account.get_current_user_info()
                stats[account.address] = {
                    "userId": info["userId"],
                    "level": info["level"],
                    "xp": info["xp"],
                    "referralCode": info["referralCode"],
                }

        with open("data/stats.json", "w") as f:
            f.write(json.dumps(stats, indent=4))

        logger.info("Stats saved to data/stats.json")

    def _generate_groups(self):
        global THREADS

        if THREADS <= 0:
            THREADS = 1
        elif THREADS > len(self.accounts):
            THREADS = len(self.accounts)

        group_size = len(self.accounts) // THREADS
        remainder = len(self.accounts) % THREADS

        groups = []
        start = 0
        for i in range(THREADS):
            # Add an extra account to some groups to distribute the remainder
            end = start + group_size + (1 if i < remainder else 0)
            groups.append(self.accounts[start:end])
            start = end

        return groups

    def _load_accounts(self, wallets: list[str], proxies: list[str]) -> list[Account]:
        accounts = []
        for i, (wallet, proxy) in enumerate(zip(wallets, proxies), start=1):
            user_agent = CACHED_USER_AGENTS.get(wallet)

            if user_agent is not None:
                accounts.append(
                    Account(id=i, key=wallet, proxy=proxy, user_agent=user_agent)
                )
            else:
                user_agent = UserAgent(os="windows").random
                CACHED_USER_AGENTS[wallet] = user_agent
                accounts.append(
                    Account(id=i, key=wallet, proxy=proxy, user_agent=user_agent)
                )

        with open("data/cached_user_agents.json", "w") as f:
            f.write(json.dumps(CACHED_USER_AGENTS, indent=4))

        if SHUFFLE_ACCOUNTS:
            random.shuffle(accounts)

        return accounts
