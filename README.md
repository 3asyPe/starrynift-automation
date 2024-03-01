# Script for StarryNift

TG channel - https://t.me/easypeoff

## Capabilities

1) Generate new wallets

2) Withdraw BNB from Binance to BNB chain or opBNB chain

3) Register an account on StarryNift using your referral code

4) Daily check ins

5) Complete quests (Follow and being 10 minutes online are now supported)

6) Use free daily ruffles (free 0 - 50xp on daily basis)

7) Get account stats (UserId, Level, XP, ReferralCode)

Other:

- proxies

- user agents are being randomly generated and cached for each wallet after the first use of the wallet in data/cached_user_agents.json. Every next execution it will use the same user agent it was using previously for this particular wallet

- configurable RPCs

## Installation

Install python3.9 or higher

In project directory run:
```
pip install -r requirements.txt
```

## Settings

Input private keys in data/private_keys.txt

Input proxies in data/proxies.txt

Read and configure script in settings.py

## Run
```
python main.py
```
