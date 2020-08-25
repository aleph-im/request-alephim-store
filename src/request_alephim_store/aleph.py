    
from aleph_client.main import create_post, get_posts
from aleph_client.chains.ethereum import ETHAccount
from functools import lru_cache

from .settings import settings

@alru_cache(maxsize=32)
async def get_aleph_account():
    return ETHAccount(settings.ethereum_pkey)


@alru_cache(maxsize=32)
async def get_aleph_address():
    return (await get_aleph_account()).get_address()


async def create_storage_event_post(height, args):
    LOGGER.debug(f"Preparing pending TX post {metadata}")
    post = await create_post(
        await get_aleph_account(),
        {'symbol': settings.token_symbol,
         'source': metadata['source'],
         'target': metadata['target'],
         'status': status},
        post_type='xchain-swap',
        ref=txhash,
        channel=settings.aleph_channel,
        api_server=settings.aleph_api_server)
    await asyncio.sleep(1)