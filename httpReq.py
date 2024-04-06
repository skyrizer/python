import requests
import json
import subprocess

def send_http_request():
    url = "http://127.0.0.1:8000/date"
    
    # Execute the ipconfig command and capture its output
    ipconfig_output = subprocess.check_output(['ipconfig']).decode('utf-8')
    
    # Create payload with the ipconfig output
    payload = {"ipconfig_output": ipconfig_output}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        if response.status_code == 200:
            print("HTTP request sent successfully")
        else:
            print("HTTP request failed with status code:", response.status_code)
    except Exception as e:
        print("An error occurred while sending HTTP request:", str(e))

if __name__ == "__main__":
    send_http_request()
