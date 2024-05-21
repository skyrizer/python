import requests
import json
import subprocess
import time
import re
import threading
import asyncio
import websockets
import socket

# Global variable to store sleep duration
sleep_duration = 10
email = ""
docker_stats = []

connected_clients = set()

# Define limit parameters
disk_limit = 80.0  # Disk usage limit in percentage
network_limit = 1000.0  # Network usage limit in MB
cpu_limit = 80.0  # CPU usage limit in percentage
memory_limit = 80.0  # Memory usage limit in percentage

# Function to parse memory usage
def parse_memory_usage(memory_string):
    match = re.match(r'([\d.]+)([KMGTPEZY])iB / ([\d.]+)([KMGTPEZY])iB', memory_string)
    if match:
        size, unit, limit_size, limit_unit = match.groups()
        return {
            "size": str(size),
            "unit": str(unit),
            "limit_size": str(limit_size) if limit_size != 'GiB' else limit_size,
            "limit_unit": str(limit_unit)
        }
    else:
        return memory_string

# Function to parse docker stats
def parse_docker_stats(output):
    stats = []
    lines = output.strip().split('\n')
    header = lines[0].split()
    for line in lines[1:]:
        values = line.split()
        container_stats = {
            "CONTAINER ID": values[0],
            "NAME": values[1],
            "CPU %": values[2],
            "MEM USAGE": parse_memory_usage(values[3]),
            "MEM SIZE": values[5],
            "NET INPUT": values[7],
            "NET OUTPUT": values[9],
            "BLOCK INPUT": values[10],
            "BLOCK OUTPUT": values[12],
            "PIDS": str(values[13])
        }
        stats.append(container_stats)
    return stats

# Function to collect docker stats
def extract_docker_stats():
    while True:
        try:
            performance_output = subprocess.check_output(['docker', 'stats', '--no-stream']).decode('utf-8')
            parsed_stats = parse_docker_stats(performance_output)
            global docker_stats
            docker_stats = parsed_stats
        except subprocess.CalledProcessError as e:
            print("Error executing 'docker stats' command:", str(e))
        except Exception as e:
            print("An unexpected error occurred:", str(e))

        time.sleep(1)

# Function to send HTTP request
def send_http_request():
    url = "http://127.0.0.1:8000/agent"
    while True:
        try:
            payload = {"performance": docker_stats}
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                print("HTTP request sent successfully")
            else:
                print("HTTP request failed with status code:", response.status_code)
        except requests.RequestException as e:
            print("An error occurred while sending HTTP request:", str(e))
        except Exception as e:
            print("An unexpected error occurred:", str(e))

        time.sleep(15)

# Function to get the machine's IP address
def get_ip():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

# Function to handle WebSocket connections and messages
async def handle_websocket(websocket, path):
    global sleep_duration
    global email
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            #print(f"Received message: {message}")
            if message == "ping":
                # Reply with "pong"
                await websocket.send("pong")
            else:
                try:
                    data = json.loads(message)
                    print(data)
                    if "sleep_duration" in data:
                        new_duration = int(data["sleep_duration"])
                        sleep_duration = new_duration
                        print(email)
                        print(f"Updated sleep duration to: {sleep_duration}")
                    elif "email" in data:
                        new_email = data["email"]
                        email = new_email
                        print(f"Updated email as: {email}")

                    else:
                        # Echo the message to other connected clients
                        for client in connected_clients.copy():
                            if client != websocket:
                                await client.send(message)
                except ValueError as e:
                    print(f"Invalid message format: {e}")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed with error: {e}")
    except websockets.exceptions.ConnectionClosedOK:
        print(f"Connection closed normally.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        connected_clients.remove(websocket)

# Function to send docker stats to connected clients
async def send_docker_stats():
    while True:
        if docker_stats:
            data = json.dumps({"performance": docker_stats})
            for client in connected_clients.copy():
                try:
                    await client.send(data)
                    print(f"Sent: {data}")
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"Error sending data: {e}")
        await asyncio.sleep(sleep_duration)  # Use the shared sleep duration variable

if __name__ == "__main__":
    # Start threads for collecting docker stats and sending HTTP requests
    extract_thread = threading.Thread(target=extract_docker_stats)
    send_http_thread = threading.Thread(target=send_http_request)
    
    extract_thread.start()
    send_http_thread.start()

    # Start WebSocket server to listen for messages from Flutter and send docker stats
    ip_address = get_ip()
    port = 8765

    start_server = websockets.serve(handle_websocket, ip_address, port)

    print(f"Starting WebSocket server on {ip_address}:{port}")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.create_task(send_docker_stats())  # Ensure this line is uncommented and corrected
    loop.run_forever()
