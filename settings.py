# Referal link to StarryNift
REF_LINK = "https://starrynift.art?referralCode=8RrY9jzgE8"

# User ids to follow for quest completion
# Make sure to input user id, not link
# Will Follow 1 not followed user per account daily.
# You can get your userIds by using Get accounts stats option
USER_IDS_TO_FOLLOW = ["bWDM5GLBvj", "y7SauYfQp2"]

SHUFFLE_ACCOUNTS = False
RETRIES = 2

THREADS = 3

MIN_SLEEP = 1
MAX_SLEEP = 10

BNB_RPC = "https://bsc.publicnode.com"


# ___________________________________________
# |             BINANCE WITHDRAW            |

BINANCE_API_KEY = ""
BINANCE_SECRET_KEY = ""

MIN_WITHDRAW = 0.01001
MAX_WITHDRAW = 0.0105

USE_PROXY_FOR_BINANCE = (
    False  # If True, you need to whitelist your proxies IPs in Binance API settings
)
