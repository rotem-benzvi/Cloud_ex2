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
from model import Work, CompletedWork
import socket

def get_private_ip():
    # Get the hostname
    hostname = socket.gethostname()

    # Get the IP address associated with the hostname
    ip_address = socket.gethostbyname(hostname)

    return ip_address

app = Flask(__name__)

Name = 'DeafultName'
Kind = 'DefaultKind'

parser = argparse.ArgumentParser()
parser.add_argument('-kind', help='Specify the kind')
parser.add_argument('-name', help='Specify the name')
parser.add_argument('-parent_private_ip', help="Specify parent private ip")
parser.add_argument('-key_name', help="Specify key_name")
parser.add_argument('-security_group', help="Specify security_group")

args = parser.parse_args()

# Access the value of the 'kind' argument
Kind = args.kind
Name = args.name
Key_Name = args.key_name
Security_Group = args.security_group
Parent_Private_Ip = args.parent_private_ip

worker = None

workQueue = Queue()
workComplete = []
maxNumOfWorkers = 2
workers = []
otherNodeIp = None
work_id_counter = 1

ec2_resource = boto3.resource('ec2')

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
        'workers':  workers,
        'workCompleteSize': len(workComplete),
        'workQueueSize': workQueue.qsize(),
        'workComplete': str(workComplete),
        'parent_private_ip': Parent_Private_Ip
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

@app.route('/workerDone', methods=['POST'])
def worker_done():
    #remove worker from list of workers
    worker_name = request.args.get('worker_name')
    message = "Not my worker."
    for worker in workers:
        if worker == worker_name:
            workers.remove(worker)
            message = "Worker " + worker_name + " removed successfully."
            break

    return jsonify({'message': message}), 200


@app.route('/giveMeWork', methods=['GET'])
def give_me_work():
    if not workQueue.empty():
        work = workQueue.get()
        print("Work given to worker: " + work.id)
        print(type(work))
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
    data = request.data
    print("Work received: " + data.decode('latin-1'))

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

    workCompleteJson = str(completed_items)
    return jsonify(workCompleteJson), 200



############################
#    For Testing Purposes  #
############################

#TODO remove this endpoint when finish debugging
@app.route('/spawn_empty_worker', methods=['POST'])
def spawn_empty_worker():
    worker_name = request.args.get('worker_name')
    workers.append(worker_name)
    return jsonify({'message': 'Worker spawned successfully.'}), 200

#TODO remove this endpoint when finish debugging
@app.route('/spawn_worker', methods=['POST'])
def spawn_worker():
    if(endpoint != None):
        key_name = request.args.get('keyName')
        security_group = request.args.get('securityGroup')
        parent_private_ip = request.args.get('parentIp')
        woker_name = "worker_456"

        print(f"key_name: {key_name}, security_group: {security_group}, woker_name: {woker_name}, parent_private_ip: {parent_private_ip}")

        public_ip, instance_id = endpoint.spawn_worker(woker_name, key_name, security_group, parent_private_ip)

        return jsonify({'instance_id': instance_id, 'public_ip': public_ip}), 200

    return jsonify({'message': 'Endpoint not initialized.'}), 404

@app.route('/shutdown', methods=['POST'])
def shutdown_os():
    if(worker != None):
        # Execute the shutdown command
        worker.shutdown()

        # Return a response indicating that the shutdown command has been initiated
        return jsonify({'message': 'Shutdown initiated successfully.'}), 200

    return jsonify({'message': 'Worker not initialized.'}), 404
    


############################
#    End Testing Purposes  #
############################

############################
#    condsider implement  #
############################

# TODO fix method
def try_get_node_quota():
    global maxNumOfWorkers
    if len(worker) < maxNumOfWorkers:
        maxNumOfWorkers -= 1
        return True
    return False

############################
#    End condsider implement  #
############################

