from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from queue import Queue

app = Flask(__name__)

workQueue = Queue()
workComplete = []
maxNumOfWorkers = 0
numOfWorkers = 0

otherNode = None  # Replace with the actual implementation of otherNode

@app.route('/enqueueWork', methods=['POST'])
def enqueue_work():
    text = request.json['text']
    iterations = request.json['iterations']
    workQueue.put((text, iterations, datetime.now()))
    return jsonify({'message': 'Work enqueued successfully.'}), 200

@app.route('/giveMeWork', methods=['GET'])
def give_me_work():
    if not workQueue.empty():
        work = workQueue.get()
        return jsonify({'text': work[0], 'iterations': work[1]}), 200
    else:
        return jsonify({'message': 'No work available.'}), 204

@app.route('/pullComplete/<int:n>', methods=['GET'])
def pull_complete(n):
    results = workComplete[:n]
    if len(results) < n:
        try:
            results.extend(otherNode.pullCompleteInternal(n - len(results)))
        except:
            pass
    return jsonify(results), 200
import boto3
import paramiko

ec2 = boto3.client('ec2')
ec2_resource = boto3.resource('ec2')

def spawn_worker():
    global numOfWorkers
    # Implement spawning of worker logic here

    # Create a new EC2 instance
    instance = ec2_resource.create_instances(
        ImageId='ami-00aa9d3df94c6c354',
        InstanceType='t2.micro',
        KeyName='worker_1_key',
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=['your_security_group_id'],
        SubnetId='subnet-0ed551442172c6d19'
    )[0]

    # Wait until the instance is running
    instance.wait_until_running()

    # Retrieve the public IP address of the instance
    instance.load()
    public_ip = instance.public_ip_address

    # SSH into the instance and deploy the Flask app
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(public_ip, username='your_username', key_filename='your_private_key.pem')

    # Copy your Flask app code to the EC2 instance (e.g., using SCP)
    # Execute commands to set up the environment and run the Flask app
    # Close the SSH connection

    # Update the worker count
    numOfWorkers += 1

def timer_10_sec_describe_instances():
    if not workQueue.empty() and (datetime.now() - workQueue.queue[0][2]) > timedelta(seconds=15):
        # Implement describe_instances logic here
        instances = []
        if len(instances) < maxNumOfWorkers:
            spawn_worker()

def timer_10_sec():
    if not workQueue.empty() and (datetime.now() - workQueue.queue[0][2]) > timedelta(seconds=15):
        if numOfWorkers < maxNumOfWorkers:
            spawn_worker()
        else:
            if otherNode.TryGetNodeQuota():
                maxNumOfWorkers += 1

def try_get_node_quota():
    global maxNumOfWorkers
    if numOfWorkers < maxNumOfWorkers:
        maxNumOfWorkers -= 1
        return True
    return False

if __name__ == '__main__':
    app.run()
