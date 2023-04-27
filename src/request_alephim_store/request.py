import aiohttp
import asyncio
from asyncio import TimeoutError, gather

from .ethereum import process_storage_history
from .aleph import get_previous_stored, create_storage
from aleph_client.asynchronous import ipfs_push_file
from .settings import settings
import io

import logging
LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=1)

ALREADY_HANDLED = set()

async def get_cid_content(session, cid):
    try:
        async with session.get("{}/ipfs/{}".format(
                settings.ipfs_request_gateway, cid)) as response:
            return await response.text()
    except TimeoutError:
        return None
    

async def handle_cid(session, context, cid):
    previous = await get_previous_stored(session, cid)
    if previous is None:
        cid_content = await get_cid_content(session, cid)
        if cid_content is not None:
            LOGGER.debug("{}:{}/{} bytes".format(context["height"],
                                                 cid, len(cid_content)))
        else:
            LOGGER.warning("{}:{} ERROR".format(context["height"], cid))
            return
        # await ipfs_push_file(io.StringIO(cid_content),
        #                      api_server=settings.aleph_api_server)
        await create_storage(content=cid_content, context=context, ref=f"request-{cid}")
    else:
        ALREADY_HANDLED.add(cid)
        LOGGER.debug("{} Already handled".format(context["height"]))


async def process_history(start_height=0):
    i = 0
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        while True:
            try:
                tasks = list()
                async for context, cid in process_storage_history(
                        start_height=start_height):
                    i += 1
                    if cid not in ALREADY_HANDLED:
                        tasks.append(handle_cid(session, context, cid))
                    
                    if not i % 10:
                        await gather(*tasks)
                        tasks = []
                    
                await gather(*tasks)
                
            except Exception:
                LOGGER.exception("Error handling hashes, retrying")
            
            await asyncio.sleep(60)
