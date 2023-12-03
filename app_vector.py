from aiohttp import web
import asyncio
import random
from os import environ
import socket
import httpx

import json


clock = {environ['POD_IP']: 0}
clock_lock = asyncio.Lock()

async def log_clock():
    '''
    Logs current clock to show events.
    '''
    # Print out current clock
    async with clock_lock:
        global clock

        # Before printing replace the key of own ip with "own"
        clocks_with_own = clock.copy()
        clocks_with_own["own"] = clocks_with_own.pop(environ['POD_IP'])

        print(f"Current time is: {clocks_with_own}")

async def get_ip_list():
    print("Getting ip list")
    own_ip = environ['POD_IP']
    ip_set = set()

    try:
        response = socket.getaddrinfo("synchro-service-internal",0,0,0,0)
    except:
        print("Got exception during DNS lookup")
        return None
    
    print(f"DNS response: {response}")

    for result in response:
        ip_set.add(result[-1][0])

    print(f"IP set is: {ip_set}")

    
    
    # Remove own POD ip from the set of pods ip's
    try: 
        ip_set.remove(own_ip)            
    except ValueError:
        print("Own ip not in set.")
    except:
        print("Unknown exception when removing own IP.")
    
    return list(ip_set)


async def event_counter():
    '''
    Process that randomly advances clock to simulate events.
    '''
    print("Starting background task")
    event_amount = 10
    for _ in range(event_amount):
        await asyncio.sleep(random.randint(10, 20))
        print("Event happening")
        # Advance clock
        async with clock_lock:
            global clock
            clock[environ['POD_IP']] += 1

            # 1/3 chance of sending to random pod
            if (random.random() < 0.3):
                print("Sending message to random pod")
                pod_port = environ['WEB_PORT']
                ip_list = await get_ip_list()

                

                target_ip = random.choice(ip_list)

                url = 'http://' + target_ip + ':' + pod_port + '/request'

                print(f"Sending to: {url}")

                async with httpx.AsyncClient() as client:
                    serialized_dict = json.dumps(clock)
                    response = await client.post(url, json=serialized_dict)
                    print(f"Sent time: {clock} with response {response}")
                
        await log_clock()
        
            


async def recieve_message(request):
    '''
    Handles POST requests with Lamport timestamp.
    '''
    
    data = await request.json()

    print(f"Got data: {data}")
    

    try:
        recieved_vector_clock = json.loads(data) # Create recieved clock dictionary
    except:
        return web.Response(text="Bad input", status=400)

    # Check if recieved vector clock contains new keys compared to own
    async with clock_lock: 
        global clock
        for key, val in recieved_vector_clock.items():
            if key in clock.keys():
                clock[key] = max(clock[key], val)
            clock[key] = val
        clock[environ['POD_IP']] += 1
    # .....
            
    await log_clock()

    return web.Response(text="OK", status=200)


async def background_tasks(app):
    task1 = asyncio.create_task(event_counter())
    yield
    task1.cancel()
    await task1

if __name__ == '__main__':
    app = web.Application()
    app.router.add_post('/request', recieve_message)
    app.cleanup_ctx.append(background_tasks)
    web.run_app(app, host='0.0.0.0', port=8080)