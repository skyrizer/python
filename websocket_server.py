import asyncio
import websockets
import socket

connected_clients = set()

async def echo(websocket, path):
    # Register client
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print(f"Received message: {message}")
            # Check if the received message is "ping"
            if message == "ping":
                # Reply with "pong"
                await websocket.send("pong")
            else:
                # Echo the message back to all connected clients
                for client in connected_clients:
                    if client != websocket:
                        await client.send(message)
    finally:
        # Unregister client
        connected_clients.remove(websocket)

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
