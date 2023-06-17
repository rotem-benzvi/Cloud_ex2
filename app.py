from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from queue import Queue
import boto3
import paramiko
import argparse
from create_node import create_instance
import subprocess
import threading
import time
import requests

# TODO take this to different file
import json

class Work:
    def __init__(self, work_id, iterations, data, created_time):
        self.id = work_id
        self.iterations = iterations
        self.data = data
        self.created_time = created_time

    def to_json(self):
        return json.dumps({
            'id': self.id,
            'iterations': self.iterations,
            'data': self.data,
            'created_time': self.created_time
        })

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls(data['id'], data['iterations'], data['data'], data['created_time'])

class CompletedWork:
    def __init__(self, work_id, value):
        self.id = work_id
        self.value = value

    def to_json(self):
        return json.dumps({
            'id': self.id,
            'value': self.value
        })

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls(data['id'], data['value'])


app = Flask(__name__)

Name = 'DeafultName'
Kind = 'DefaultKind'

parser = argparse.ArgumentParser()
parser.add_argument('-kind', help='Specify the kind')
parser.add_argument('-name', help='Specify the name')
args = parser.parse_args()

# Access the value of the 'kind' argument
Kind = args.kind
Name = args.name

worker = None

workQueue = Queue()
workComplete = []
maxNumOfWorkers = 2
workers = []
numOfWorkers = 0
otherNodeIp = None
work_id_counter = 1

ec2_resource = boto3.resource('ec2')

otherNode = None  # Replace with the actual implementation of otherNode

@app.route('/getStatus', methods=['GET'])
def get_arguments():
    if(worker != None):
        return jsonify(worker.get_state()), 200

    serverState = {
        'name': Name,
        'kind': Kind,
        'otherNodeIp': otherNodeIp,
        'maxNumOfWorkers': maxNumOfWorkers,
        'numOfWorkers': len(workers),
        'workCompleteSize': len(workComplete),
        'workQueueSize': workQueue.qsize(),
        workComplete: workComplete,
        workQueue: list(workQueue.queue)
    }
    return jsonify(serverState), 200

@app.route('/setOtherNodeIp', methods=['POST'])
def set_other_node_ip():
    global otherNodeIp
    otherNodeIp = request.args.get('ip')
    return jsonify({'message': 'Other node IP set successfully.'}), 200

@app.route('/setParentIp', methods=['POST'])
def set_parent_ip():
    if(worker != None):
        ip = request.args.get('ip')
        worker.set_parent_ip(ip)
        return jsonify({'message': 'Other node IP set successfully.'}), 200

    return jsonify({'message': 'Worker not initialized.'}), 404

@app.route('/')
def index():
    completed_work = workComplete
    return render_template('index.html', completed_work=completed_work)


# Endpoint Node calls 

#create post request /workerDone with worker name in quesry params
@app.route('/workerDone', methods=['POST'])
def worker_done():
    #remove worker from list of workers
    worker_name = request.args.get('worker_name')
    message = "Not my worker."
    for worker in workers:
        if worker.name == worker_name:
            workers.remove(worker)
            message = "Worker " + worker_name + " removed successfully."
            break

    return jsonify({'message': message}), 200


@app.route('/giveMeWork', methods=['GET'])
def give_me_work():
    if not workQueue.empty():
        work = workQueue.get()
        return work.to_json(), 200
    else:
        return jsonify({'message': 'No work available.'}), 204

@app.route('/postCompletedWork', methods=['POST'])
def post_completed_work():
    work = CompletedWork.from_json(request.data.decode('utf-8'))
    workComplete.append(work)
    return jsonify({'message': 'Work posted successfully.'}), 200

@app.route('/enqueue', methods=['PUT'])
def enqueue_work():
    iterations = int(request.args.get('iterations'))
    data = request.data.decode('utf-8')

    global work_id_counter
    work_id = Name + str(work_id_counter) 
    work_id_counter += 1

    work = Work(work_id, iterations, data, datetime.now())

    workQueue.put(work)

    return jsonify({'work_id': work_id}), 200

