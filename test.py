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

# Global variable to store container limits from API
containers_limits = []

# Define limit parameters
block_limit = 80.0  # Block usage limit in percentage
network_limit = 1000.0  # Network usage limit in MB
cpu_limit = 80.0  # CPU usage limit in percentage
memory_limit = 80.0  # Memory usage limit in percentage


# Function to get the machine's IP address
def get_ip():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

# Function to parse memory usage
def parse_memory_usage(memory_string):
    match = re.match(r'([\d.]+)([KMGTPEZY]iB) / ([\d.]+)([KMGTPEZY]iB)', memory_string)
    if match:
        size, unit, limit_size, limit_unit = match.groups()
        size = float(size)
        limit_size = float(limit_size)
        # Convert both sizes to the same unit (bytes) for comparison
        unit_multipliers = {
            'KiB': 2**10, 'MiB': 2**20, 'GiB': 2**30, 'TiB': 2**40,
            'PiB': 2**50, 'EiB': 2**60, 'ZiB': 2**70, 'YiB': 2**80
        }
        size_bytes = size * unit_multipliers[unit]
        limit_bytes = limit_size * unit_multipliers[limit_unit]
        return {
            "size_bytes": size_bytes,
            "limit_bytes": limit_bytes
        }
    else:
        return {"size_bytes": 0, "limit_bytes": 1}  # Fallback to avoid division by zero


def fetch_container_limits():
    global containers_limits
    ip_address = get_ip()
    url = "http://192.168.0.115:8000/getAgentContainers"  # Replace with your actual API endpoint
    try:
        payload = {"ip_address": ip_address}
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            containers_limits = response.json()
            print("Fetched container limits successfully")
        else:
            print("Failed to fetch container limits, status code:", response.status_code)
    except requests.RequestException as e:
        print("An error occurred while fetching container limits:", str(e))

# Call fetch_container_limits initially and set it to refresh periodically
fetch_container_limits()
threading.Timer(300, fetch_container_limits).start()  # Refresh every 5 minutes

def check_limits(container_stats):
    alerts = []
    container_id = container_stats["CONTAINER ID"]
    container = next((c for c in containers_limits if c['id'] == container_id), None)

    if not container:
        return alerts  # No matching container found

    # Check CPU limit
    cpu_usage = float(container_stats["CPU %"].rstrip('%'))
    if cpu_usage > container['cpu_limit']:
        alerts.append(f"CPU usage for {container_stats['NAME']} exceeds limit: {cpu_usage}% > {container['cpu_limit']}%")
    
    # Check memory limit
    memory_usage = float(container_stats["MEM USAGE"]["size_bytes"])
    memory_limit_value = float(container_stats["MEM USAGE"]["limit_bytes"])
    memory_usage_percent = (memory_usage / memory_limit_value) * 100
    if memory_usage_percent > container['mem_limit']:
        alerts.append(f"Memory usage for {container_stats['NAME']} exceeds limit: {memory_usage_percent}% > {container['mem_limit']}%")
    
    # Check network limit
    net_input = float(container_stats["NET INPUT"].rstrip('B'))
    net_output = float(container_stats["NET OUTPUT"].rstrip('B'))
    if net_input > container['net_limit'] * (1024 ** 2) or net_output > container['net_limit'] * (1024 ** 2):
        alerts.append(f"Network usage for {container_stats['NAME']} exceeds limit: {net_input}MB or {net_output}MB > {container['net_limit']}MB")
    
    # Check block (disk) limit
    block_input = float(container_stats["BLOCK INPUT"].rstrip('B'))
    block_output = float(container_stats["BLOCK OUTPUT"].rstrip('B'))
    if block_input > container['disk_limit'] * (1024 ** 2) or block_output > container['disk_limit'] * (1024 ** 2):
        alerts.append(f"Block usage for {container_stats['NAME']} exceeds limit: {block_input}MB or {block_output}MB > {container['disk_limit']}MB")

    return alerts

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

 # Fetch container limits initially and set to refresh periodically
    fetch_container_limits()
    threading.Timer(300, fetch_container_limits).start()  # Refresh every 5 minutes

    # Start WebSocket server to listen for messages from Flutter and send docker stats
    ip_address = get_ip()
    port = 8765

    start_server = websockets.serve(handle_websocket, ip_address, port)

    print(f"Starting WebSocket server on {ip_address}:{port}")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.create_task(send_docker_stats())  # Ensure this line is uncommented and corrected
    loop.run_forever()
