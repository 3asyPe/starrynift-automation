import json


with open("data/private_keys.txt", "r") as f:
    PRIVATE_KEYS = f.read().splitlines()


with open("data/proxies.txt", "r") as f:
    PROXIES = f.read().splitlines()


with open("data/abi/daily_claim_abi.json", "r") as f:
    DAILY_CLAIM_ABI = json.load(f)

try:
    with open("data/cached_user_agents.json", "r") as f:
        CACHED_USER_AGENTS = json.load(f)
except FileNotFoundError:
    CACHED_USER_AGENTS = {}