@app.route('/pullCompleted', methods=['POST'])
def pull_completed():
    top = int(request.args.get('top'))
    completed_items = workComplete[-top:]
    del workComplete[-top:]
    # if len(results) < n:
    #     try:
    #         results.extend(otherNode.pullCompleteInternal(n - len(results)))
    #     except:
    #         pass
    return jsonify(completed_items), 200

# @app.route('/enqueueWork', methods=['POST'])
# def enqueue_work():
#     text = request.form['text']
#     iterations = request.form['iterations']
#     workQueue.put((text, iterations, datetime.now()))
#     return jsonify({'message': 'Work enqueued successfully.'}), 200

# @app.route('/giveMeWork', methods=['POST'])
# def give_me_work():
#     if not workQueue.empty():
#         work = workQueue.get()
#         return jsonify({'text': work[0], 'iterations': work[1]}), 200
#     else:
#         return jsonify({'message': 'No work available.'}), 204

# @app.route('/pullComplete', methods=['POST'])
# def pull_complete():
#     n = int(request.form['n'])
#     results = workComplete[:n]
#     # if len(results) < n:
#     #     try:
#     #         results.extend(otherNode.pullCompleteInternal(n - len(results)))
#     #     except:
#     #         pass
#     return jsonify(results), 200

@app.route('/spawn_worker', methods=['POST'])
def spawn_worker():
    key_name = request.args.get('keyName')
    security_group = request.args.get('securityGroup')
    node_name = "worker_456"   
    node_kind = "WorkerNode"
    print("spawn_worker: key_name = " + key_name)
    print("spawn_worker: security_group = " + security_group)
    print("spawn_worker: node_name = " + node_name)
    print("spawn_worker: node_kind = " + node_kind)

    public_ip, instance_id = create_instance(key_name, security_group, node_name, node_kind)

    workers.append(node_name)

    #TODO set worker parent ip
    #set_worker_parent_ip(public_ip)

    return jsonify({'instance_id': instance_id, 'public_ip': public_ip}), 200

@app.route('/shutdown', methods=['POST'])
def shutdown_os():
    # Execute the shutdown command
    subprocess.run(['sudo', 'shutdown', '-h', 'now'])

    # Return a response indicating that the shutdown command has been initiated
    return jsonify({'message': 'Shutdown initiated successfully.'}), 200

# TODO fix method
def timer_10_sec_describe_instances():
    if not workQueue.empty() and (datetime.now() - workQueue.queue[0][2]) > timedelta(seconds=15):
        # Implement describe_instances logic here
        instances = []
        if len(instances) < maxNumOfWorkers:
            spawn_worker()

# TODO fix method
def timer_10_sec():
    while True:
        if not workQueue.empty() and (datetime.now() - workQueue.queue[0][2]) > timedelta(seconds=15):
            if numOfWorkers < maxNumOfWorkers:
                spawn_worker()
            # else:
            #     if otherNode.TryGetNodeQuota():
            #         maxNumOfWorkers += 1

# TODO fix method
def try_get_node_quota():
    global maxNumOfWorkers
    if numOfWorkers < maxNumOfWorkers:
        maxNumOfWorkers -= 1
        return True
    return False

print("I've made it here")

#spawn_worker()

# new Code 

