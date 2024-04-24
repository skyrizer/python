import requests
import json
import subprocess
import time
import re

def parse_memory_usage(memory_string):
    # Parsing memory string like "8.281MiB / 7.65GiB" into a dictionary
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
        # If the memory string does not match the expected format, return it as is
        return memory_string


def parse_docker_stats(output):
    stats = []
    lines = output.strip().split('\n')
    header = lines[0].split()
    for line in lines[1:]:
        values = line.split()
        container_stats = {}
        container_stats["CONTAINER ID"] = values[0]
        container_stats["NAME"] = values[1]
        container_stats["CPU %"] = values[2]
        container_stats["MEM USAGE"] = parse_memory_usage(values[3])
        container_stats["MEM SIZE"] = values[5]
        container_stats["NET INPUT"] = values[7]
        container_stats["NET OUTPUT"] = values[9]
        container_stats["BLOCK INPUT"] = values[10]
        container_stats["BLOCK OUTPUT"] = values[12]
        container_stats["PIDS"] = str(values[13])
        stats.append(container_stats)
    return stats


def send_http_request():
    url = "http://127.0.0.1:8000/agent"
    
    while True:
        try:
            # Execute the docker stats command and capture its output
            performance_output = subprocess.check_output(['docker', 'stats', '--no-stream']).decode('utf-8')
            
            # Parse the output of docker stats command
            parsed_stats = parse_docker_stats(performance_output)
            print(parsed_stats)
            
            # Create payload with the parsed stats
            payload = {"performance": parsed_stats}
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

        time.sleep(5)  # Wait for 5 seconds before sending the next request

if __name__ == "__main__":
    send_http_request()
