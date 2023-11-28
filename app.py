from aiohttp import web
import asyncio
import random
from os import environ

# Wait a random amount of time
    # Increment time and send message to other pod

# Message recieved
    # Increment time to match incoming message

async get_ip_list(own_ip):


async def message_sender():
    num_of_messages = 10
    for _ in 10:
        await asyncio.sleep(random.randint(5, 20))
        ip_list = get_ip_list(environ['POD_IP'])


async def background_tasks():
    task = asyncio.create_task(message_sender())
    yield
    task.cancel()
    await task

if __name__ == '__main__':
    app = web.Application()
    app.router.add_post('/request', recieve_message)
    app.cleanup_ctx.append(background_tasks)
    web.run_app(app, host='127.0.0.1', port=8080)