from aiohttp import web
import asyncio
import random
from os import environ
import socket
import requests

clock = 0
clock_lock = asyncio.Lock()

def log_clock():
    '''
    Logs current clock to show events.
    '''
    # Print out current clock
    with clock_lock:
        global clock
        print(f"Current time is: {clock}")

    # Send to logger pod somehow


async def get_ip_list():
    own_ip = environ['POD_IP']
    ip_set = set()

    try:
        response = socket.getaddrinfo("bully-service-internal",0,0,0,0)
    except:
        print("Got exception during DNS lookup")
        return None
    
    for result in response:
        ip_set.add(result[-1][0])
    
    # Remove own POD ip from the set of pods ip's
    try: 
        ip_set.remove(own_ip)
    except ValueError:
        print("Own ip not in set")
    
    return list(ip_set)


async def event_counter():
    '''
    Process that randomly advances clock to simulate events.
    '''
    event_amount = 10
    for _ in event_amount:
        asyncio.sleep(random.randint(10, 20))
        # Advance clock
        async with clock_lock:
            global clock
            clock += 1

            # 1/3 chance of sending to random pod
            if random.randint(1, 3) == 1:
                pod_port = environ['WEB_PORT']
                ip_list = get_ip_list()
                target_ip = random.choice(ip_list)

                url = 'http://' + target_ip + ':' + pod_port + '/request'

                response = await requests.post(url, json={"time": str(clock)})
                print(f"Sent time: {clock}")
                
        log_clock()
        
            


async def recieve_message(request):
    '''
    Handles POST requests with Lamport timestamp.
    '''
    
    data = await request.json()
    
    try:
        recieved_time = data['time']
    except:
        return web.Response(text="Bad input", status=400)

    async with clock_lock:
        global clock
        clock = max(clock, recieved_time) + 1

    log_clock()

    return web.Response(text="OK", status=200)


async def background_tasks():
    # task0 = asyncio.create_task(message_sender())
    task1 = asyncio.create_task(event_counter())
    yield
    # task0.cancel()
    task1.cancel()
    # await task0
    await task1

if __name__ == '__main__':
    app = web.Application()
    app.router.add_post('/request', recieve_message)
    app.cleanup_ctx.append(background_tasks)
    web.run_app(app, host='0.0.0.0', port=8080)