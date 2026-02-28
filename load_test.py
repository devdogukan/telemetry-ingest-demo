import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor

URL = "http://127.0.0.1:5000/api/telemetry"
NUM_REQUESTS = 5000
CONCURRENCY = 50

def send_request(i):
    data = {"sensor_id": f"room_{i}", "temperature": random.random()*100}
    start = time.time()
    r = requests.post(URL, json=data)
    latency = time.time() - start
    return latency, r.status_code

latencies = []

with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    futures = [executor.submit(send_request, i) for i in range(NUM_REQUESTS)]
    for f in futures:
        lat, code = f.result()
        latencies.append(lat)

print("Average latency:", sum(latencies)/len(latencies))
print("Max latency:", max(latencies))