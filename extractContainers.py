import requests
import json
import subprocess
import time
import re

def parse_docker_containers(output):
    containers = []
    lines = output.strip().split('\n')
    header = lines[0].split()
    for line in lines[1:]:
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

def send_http_request():
    url = "http://127.0.0.1:8000/getContainers"
    try:
        # Define the format string for docker ps
        format_string = "{{.ID}} | {{.Names}} | {{.Image}} | {{.CreatedAt}} | {{.Ports}} | {{.Status}}"

        # Run the docker ps command with the format string
        containers_output = subprocess.check_output(['docker', 'ps', '-a', '--format', format_string]).decode('utf-8')

        # Parse the output of docker stats command
        parsed_containers = parse_docker_containers(containers_output)
        print(parsed_containers)

        # Create payload with the parsed stats
        payload = {"containers": parsed_containers}
        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            print("HTTP request sent successfully")
        else:
            print("HTTP request failed with status code:", response.status_code)
    except subprocess.CalledProcessError as e:
        print("Error executing 'docker stats' command:", str(e))
    except requests.RequestException as e:
        print("An error occurred while sending HTTP request:", str(e))
    except Exception as e:
        print("An unexpected error occurred:", str(e))

if __name__ == "__main__":
    send_http_request()
