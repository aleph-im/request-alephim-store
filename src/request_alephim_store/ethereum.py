import web3
from web3.gas_strategies.time_based import medium_gas_price_strategy
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from web3.exceptions import TransactionNotFound
from web3.contract import get_event_data
from web3._utils.events import (
    construct_event_topic_set,
)
import json
import os
from pathlib import Path
from eth_account.messages import defunct_hash_message, encode_defunct
from eth_account import Account
from eth_keys import keys
from hexbytes import HexBytes
from async_lru import alru_cache
from functools import lru_cache
from .settings import settings

import logging
LOGGER = logging.getLogger(__name__)

DECIMALS = 10**18

NONCE = None

@lru_cache(maxsize=2)
def get_web3():
    w3 = None
    if settings.ethereum_api_server:
        w3 = web3.Web3(web3.providers.rpc.HTTPProvider(settings.ethereum_api_server))
    else:
        from web3.auto.infura import w3 as iw3
        assert w3.isConnected()
        w3 = iw3
    
    w3.eth.setGasPriceStrategy(rpc_gas_price_strategy)
    
    return w3

@lru_cache(maxsize=2)
def get_storage_contract_abi():
    return json.load(open(os.path.join(Path(__file__).resolve().parent, 'abi/REQUEST_HASH_STORAGE.json')))

@lru_cache(maxsize=2)
def get_storage_contract(web3):
    tokens = web3.eth.contract(address=web3.toChecksumAddress(settings.ethereum_event_contract), abi=get_storage_contract_abi())
    return tokens

def get_gas_price():
    w3 = get_web3()
    return w3.eth.generateGasPrice()

@lru_cache(maxsize=2)
def get_account():
    if settings.ethereum_pkey:
        pri_key = HexBytes(settings.ethereum_pkey)
        account = Account.privateKeyToAccount(pri_key)
        return account
    else:
        return None


async def get_logs_query(web3, contract, start_height, end_height, topics):
    logs = web3.eth.getLogs({'address': contract.address,
                             'fromBlock': start_height,
                             'toBlock': end_height,
                             'topics': topics})
    for log in logs:
        yield log
        

async def get_logs(web3, contract, start_height, topics=None):
    print(start_height)
    try:
        logs = get_logs_query(web3, contract,
                              start_height+1, 'latest', topics=topics)
        async for log in logs:
            yield log
    except ValueError as e:
        # we got an error, let's try the pagination aware version.
        if e.args[0]['code'] != -32005:
            return

        last_block = web3.eth.blockNumber
#         if (start_height < config.ethereum.start_height.value):
#             start_height = config.ethereum.start_height.value

        end_height = start_height + 6000

        while True:
            try:
                logs = get_logs_query(web3, contract,
                                      start_height, end_height, topics=topics)
                async for log in logs:
                    yield log

                start_height = end_height + 1
                end_height = start_height + 6000

                if start_height > last_block:
                    LOGGER.info("Ending big batch sync")
                    break

            except ValueError as e:
                if e.args[0]['code'] == -32005:
                    end_height = start_height + 1000
                else:
                    raise
            

async def process_storage_history(start_height=0):
    web3 = get_web3()
    contract = get_storage_contract(web3)
    abi = contract.events.NewHash._get_event_abi()
    topic = construct_event_topic_set(abi, web3.codec)
    
    start = max(start_height, settings.ethereum_min_height)
    last_height = start
    end_height = web3.eth.blockNumber
    count = 0

    async for i in get_logs(web3, contract, start, topics=topic):
        count += 1
        evt_data = get_event_data(web3.codec, abi, i)
        args = evt_data['args']
        height = evt_data['blockNumber']
        LOGGER.debug(f"{height}: {evt_data}")
        context = {"source_chain": 'ETH',
                   "source_contract": settings.ethereum_event_contract,
                   "tx_hash": evt_data.transactionHash.hex(),
                   "height": evt_data.blockNumber,
                   "submitter": args['hashSubmitter']}
        yield (context, args["hash"])
        
    LOGGER.info(f"Scanned {count} events")