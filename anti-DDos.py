import time
import logging
import threading
import subprocess
from flask import Flask, request, jsonify, render_template_string
import requests
from collections import defaultdict

# Logging setup
logging.basicConfig(filename="anti_ddos.log", level=logging.INFO, format='%(asctime)s - %(message)s')

# Rate limiting setup
REQUEST_LIMIT = 100  # Max requests per minute
BLOCK_TIME = 300  # Block duration in seconds
blocked_ips = {}
ip_requests = defaultdict(list)

app = Flask(__name__)

def is_bot(ip):
    """ Check if the IP is a known bot using an external API. """
    try:
        response = requests.get(f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}", headers={
            "Key": "YOUR_API_KEY",
            "Accept": "application/json"
        })
        data = response.json()
        return data.get("data", {}).get("abuseConfidenceScore", 0) > 50  # Threshold
    except Exception as e:
        logging.error(f"Failed to check bot status: {e}")
        return False

def block_ip(ip):
    """ Block IP using Windows Firewall """
    command = f'netsh advfirewall firewall add rule name="Block {ip}" dir=in action=block remoteip={ip}'
    subprocess.run(command, shell=True)
    blocked_ips[ip] = time.time() + BLOCK_TIME
    logging.info(f"Blocked IP: {ip}")

def unblock_ip(ip):
    """ Unblock IP using Windows Firewall """
    command = f'netsh advfirewall firewall delete rule name="Block {ip}"'
    subprocess.run(command, shell=True)
    logging.info(f"Unblocked IP: {ip}")

def unblock_ips():
    """ Unblock IPs after block duration. """
    while True:
        current_time = time.time()
        for ip, unblock_time in list(blocked_ips.items()):
            if current_time > unblock_time:
                unblock_ip(ip)
                del blocked_ips[ip]
        time.sleep(60)

@app.before_request
def limit_requests():
    """ Rate limiting logic. """
    ip = request.remote_addr
    now = time.time()
    ip_requests[ip] = [t for t in ip_requests[ip] if now - t < 60]  # Keep only last minute's requests
    
    if is_bot(ip) or len(ip_requests[ip]) >= REQUEST_LIMIT:
        block_ip(ip)
        return jsonify({"error": "Too many requests, you are blocked."}), 429
    
    ip_requests[ip].append(now)

@app.route('/')
def home():
    html_content = """
    <html>
    <head>
        <title>Protected Server</title>
    </head>
    <body>
        <h1>Welcome to the protected server!</h1>
        <p>Enjoy some entertainment while you're here:</p>
        <iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ" frameborder="0" allowfullscreen></iframe>
        <br>
        <a href="https://www.crazygames.com" target="_blank">Play Games</a>
    </body>
    </html>
    """
    return render_template_string(html_content)

if __name__ == "__main__":
    threading.Thread(target=unblock_ips, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)
