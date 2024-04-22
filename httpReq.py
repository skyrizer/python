import requests
import json
import subprocess
import time

def send_http_request():
    url = "http://127.0.0.1:8000/agent"
    
    while True:
        try:
            # Execute the ipconfig command and capture its output
            performance_output = subprocess.check_output(['docker', 'stats', '--no-stream']).decode('utf-8')
            
            # Create payload with the ipconfig output
            payload = {"performance": performance_output}
            headers = {"Content-Type": "application/json"}

            response = requests.post(url, data=json.dumps(payload), headers=headers)
            
            if response.status_code == 200:
                print("HTTP request sent successfully")
            else:
                print("HTTP request failed with status code:", response.status_code)
        except subprocess.CalledProcessError as e:
            print("Error executing 'performance' command:", str(e))
        except requests.RequestException as e:
            print("An error occurred while sending HTTP request:", str(e))
        except Exception as e:
            print("An unexpected error occurred:", str(e))
        
        #time.sleep(5)  # Wait for 5 seconds before sending the next request

if __name__ == "__main__":
    send_http_request()
