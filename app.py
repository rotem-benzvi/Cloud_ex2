from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from queue import Queue
import boto3
import paramiko
import argparse

app = Flask(__name__)

parser = argparse.ArgumentParser()
parser.add_argument('-kind', help='Specify the kind')
parser.add_argument('-name', help='Specify the name')
args = parser.parse_args()

# Access the value of the 'kind' argument
kind = args.kind
Name = args.name

workQueue = Queue()
workComplete = []
maxNumOfWorkers = 2
numOfWorkers = 0

Name = 'DeafultName'
Kind = 'DefaultKind'

# Access the environment variables
access_key = os.environ['AWS_ACCESS_KEY_ID']
secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
region = os.environ['AWS_DEFAULT_REGION']

# Create a session using the environment variables
session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name=region
)

# Create an EC2 resource using the session
ec2_resource = session.resource('ec2')

# region_name = 'eu-west-1'
# ec2_resource = boto3.resource('ec2', region_name=region_name)

otherNode = None  # Replace with the actual implementation of otherNode

@app.route('/getArguments', methods=['GET'])
def get_arguments():
    return jsonify({'name': Name, 'kind:': Kind}), 200

@app.route('/')
def index():
    completed_work = workComplete
    return render_template('index.html', completed_work=completed_work)

@app.route('/enqueueWork', methods=['POST'])
def enqueue_work():
    text = request.form['text']
    iterations = request.form['iterations']
    workQueue.put((text, iterations, datetime.now()))
    return jsonify({'message': 'Work enqueued successfully.'}), 200

@app.route('/giveMeWork', methods=['POST'])
def give_me_work():
    if not workQueue.empty():
        work = workQueue.get()
        return jsonify({'text': work[0], 'iterations': work[1]}), 200
    else:
        return jsonify({'message': 'No work available.'}), 204

@app.route('/pullComplete', methods=['POST'])
def pull_complete():
    n = int(request.form['n'])
    results = workComplete[:n]
    # if len(results) < n:
    #     try:
    #         results.extend(otherNode.pullCompleteInternal(n - len(results)))
    #     except:
    #         pass
    return jsonify(results), 200

@app.route('/spawn_worker', methods=['POST'])
def spawn_worker():
    global numOfWorkers
    global ec2_resource
    # Create a new EC2 instance
    instance = ec2_resource.create_instances(
        ImageId='ami-00aa9d3df94c6c354',
        InstanceType='t2.micro',
        KeyName='eladkey',
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=['my-sg-N'],
        UserData='''#!/bin/bash

            echo "Install: apt update"
            apt update
            echo "Install: python3"
            apt install python3 -y
            echo "Install: python3-flask"
            apt install python3-flask -y
            echo "Install: python3-pip"
            apt install python3-pip -y
            echo "Install: upgrade pip"
            pip3 install --upgrade pip
            echo "Install: awscli"
            pip3 install awscli
            echo "Install: boto3"
            pip3 install boto3 
            echo "Install: paramiko"
            pip3 install paramiko
            echo "Install: Done"

            git clone --single-branch --branch EladBranch https://github.com/rotem-benzvi/Cloud_ex2.git

            cd Cloud_ex2/

            FLASK_APP="app.py"
            nohup python3 app.py -name endpoint_node1 -kind EndpointNode &>/var/log/pythonlogs.txt &
            
            echo "done"
            exit
         ''',
    )[0]

    # Wait until the instance is running
    instance.wait_until_running()

    # Update the worker count
    numOfWorkers += 1

    return jsonify({'instance_id': instance.id}), 200
      

def timer_10_sec_describe_instances():
    if not workQueue.empty() and (datetime.now() - workQueue.queue[0][2]) > timedelta(seconds=15):
        # Implement describe_instances logic here
        instances = []
        if len(instances) < maxNumOfWorkers:
            spawn_worker()

def timer_10_sec():
    while True:
        if not workQueue.empty() and (datetime.now() - workQueue.queue[0][2]) > timedelta(seconds=15):
            if numOfWorkers < maxNumOfWorkers:
                spawn_worker()
            # else:
            #     if otherNode.TryGetNodeQuota():
            #         maxNumOfWorkers += 1

def try_get_node_quota():
    global maxNumOfWorkers
    if numOfWorkers < maxNumOfWorkers:
        maxNumOfWorkers -= 1
        return True
    return False

print("I've made it here")

#spawn_worker()

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
    app.run(host='0.0.0.0', port=5000)