class WorkerNode:
    # creaete a worker node
    def __init__(self, name, parentIP=None):
        self.name = name
        self.parentIP = parentIP
        self.endpointNodesIPs = []
        if parentIP is not None:
            self.endpointNodesIPs.append(parentIP)
        self.lastWorkTime = None
        self.shouldShutdown = False


    def get_endpoint_nodes_ips_from_AWS(self):
        # Get the AWS default region from the AWS CLI configuration
        aws_region = boto3.Session().region_name

        # Create an EC2 client
        ec2_client = boto3.client('ec2', region_name=aws_region)

        while True:
            localEndpointNodesIPs = []
            # Implement logic to get endpoint nodes IPs from AWS here
            
            # Use ec2_client.describe_instances() to get the list of instances with the tag 'Type' = 'EndpointNode'
            # For each instance, get the private IP address and append it to the localEndpointNodesIPs list
            # wrte your code here
            response = ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:Type',
                        'Values': [
                            'EndpointNode',
                        ]
                    },
                ],
            )
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    localEndpointNodesIPs.append(instance["PrivateIpAddress"])

            # If the localEndpointNodesIPs not contains the parentIP print error message and set shouldShutdown to True
            if self.parentIP != None and self.parentIP not in localEndpointNodesIPs: 
                print("Error: Parent IP not in localEndpointNodesIPs")
                self.shouldShutdown = True
                # TODO could probably also try and talk with the parentIP and check if is alive before setting the worker to shutdown
            else:
                print("Setting new endpointNodesIPs: ", localEndpointNodesIPs)
                self.endpointNodesIPs = localEndpointNodesIPs

            time.sleep(30)

    def work(self, buffer, iterations):
        import hashlib
        output = hashlib.sha512(buffer).digest()
        for i in range(iterations - 1):
            output = hashlib.sha512(output).digest()
        return output

    def run(self):
        # Start get_endpoint_nodes_ips_from_AWS as background thread
        endpoint_nodes_ips_thread = threading.Thread(target=self.get_endpoint_nodes_ips_from_AWS)
        endpoint_nodes_ips_thread.daemon = True
        endpoint_nodes_ips_thread.start()
        
        # Take different node every time
        self.lastWorkTime = time.time()
        while not self.shouldShutdown and (time.time() - self.lastWorkTime) < 600:
            for nodeIP in self.endpointNodesIPs:
                work = self.get_work(nodeIP)
                if work != None:
                    print("Got work from node:" + nodeIP)
                    result = self.work(work.data, work.iterations)
                    self.completed_work(nodeIP, work.work_id, result)
                    self.lastWorkTime = time.time()
                else:
                    print("No work available for node:" + nodeIP)
            
            # TODO change the timeout to 0.1
            time.sleep(5)

        # TODO implelment logic to shutdown the worker node here 
        self.kill_myself()

    def get_work(self, ip):
        try:
            response = requests.get("http://" + ip + ":5000/giveMeWork", timeout=2)
            if response != None and response.status_code == 200:
                return Work.from_json(response.text)
        except requests.exceptions.Timeout:
            print("get_work: Timeout error")

        return None

    def completed_work(self, ip, work_id, result):
        # Send the result to the node with the given IP, using http request to port 5000 and endppoint /workCompleted
        # Write your code here
        completedWork = CompletedWork(work_id, result)
        print("completed_work: " + completedWork.to_json())
        try:
            response = requests.post("http://" + ip + ":5000/workCompleted", json=completedWork.to_json())
            if respons != None:
                print("completed_work (status code" + response.status_code + "): " + response.text)
        except requests.exceptions.Timeout:
            print("completed_work: Timeout error")

    def set_parent_ip(self, ip):
        self.parentIP = ip

    def kill_myself(self):
        print("kill_myself: " + self.name)

        try:
            response = requests.post("http://" + self.parentIP + ":5000/workerDone?worker_name=" + self.name, timeout=5)
            if response != None:
                print("kill_myself (status code" + response.status_code + "): " + response.text)
        except requests.exceptions.Timeout:
            print("kill_myself: Timeout error")

        #TODO shutdown the worker node
        #self.shutdown_os()

    def shutdown_os(self):
        # Execute the shutdown command
        subprocess.run(['sudo', 'shutdown', '-h', 'now'])

    def get_state(self):
        return {
            'name': self.name,
            'kind': 'WorkerNode',
            'parentIP': self.parentIP,
            'endpointNodesIPs': self.endpointNodesIPs,
            'lastWorkTime': self.lastWorkTime
        }


def get_public_ip():
    url = 'https://checkip.amazonaws.com'
    with urllib.request.urlopen(url) as response:
        public_ip = response.read().decode('utf-8').strip()
    return public_ip



if __name__ == '__main__':
    # Start the timer_10_sec thread in the background
    # timer_thread = threading.Thread(target=timer_10_sec)
    # timer_thread.daemon = True
    # timer_thread.start()
    # spawn_worker()

    if(Kind == "WorkerNode"):
        worker = WorkerNode(Name)
        # run worker.run() in background thread
        worker_thread = threading.Thread(target=worker.run)
        worker_thread.daemon = True
        worker_thread.start()


    app.run(host='0.0.0.0', port=5000)
