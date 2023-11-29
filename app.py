from aiohttp import web
import asyncio
import random
from os import environ
import socket
import httpx

clock = 0
clock_lock = asyncio.Lock()

async def log_clock():
    '''
    Logs current clock to show events.
    '''
    # Print out current clock
    async with clock_lock:
        global clock
        print(f"Current time is: {clock}")

    # Send to logger pod somehow


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
            clock += 1

            # 1/3 chance of sending to random pod
            if (random.random() < 0.3):
                print("Sending message to random pod")
                pod_port = environ['WEB_PORT']
                ip_list = await get_ip_list()
                target_ip = random.choice(ip_list)

                url = 'http://' + target_ip + ':' + pod_port + '/request'

                print(f"Sending to: {url}")

                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json={"time": str(clock)})
                    print(f"Sent time: {clock} with response {response}")
                
        await log_clock()
        
            


async def recieve_message(request):
    '''
    Handles POST requests with Lamport timestamp.
    '''
    
    data = await request.json()

    print(f"Got data: {data}")
    
    try:
        recieved_time = data['time']
    except:
        return web.Response(text="Bad input", status=400)

    async with clock_lock:
        global clock
        clock = max(clock, int(recieved_time)) + 1

    await log_clock()

    return web.Response(text="OK", status=200)


async def background_tasks(app):
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