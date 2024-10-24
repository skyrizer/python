import requests
import json
import subprocess
import time
import re
import threading
import asyncio
import websockets
import socket
import psutil
import os
import platform
from datetime import datetime
from daemonize import Daemonize
import signal
import sys

PID = "/var/run/contain_safe.pid"
server_ip = "http://128.199.194.23:8000"

# Global variable to store sleep duration
sleep_duration = 10
email = ""
docker_stats = []

connected_clients = set()

# Global variable to store container limits from API
containers_limits = []
node_services = []

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

def get_node_id():
    # Define the URL of your Laravel endpoint

    url = f"{server_ip}/getNodeId"  # This appends the path to the server_ip


    # Define the data to send with the request
    data = {
        'ip_address': get_ip()
    }

    try:
        # Make an HTTP POST request to the Laravel API
        response = requests.get(url, json=data)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response to get the node ID
            node_id = response.json().get('node_id')
            return node_id
        else:
            print("Failed to fetch node ID. Status code:", response.status_code)
    except Exception as e:
        print("Error making HTTP request to Laravel:", str(e))

    return None

def parse_docker_containers(output):
    containers = []
    lines = output.strip().split('\n')
    header = lines[0].split()
    for line in lines[0:]:
        values = line.split()
        container = {}
        container["CONTAINER ID"] = values[0]
        container["NAME"] = values[2]
        container["IMAGE"] = values[4]
        container["CREATED"] = values[6]
        container["STATUS"] = values[13]
        container["PORT"] = values[11]
        containers.append(container)
    return containers

def store_containers(node_id, containers):
    url = f"{server_ip}/storeContainers"
    try:
        # Create payload with the parsed stats and node ID
        payload = {"node_id": node_id, "containers": containers}
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

async def extract_docker_containers(ip_address):

    node_id = get_node_id()

    if node_id:
        # Define the format string for docker ps
        format_string = "{{.ID}} | {{.Names}} | {{.Image}} | {{.CreatedAt}} | {{.Ports}} | {{.Status}}"

        try:
            # Run the docker ps command with the format string
            containers_output = subprocess.check_output(['docker', 'ps', '-a', '--format', format_string]).decode('utf-8')

            # Parse the output of docker ps command
            parsed_containers = parse_docker_containers(containers_output)

            # Send HTTP request with node ID and container information
            store_containers(node_id, parsed_containers)
        except subprocess.CalledProcessError as e:
            print("Error executing 'docker ps' command:", str(e))
    else:
        print("Node ID not found for IP address:", ip_address)
        
    time.sleep(sleep_duration)



def parse_memory_usage2(memory_str):
    try:
        # Remove any non-numeric characters except '.'
        value_str = ''.join(c for c in memory_str if c.isdigit() or c == '.')
        # Convert to float
        value = float(value_str)
        
        # Handle units (assuming memory_str ends with 'MiB', 'GiB', 'kB', etc.)
        if 'GiB' in memory_str:
            value *= 1024  # Convert GiB to MiB
        elif 'kB' in memory_str:
            value /= 1024  # Convert kB to MiB
        elif 'MB' in memory_str:
            value *= 1  # Already in MiB, no conversion needed

        return value
    except Exception as e:
        print(f"Error parsing memory usage: {e}")
        return 0  # or some default value if parsing fails


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
    
def parse_usage(usage_str):
    try:
        # Remove non-numeric characters except for '.'
        value_str = ''.join(c for c in usage_str if c.isdigit() or c == '.')
        value = float(value_str)
        
        # Handle units (assuming usage_str ends with 'MB', 'GB', etc.)
        if 'GiB' in usage_str:
            value *= 1024  # Convert GiB to MB
        elif 'kB' in usage_str:
            value /= 1024  # Convert kB to MB
        elif 'MB' in usage_str:
            value *= 1  # Already in MB, no conversion needed
        
        return value
    except Exception as e:
        print(f"Error parsing usage: {e}")
        return 0  # or some default value if parsing fails


def fetch_container_limits():
    global containers_limits
    ip_address = get_ip()
    url = f"{server_ip}/getAgentContainers"  # Replace with your actual API endpoint
    try:
        payload = {"ip_address": ip_address}
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            containers_limits = data.get('containers', [])  # Extract the list from the response
            #print("API Response:", data) 
            print("Fetched container limits successfully")
        else:
            print("Failed to fetch container limits, status code:", response.status_code)
    except requests.RequestException as e:
        print("An error occurred while fetching container limits:", str(e))

# Call fetch_container_limits initially and set it to refresh periodically
fetch_container_limits()
threading.Timer(300, fetch_container_limits).start()  # Refresh every 5 minutes

# fetch services for node
def fetch_node_services():
    global node_services
    ip_address = get_ip()
    url = f"{server_ip}/getServicesByNode"  # Replace with your actual API endpoint
    try:
        payload = {"ip_address": ip_address}
        headers = {"Content-Type": "application/json"}
        response = requests.get(url, json=payload, headers=headers)
        if response.status_code == 200:
            node_services = response.json().get('nodeServices', [])
            print("Fetched node services successfully")
        else:
            print("Failed to fetch node services, status code:", response.status_code)
    except requests.RequestException as e:
        print("An error occurred while fetching node services:", str(e))

