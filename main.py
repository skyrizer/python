from datetime import datetime
import requests

def dateTest():
    current_time = datetime.now()
    response = requests.get('http://192.168.0.123:5001/', params={
        "string": current_time.strftime("%Y-%m-%d_%H:%M:%S"),
        "dt": datetime.isoformat(current_time)
    })
    print(response.text)  # Print server response

def main():
    print("start")
    dateTest()

main()