# new Code 
class EndPointNode:
    # creaete a worker node
    def __init__(self, name, key_name, security_group):
        self.name = name
        self.key_name = key_name
        self.security_group = security_group
        self.worker_id_counter = 1

    def spawn_worker_if_needed(self):
        while True:
            if not workQueue.empty() and (datetime.now() - workQueue.queue[0].created_time) > timedelta(seconds=15):
                print("spawn_worker_if_needed: workQueue not empty and last work created more than 15 seconds ago.")
                if len(workers) < maxNumOfWorkers:
                    print("spawn_worker_if_needed: workers list is not full.")
                    # create worker name based on the endpointname + the worker number
                    woker_name = "worker_" + str(self.worker_id_counter) + "_of_" + self.name
                    self.worker_id_counter += 1
                    parent_private_ip = get_private_ip()

                    public_ip, instance_id = self.spawn_worker(woker_name, self.key_name, self.security_group, parent_private_ip)
                    print(f"spawn_worker_if_needed: worker spawned successfully. public_ip: {public_ip} , instance_id: {instance_id}")
            else:
                print("spawn_worker_if_needed: workQueue is empty or last work created less than 15 seconds ago.")
            
                
            print("spawn_worker_if_needed: sleeping for 15 seconds.")
            #TODO change sleep to 0.1
            time.sleep(15)
            
            # TODO check if needed
            # else:
            #     if otherNode.try_get_node_quota():
            #         maxNumOfWorkers += 1
            

    def spawn_worker(self, woker_name, key_name, security_group, parent_private_ip):
        node_name = woker_name
        node_kind = "WorkerNode"

        print("spawn_worker: key_name = " + key_name)
        print("spawn_worker: security_group = " + security_group)
        print("spawn_worker: node_name = " + node_name)
        print("spawn_worker: node_kind = " + node_kind)
        print("spawn_worker: private_ip = " + parent_private_ip)

        public_ip, instance_id = create_instance(key_name, security_group, node_name, node_kind, parent_private_ip)
        workers.append(node_name)

        return public_ip, instance_id


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
            
            filters = [
                {'Name': 'instance-state-name', 'Values': ['running']},
                {'Name': 'tag:Type', 'Values': ['EndpointNode']}
            ]

            response = ec2_client.describe_instances(Filters=filters)

            # Extract the instance IDs
            instance_ids = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_ids.append(instance['InstanceId'])

            # Call describe_instance_status to check status checks
            status_response = ec2_client.describe_instance_status(InstanceIds=instance_ids, Filters=[{'Name': 'instance-status.status', 'Values': ['ok']}])

            # Extract the instances that pass all status checks
            instances = []
            for instance_status in status_response['InstanceStatuses']:
                instances.append(instance_status['InstanceId'])

            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    if instance['InstanceId'] in instances:
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
                    self.send_completed_work(nodeIP, work.work_id, result)
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

    def send_completed_work(self, ip, work_id, result):
        encoded_result = base64.b64encode(result)
        encoded_result = encoded_result.decode('utf-8')
        completedWork = CompletedWork(work_id, encoded_result)
        print("send_completed_work: " + completedWork.to_json())
        try:
            response = requests.post("http://" + ip + ":" + port + "/postCompletedWork", data=completedWork.to_json())
            if response != None:
                print("send_completed_work (status code" + str(response.status_code) + "): " + response.text)
        except requests.exceptions.Timeout:
            print("send_completed_work: Timeout error")

    def set_parent_ip(self, ip):
        self.parentIP = ip

    def kill_myself(self):
        print("kill_myself: " + self.name)

        try:
            response = requests.post("http://" + self.parentIP + ":5000/workerDone?worker_name=" + self.name, timeout=5)
            if response != None:
                print("kill_myself (status code" + str(response.status_code) + "): " + response.text)
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


if __name__ == '__main__':
    if(Kind == "WorkerNode"):
        print("Starting worker node")
        worker = WorkerNode(Name, parentIP=Parent_Private_Ip)
        # run worker.run() in background thread
        worker_thread = threading.Thread(target=worker.run)
        worker_thread.daemon = True
        worker_thread.start()

    if (Kind == "EndpointNode"):
        print("Starting endpoint node")
        endpoint = EndPointNode(Name, Key_Name, Security_Group)
        # run endpoint.run() in background thread
        endpoint_thread = threading.Thread(target=endpoint.spawn_worker_if_needed)
        endpoint_thread.daemon = True
        endpoint_thread.start()

    app.run(host='0.0.0.0', port=4555)
