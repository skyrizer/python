import requests
import json
import subprocess
import time
import re
import mysql.connector


def get_node_id(ip_address):
    # Define the URL of your Laravel endpoint
    url = "http://127.0.0.1:8000/getNodeId"  # Replace with your actual URL

    # Define the data to send with the request
    data = {
        'ip_address': ip_address
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

def send_http_request(node_id, containers):
    url = "http://127.0.0.1:8000/storeContainers"
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

def extract_docker_containers():
    # Get the IP address of the current node
    ip_address = subprocess.check_output(["hostname", "-I"]).strip().decode("utf-8").split()[0]

    # Get the node ID from Laravel based on the IP address
    node_id = get_node_id(ip_address)

    if node_id:
        # Define the format string for docker ps
        format_string = "{{.ID}} | {{.Names}} | {{.Image}} | {{.CreatedAt}} | {{.Ports}} | {{.Status}}"

        try:
            # Run the docker ps command with the format string
            containers_output = subprocess.check_output(['docker', 'ps', '-a', '--format', format_string]).decode('utf-8')

            # Parse the output of docker ps command
            parsed_containers = parse_docker_containers(containers_output)

            # Send HTTP request with node ID and container information
            send_http_request(node_id, parsed_containers)
        except subprocess.CalledProcessError as e:
            print("Error executing 'docker ps' command:", str(e))
    else:
        print("Node ID not found for IP address:", ip_address)


if __name__ == "__main__":

      # Get the hostname of the current node
    hostname = subprocess.check_output(['hostname']).strip().decode("utf-8")

    # Get the node ID from the database based on the hostname
    node_id = get_node_id(hostname)

    if node_id:
        # Define the format string for docker ps
        format_string = "{{.ID}} | {{.Names}} | {{.Image}} | {{.CreatedAt}} | {{.Ports}} | {{.Status}}"

        try:
            # Run the docker ps command with the format string
            containers_output = subprocess.check_output(['docker', 'ps', '-a', '--format', format_string]).decode('utf-8')

            # Parse the output of docker stats command
            parsed_containers = parse_docker_containers(containers_output)

            # Send HTTP request with node ID and container information
            send_http_request(node_id, parsed_containers)
        except subprocess.CalledProcessError as e:
            print("Error executing 'docker ps' command:", str(e))
    else:
        print("Node ID not found in the database for hostname:", hostname)

    #send_http_request()