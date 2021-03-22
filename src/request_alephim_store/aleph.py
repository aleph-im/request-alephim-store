    
from aleph_client.asynchronous import create_store
from aleph_client.chains.ethereum import ETHAccount
from functools import lru_cache
import io

from .settings import settings
import logging
LOGGER = logging.getLogger(__name__)

@lru_cache(maxsize=32)
def get_aleph_account():
    return ETHAccount(settings.ethereum_pkey)


@lru_cache(maxsize=32)
def get_aleph_address():
    return (get_aleph_account()).get_address()


async def get_previous_stored(session, cid):
    async with session.get("%s/api/v0/messages.json" % (
        settings.aleph_api_server
    ), params={
        "msgType": "STORE",
        "refs": cid, 
        "address": get_aleph_address(),
        "channels": settings.aleph_channel
    }) as resp:
        result = await resp.json()
        if result["pagination_total"] > 0:
            return result["messages"][0]
        else:
            return None


async def create_storage(session, ref, content, context):
    LOGGER.debug(f"Preparing STORE item for {ref} on height {context['height']}")
    store = await create_store(
        get_aleph_account(),
        file_content=io.StringIO(content),
        storage_engine="ipfs",
        channel=settings.aleph_channel,
        api_server=settings.aleph_api_server,
        extra_fields={
            'ref': ref,
            **context
        })
    print(store["content"]["item_hash"], ref)
    assert store["content"]["item_hash"] == ref
    return store