# Call fetch_node_services initially and set it to refresh periodically
fetch_node_services()
threading.Timer(5, fetch_node_services).start()  # Refresh every 5 minutes

def check_limits(container_stats):
    try:
        container_id = container_stats.get("CONTAINER ID")
        container_name = container_stats.get("NAME")
        if not container_id:
            print("No container ID found in container_stats")
            return

        if not isinstance(containers_limits, list):
            print("Error: containers_limits is not a list")
            return
        
        container = next((c for c in containers_limits if c['id'] == container_id), None)
        if not container:
            print("No matching container found")
            return

        # Check CPU limit
        try:
            cpu_usage = float(container_stats.get("CPU %", '0').rstrip('%'))
            print("CPU Usage:", cpu_usage)
            if cpu_usage > container['cpu_limit']:
                alert_message = f"CPU usage for {container_stats.get('NAME', 'unknown')} exceeds threshold: {cpu_usage}% > {container['cpu_limit']}%"
                print("Alert:", alert_message)
                alert_notification(alert_message)
        except ValueError:
            print("Error parsing CPU usage")

        # Check memory limit
        try:
            memory_usage = parse_memory_usage2(container_stats.get("MEM USAGE", '0'))
            memory_limit_value = parse_memory_usage2(container_stats.get("MEM SIZE", '0'))
            memory_usage_percent = (memory_usage / memory_limit_value) * 100 if memory_limit_value > 0 else 0
            if memory_usage_percent > container['mem_limit']:
                alert_message = f"Memory usage for {container_stats.get('NAME', 'unknown')} exceeds threshold: {memory_usage_percent}% > {container['mem_limit']}%"
                print("Alert:", alert_message)
                alert_notification(alert_message)
        except Exception as e:
            print("Error parsing memory usage:", e)

        # Check network limit
        try:
            net_input = parse_usage(container_stats.get("NET INPUT", '0'))
            net_output = parse_usage(container_stats.get("NET OUTPUT", '0'))
            print("Network Input:", net_input)
            print("Network Output:", net_output)
            if net_input > container['net_limit'] or net_output > container['net_limit']:
                alert_message = f"Network usage for {container_stats.get('NAME', 'unknown')} exceeds threshold: {net_input}MB or {net_output}MB > {container['net_limit']}MB"
                print("Alert:", alert_message)
                alert_notification(alert_message)
        except Exception as e:
            print("Error parsing network usage:", e)

        # Check block (disk) limit
        try:
            block_input = parse_usage(container_stats.get("BLOCK INPUT", '0'))
            block_output = parse_usage(container_stats.get("BLOCK OUTPUT", '0'))
            print("Block Input:", block_input)
            print("Block Output:", block_output)
            if block_input > container['disk_limit'] or block_output > container['disk_limit']:
                alert_message = f"Block usage for {container_stats.get('NAME', 'unknown')} exceeds threshold: {block_input}MB or {block_output}MB > {container['disk_limit']}MB"
                print("Alert:", alert_message)
                alert_notification(alert_message)
        except Exception as e:
            print("Error parsing block usage:", e)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")



