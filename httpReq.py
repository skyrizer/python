import requests
import json
import subprocess
import time
import re
import threading
import asyncio
import websockets
import socket

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

# Function to send data to WebSocket server
async def send_data():
    ip_address = get_ip()
    uri = f"ws://{ip_address}:8080"  # Use the machine's IP address
    async with websockets.connect(uri) as websocket:
        while True:
            data = json.dumps({"performance": docker_stats})
            await websocket.send(data)
            print(f"Sent: {data}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    docker_stats = []

    # Start threads for collecting docker stats and sending HTTP requests
    extract_thread = threading.Thread(target=extract_docker_stats)
    send_http_thread = threading.Thread(target=send_http_request)
    
    extract_thread.start()
    send_http_thread.start()

    # Start asyncio loop for sending data to WebSocket server
    asyncio.get_event_loop().run_until_complete(send_data())
