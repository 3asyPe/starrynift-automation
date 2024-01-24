from typing import Optional
from loguru import logger

from hdwallet import BIP44HDWallet
from hdwallet.cryptocurrencies import EthereumMainnet
from hdwallet.derivations import BIP44Derivation
from hdwallet.utils import generate_mnemonic


async def generate_wallets():
    num = input("How many wallets do you want to generate? ")
    logger.info(f"Generating {num} wallets")

    wallets = {
        "mnemonics": [],
        "addresses": [],
        "keys": [],
    }

    for i in range(int(num)):
        # Generate english mnemonic words
        MNEMONIC: str = generate_mnemonic(language="english", strength=128)
        # Secret passphrase/password for mnemonic
        PASSPHRASE: Optional[str] = None  # "meherett"

        # Initialize Ethereum mainnet BIP44HDWallet
        bip44_hdwallet: BIP44HDWallet = BIP44HDWallet(cryptocurrency=EthereumMainnet)
        # Get Ethereum BIP44HDWallet from mnemonic
        bip44_hdwallet.from_mnemonic(
            mnemonic=MNEMONIC, language="english", passphrase=PASSPHRASE
        )
        # Clean default BIP44 derivation indexes/paths
        bip44_hdwallet.clean_derivation()
        mnemonics = bip44_hdwallet.mnemonic()

        # Derivation from Ethereum BIP44 derivation path
        bip44_derivation: BIP44Derivation = BIP44Derivation(
            cryptocurrency=EthereumMainnet, account=0, change=False, address=0
        )
        # Drive Ethereum BIP44HDWallet
        bip44_hdwallet.from_path(path=bip44_derivation)
        # Print address_index, path, address and private_key
        address = bip44_hdwallet.address()
        key = bip44_hdwallet.private_key()
        # Clean derivation indexes/paths
        bip44_hdwallet.clean_derivation()

        wallets["mnemonics"].append(mnemonics)
        wallets["addresses"].append(address)
        wallets["keys"].append(f"{key}")

    with open(f"data/generated_keys.txt", "w+") as f:
        for x in wallets["keys"]:
            f.write(f"0x{str(x)}\n")

    with open(f"data/generated_addresses.txt", "w+") as f:
        for x in wallets["addresses"]:
            f.write(f"{str(x)}\n")

    with open(f"data/generated_seeds.txt", "w+") as f:
        for x in wallets["mnemonics"]:
            f.write(f"{str(x)}\n")

    logger.success("Done generating wallets")
