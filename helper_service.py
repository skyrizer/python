from flask import Flask, request, jsonify
import subprocess
import platform

app = Flask(__name__)

def run_service_command(service_name):
    os_type = platform.system()
    if os_type == 'Linux':
        command = f"sudo {service_name}"
    elif os_type == 'Windows':
        command = service_name
    else:
        return jsonify({'error': 'Unsupported OS'}), 400

    try:
        result = subprocess.run(command, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return jsonify({'status': 'success', 'output': result.stdout.decode()}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'output': e.stderr.decode()}), 500

@app.route('/run_command', methods=['POST'])
def handle_command():
    data = request.json
    service_name = data.get('service_name')
    if not service_name:
        return jsonify({'error': 'Service name is required'}), 400
    return run_service_command(service_name)

if __name__ == '__main__':
    app.run(port=5001, debug=True)
