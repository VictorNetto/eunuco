import asyncio
import websockets
import datetime
import json

async def send_periodic_updates(websocket):
    """Task to send a message every 3 seconds."""
    try:
        while True:
            now = datetime.datetime.now().strftime("%H:%M:%S")
            payload = {"type": "timer", "content": f"Server time: {now}"}
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(3) # Wait for 3 seconds
    except websockets.ConnectionClosed:
        pass

async def listen_for_messages(websocket):
    """Task to handle incoming messages from JS."""
    try:
        async for message in websocket:
            data = json.loads(message)
            print(f"Received from JS: {data}")
            # Optional: Echo back a confirmation
            await websocket.send(json.dumps({"type": "echo", "content": "Got it!"}))
    except websockets.ConnectionClosed:
        print("Connection closed")

async def handler(websocket):
    # Run both tasks concurrently
    # gather() starts them both and manages them on the same connection
    await asyncio.gather(
        send_periodic_updates(websocket),
        listen_for_messages(websocket)
    )

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("Server active. Sending updates every 3s...")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

# import asyncio
# import websockets
# import json
# import random

# async def handler(websocket):
#     print("Client connected")
    
#     # Example data to cycle through
#     mockData = [
#         {
#             "url": "bb.com.br",
#             "method": "GET",
#             "originalResponse": """{"city":{"code":"brasilia","name":"Bras\u00edlia"},"country":{"code":["a","b","c","D"],"name":"Brazil","pt":"Brasil","ptSlug":"brasil"},"extra":{"city_uri":"http://semantica.globo.com/base/Cidade_Brasilia_DF","region_name":"Distrito Federal","region_news_path":"df/distrito-federal"},"ip":"100.80.14.130","latitude":-15.7798,"longitude":-47.9331,"semantic":{"city":"brasilia","region":"distrito-federal","state":"df","uri":"http://semantica.globo.com/base/Cidade_Brasilia_DF"},"state":{"code":"DF","name":"Federal District"}}""",
#             "replayResponse": """{"city":{"code":"paris","name":"Bras\u00edlia"},"country":{"code":["a","b","c","D"],"name":"Brazil","pt":"Brasil","ptSlug":"brasil"},"extra":{"city_uri":"http://semantica.globo.com/base/Cidade_Brasilia_DF","region_name":"Distrito Federal","region_news_path":"df/distrito-federal"},"ip":"100.80.14.130","latitude":-15.7798,"longitude":-47.9331,"semantic":{"city":"brasilia","region":"distrito-federal","state":"df","uri":"http://semantica.globo.com/base/Cidade_Brasilia_DF"},"state":{"code":"DF","name":"Federal District"}}""",
#         },

#         {
#             "url": "bb.com.br",
#             "method": "POST",
#             "originalResponse": """{"city":{"code":"paris","name":"Bras\u00edlia"},"country":{"code":["a","b","c","D"],"name":"Brazil","pt":"Brasil","ptSlug":"brasil"},"extra":{"city_uri":"http://semantica.globo.com/base/Cidade_Brasilia_DF","region_name":"Distrito Federal","region_news_path":"df/distrito-federal"},"ip":"100.80.14.130","latitude":-15.7798,"longitude":-47.9331,"semantic":{"city":"brasilia","region":"distrito-federal","state":"df","uri":"http://semantica.globo.com/base/Cidade_Brasilia_DF"},"state":{"code":"DF","name":"Federal District"}}""",
#             "replayResponse": """{"city":{"code":"brasilia","name":"Bras\u00edlia"},"country":{"code":["a","b","c","D"],"name":"Brazil","pt":"Brasil","ptSlug":"brasil"},"extra":{"city_uri":"http://semantica.globo.com/base/Cidade_Brasilia_DF","region_name":"Distrito Federal","region_news_path":"df/distrito-federal"},"ip":"100.80.14.130","latitude":-15.7798,"longitude":-47.9331,"semantic":{"city":"brasilia","region":"distrito-federal","state":"df","uri":"http://semantica.globo.com/base/Cidade_Brasilia_DF"},"state":{"code":"DF","name":"Federal District"}}""",
#         },
#     ]
    
#     try:
#         while True:
#             # 1. Send a random domain for the sidebar
#             await websocket.send(json.dumps(random.choice(mockData)))
            
#             # Wait 3 seconds before sending the next update
#             await asyncio.sleep(3)
            
#     except websockets.exceptions.ConnectionClosed:
#         print("Client disconnected")

# async def main():
#     async with websockets.serve(handler, "localhost", 8765):
#         print("Server started on ws://localhost:8765")
#         await asyncio.Future() # Run forever

# if __name__ == "__main__":
#     asyncio.run(main())