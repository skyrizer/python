import requests
import json
import subprocess
import time
import re
import mysql.connector


def get_node_id_from_database(hostname):
    # Connect to your MySQL database
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="Wafir@020304",
        database="containsafe"
    )

    # Create a cursor object
    cur = conn.cursor()

    try:
        # Execute a SELECT query to retrieve the node ID based on hostname
        cur.execute("SELECT id FROM nodes WHERE hostname = %s", (hostname,))
        node_id = cur.fetchone()[0]  # Fetch the node ID
        return node_id
    except Exception as e:
        print("Error fetching node ID from database:", str(e))
    finally:
        # Close the cursor and connection
        cur.close()
        conn.close()

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

if __name__ == "__main__":

      # Get the hostname of the current node
    hostname = subprocess.check_output(['hostname']).strip().decode("utf-8")

    # Get the node ID from the database based on the hostname
    node_id = get_node_id_from_database(hostname)

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