import time
import sys
import requests

class Worker:
    def __init__(self, node_public_ip):
        self.node_public_ip = node_public_ip

    def DoWork(self, t):
        # Perform the actual work here
        print(t)
        return t
        pass

    def loop(self):
        nodes = [f'http://{self.node_public_ip}:5000']  # Replace with the actual URL of the Flask app node
        lastTime = time.time()
        while time.time() - lastTime <= 20:  # 10 minutes in seconds
            for node in nodes:
                print(nodes[0])
                work = self.get_work(node)
                print(work)
            #     if work is not None:
            #         result = self.DoWork(work)
            #         self.complete_work(node, result)
            #         lastTime = time.time()
            #         continue
            # time.sleep(100)
        # parent.WorkerDone()  # Replace with the appropriate function call

    @staticmethod
    def get_work(node_url):
        try:
            print(f"{node_url}/giveMeWork")
            response = requests.post(f"{node_url}/giveMeWork")
            print("response: ", response)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.exceptions.RequestException:
            print("error")
            return None

    @staticmethod
    def complete_work(node_url, result):
        try:
            response = requests.post(f"{node_url}/workComplete", json=result)
            if response.status_code == 200:
                return True
            else:
                return False
        except requests.exceptions.RequestException:
            return False

node_public_ip = sys.argv[1]
worker = Worker(node_public_ip=node_public_ip)  # Replace <node-public-ip> with the actual IP address
worker.loop()
