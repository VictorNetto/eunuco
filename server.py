import asyncio
import json
import websockets
import datetime
import os
from typing import Dict, Any, List

from watcher import Watcher

monitor = Watcher()

async def wait_for_flow_files(dir_name: str, timeout: int = 30) -> bool:
    """
    Non-blocking check that waits for metadata.json, original_request.raw, 
    and replay_request.raw to exist within a specific flow directory.
    """
    required_files: List[str] = [
        "metadata.json",
        "original_request.raw",
        "replay_request.raw"
    ]
    
    base_path: str = os.path.join("flows", dir_name)
    start_time: float = asyncio.get_event_loop().time()

    print(f"Waiting for files in {dir_name}...")

    while True:
        # Check if all files exist
        missing_files = [
            f for f in required_files 
            if not os.path.exists(os.path.join(base_path, f))
        ]

        if not missing_files:
            print(f"All files confirmed for {dir_name}.")
            return True

        # Check for timeout
        if (asyncio.get_event_loop().time() - start_time) > timeout:
            print(f"Timeout: Files {missing_files} not found in {dir_name}.")
            return False

        # Wait 1 second before checking again (non-blocking)
        await asyncio.sleep(1)

def read_file(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return f.read().decode("utf-8")

async def process_new_flow(dir_name: str, websocket: websockets.ServerConnection) -> None:
    # 1. Wait for the files to physically exist
    success = await wait_for_flow_files(dir_name)
    
    if success:
        metadata_path = os.path.join("flows", dir_name, "metadata.json")
        original_request_path = os.path.join("flows", dir_name, "original_request.raw")
        replay_request_path = os.path.join("flows", dir_name, "replay_request.raw")
        original_response_path = os.path.join("flows", dir_name, "original_response.raw")

        metadata = None
        # 2. Try to read the file with retries to handle locks
        for _ in range(5):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                break  # Success! Exit the retry loop
            except (PermissionError, json.JSONDecodeError):
                # Wait a bit longer for the other process to finish writing
                print(f"File locked or empty, retrying {dir_name} in 1s...")
                await asyncio.sleep(1)
        
        if metadata:
            metadata["flow-name"] = dir_name
            metadata["original-request"] = read_file(original_request_path)
            metadata["replay-request"] = read_file(replay_request_path)
            metadata["original-response"] = read_file(original_response_path)
            await websocket.send(json.dumps(metadata))
        else:
            print(f"Failed to read metadata for {dir_name} after multiple attempts.")

async def directory_producer(websocket: websockets.server.ServerConnection) -> None:
    try:
        while True:
            new_dirs = monitor.watch()
            
            for dir in new_dirs:
                # We create a background task for each new folder 
                # so the 5-second loop doesn't have to wait for the files.
                asyncio.create_task(process_new_flow(dir, websocket))
            
            await asyncio.sleep(5) 
    except asyncio.CancelledError:
        pass

async def handle_message(message: str, websocket: websockets.ServerConnection) -> None:
    """
    Logic for handling incoming messages based on the 'event' field.
    """
    try:
        data: Dict[str, Any] = json.loads(message)
        event = data.get("event")

        if event == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
        elif event == "reset_watcher":
            monitor.reset()
            await websocket.send(json.dumps({"type": "status", "msg": "Watcher reset"}))
        else:
            print(f"Unknown event received: {event}")
            
    except json.JSONDecodeError:
        print("Received invalid JSON")

async def handler(websocket: websockets.ServerConnection) -> None:
    """
    Main connection handler. Manages the producer and consumer concurrently.
    """
    # Create the background directory watcher task
    producer_task = asyncio.create_task(directory_producer(websocket))
    
    try:
        # Listen for incoming messages indefinitely
        async for message in websocket:
            await handle_message(message, websocket)
    except websockets.ConnectionClosed:
        print("Client disconnected")
    finally:
        # Stop the background task when the user disconnects
        producer_task.cancel()

async def main() -> None:
    print("Starting WebSocket server on ws://localhost:8765")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.get_running_loop().create_future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())

# async def send_periodic_updates(websocket):
#     """Task to send a message every 3 seconds."""
#     try:
#         while True:
#             now = datetime.datetime.now().strftime("%H:%M:%S")
#             payload = {"type": "timer", "content": f"Server time: {now}"}
#             await websocket.send(json.dumps(payload))
#             await asyncio.sleep(10) # Wait for 3 seconds
#     except websockets.ConnectionClosed:
#         pass

# async def listen_for_messages(websocket):
#     """Task to handle incoming messages from JS."""
#     try:
#         async for message in websocket:
#             data = json.loads(message)
#             print(f"Received from JS: {data}")
#             # Optional: Echo back a confirmation
#             await websocket.send(json.dumps({"type": "echo", "content": "Got it!"}))
#     except websockets.ConnectionClosed:
#         print("Connection closed")

# async def handler(websocket):
#     # Run both tasks concurrently
#     # gather() starts them both and manages them on the same connection
#     await asyncio.gather(
#         send_periodic_updates(websocket),
#         listen_for_messages(websocket)
#     )

# async def main():
#     async with websockets.serve(handler, "localhost", 8765):
#         print("Server active. Sending updates every 3s...")
#         await asyncio.Future()

# if __name__ == "__main__":
#     asyncio.run(main())

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