# Function to parse docker stats
def parse_docker_stats(output):
    stats = []
    lines = output.strip().split('\n')
    header = lines[0].split()
    
    # Get the current timestamp
    timestamp = datetime.utcnow().isoformat()

    for line in lines[1:]:
        values = line.split()
        container_stats = {
            "TIMESTAMP": timestamp,
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

            for container_stats in docker_stats:
                check_limits(container_stats)

        except subprocess.CalledProcessError as e:
            print("Error executing 'docker stats' command:", str(e))
        except Exception as e:
            print("An unexpected error occurred:", str(e))

        time.sleep(1)

# Function to send HTTP request
def send_http_request():
    url = f"{server_ip}/agent"
    while True:
        try:
            payload = {"performance": docker_stats}
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                print("HTTP request sent successfully")
            else:
                print(docker_stats)
                print("HTTP request failed with status code:", response.status_code)
        except requests.RequestException as e:
            print("An error occurred while sending HTTP request:", str(e))
        except Exception as e:
            print("An unexpected error occurred:", str(e))

        time.sleep(15)


def alert_notification(message):

    url = "https://onesignal.com/api/v1/notifications"
    payload = {
        "app_id": "2c9ce8b1-a075-4864-83a3-009c8497310e",
        "include_external_user_ids": [email],
        "contents": {
            "en": message
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic MTI3ZjcwYjktNGJiMy00YWViLTljMmQtYjMwNDI5NzBkMjRk"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print("HTTP request sent successfully")
        else:
            print("HTTP request failed with status code:", response.status_code)
            print("Response content:", response.text)  # Print response content for debugging
    except requests.RequestException as e:
        print("An error occurred while sending HTTP request:", str(e))
    except Exception as e:
        print("An unexpected error occurred:", str(e))

        # time.sleep(15)

# Function to get the service commands from the Laravel server
def get_service_commands(service_name):
    url = f'{server_ip}/api/service/{service_name}'
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception('Service not found')
        

# Function to identify the OS and run the related command
def run_service_command(service_name):
    service = get_service_commands(service_name)
    os_type = platform.system()

    if os_type == 'Linux':
         command = f"sudo {service['start_command_linux']}"
    elif os_type == 'Windows':
        command = service['start_command_windows']
    else:
        raise Exception('Unsupported OS')

    try:
        # Command to run as administrator
        # subprocess.run(['runas', '/user:Administrator', command], check=True, shell=True)
        subprocess.run(['powershell', '-Command', f"Start-Process cmd.exe -ArgumentList '/c {command}' -Verb RunAs"], check=True)

    except subprocess.CalledProcessError as e:
        print(f'Failed to execute command with admin privileges: {e}')



# Function to handle WebSocket connections and messages
async def handle_websocket(websocket, path):
    global sleep_duration
    global email
    global service_name
    connected_clients.add(websocket)
    try:
        async for message in websocket:
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
                    elif "service_name" in data:
                        new_service = data["service_name"]
                        service_name = new_service
                        run_service_command(service_name)
                    elif "email" in data:
                        new_email = data["email"]
                        email = new_email
                        print(f"Updated email as: {email}")
                    else:
                        # Echo the message to other connected clients
                        for client in connected_clients.copy():
                            if client != websocket:
                                await client.send(message)
                except json.JSONDecodeError as e:
                    print(f"Invalid message format: {e}")
                except Exception as e:
                    print(f"Error processing message: {e}")
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
            data = json.dumps({
                "performance": docker_stats,
            })
            for client in connected_clients.copy():
                try:
                    await client.send(data)
                    print(f"Sent docker stats: {data}")
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"Error sending docker stats: {e}")
                except Exception as e:
                    print(f"Unexpected error in send_docker_stats: {e}")
        await asyncio.sleep(sleep_duration)  # Shortened sleep for better concurrency

# Function to send service status to connected clients
async def send_service_status():
    while True:
        if node_services:
            data = json.dumps({
                "service_status": get_service_status()
            })
            for client in connected_clients.copy():
                try:
                    await client.send(data)
                    print(f"Sent service status: {data}")
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"Error sending service status: {e}")
                except Exception as e:
                    print(f"Unexpected error in send_service_status: {e}")
        await asyncio.sleep(sleep_duration)  # Shortened sleep for better concurrency

# Function to check if services are running based on background processes
def get_service_status():
    services_status = []

    # Iterate through node_services to get background processes
    for service in node_services:
        service_name = service['name']
        service_id = service['id']
        is_running = False

        background_processes = [bp['name'].lower() for bp in service['background_processes']]

        # Iterate through all running processes
        for process in psutil.process_iter(['name']):
            try:
                process_name = process.info['name'].lower()
                if process_name in background_processes:
                    is_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Append service status to the list in the desired format
        services_status.append({"id": service_id, "name": service_name, "value": is_running})

    return services_status

def periodic_task():
    while True:
        fetch_container_limits()
        fetch_node_services()
        time.sleep(5)

def start():
    def run():
         # Start threads for collecting Docker stats and sending HTTP requests
        extract_thread = threading.Thread(target=extract_docker_stats)
        send_http_thread = threading.Thread(target=send_http_request)
        periodic_task_thread = threading.Thread(target=periodic_task)

        extract_thread.start()
        send_http_thread.start()
        periodic_task_thread.start()

        # Fetch container limits initially and set to refresh periodically
        fetch_container_limits()
        threading.Timer(300, fetch_container_limits).start()  # Refresh every 5 minutes

        # Fetch node services initially and set to refresh periodically
        fetch_node_services()
        threading.Timer(300, fetch_node_services).start()  # Refresh every 5 minutes

        # Start WebSocket server to listen for messages from Flutter and send Docker stats
        ip_address = get_ip()
        port = 8765

        start_server = websockets.serve(handle_websocket, ip_address, port)

        print(f"Starting WebSocket server on {ip_address}:{port}")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_server)
        loop.create_task(send_docker_stats())  # Ensure this line is uncommented and corrected
        loop.create_task(send_service_status())  # Ensure this line is uncommented and corrected
        loop.create_task(extract_docker_containers(ip_address))  # Ensure this line is uncommented and corrected

        loop.run_forever()

    daemon = Daemonize(app="contain_safe", pid=PID, action=run,
                    foreground=False)
    daemon.start()
    print("ContainSafe started as a daemon.")



def stop():
    if os.path.exists(PID):
        with open(PID, 'r') as f:
            pid = int(f.read())
        try:
            os.kill(pid, signal.SIGTERM)  # Send termination signal
            os.remove(PID)  # Remove the PID file
            print("ContainSafe stopped.")
        except ProcessLookupError:
            print("No such process with PID:", pid)
    else:
        print("ContainSafe is not running.")

def main():
    if len(sys.argv) != 2:
        print("Usage: ./ContainSafe start|stop")
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == "start":
        start()
    elif command == "stop":
        stop()
    else:
        print("Invalid command. Use 'start' or 'stop'.")
        sys.exit(1)

if __name__ == "__main__":
    main()