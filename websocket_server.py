import asyncio
import websockets
import socket

async def echo(websocket, path):
    async for message in websocket:
        print(f"Received message: {message}")
        await websocket.send(f"Echo: {message}")

def get_ip():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

ip_address = get_ip()
port = 8080

start_server = websockets.serve(echo, ip_address, port)

print(f"Starting server on {ip_address}:{port}")

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()