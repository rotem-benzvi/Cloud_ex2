from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from queue import Queue
import boto3
import paramiko
import redis
import urllib.request

app = Flask(__name__)
redis_client = redis.Redis()

workQueue = Queue()
workComplete = []
maxNumOfWorkers = 2
numOfWorkers = 0

region_name = 'eu-west-1'
ec2_client = boto3.client('ec2', region_name=region_name)
ec2_resource = boto3.resource('ec2', region_name=region_name)

otherNode = None  # Replace with the actual implementation of otherNode

@app.route('/')
def index():
    completed_work = workComplete
    return render_template('index.html', completed_work=completed_work)

@app.route('/enqueueWork', methods=['POST'])
def enqueue_work():
    text = request.form['text']
    iterations = request.form['iterations']
    work_id = len(redis_client.lrange('work_queue', 0, -1)) + 1
    work = {'id': work_id, 'text': text, 'iterations': iterations}
    redis_client.rpush('work_queue', jsonify(work))
    return jsonify({'message': 'Work enqueued successfully.', 'id': work_id}), 200

@app.route('/giveMeWork', methods=['POST'])
def give_me_work():
    work = redis_client.lpop('work_queue')
    if work:
        return work, 200
    else:
        return jsonify({'message': 'No work available.'}), 204

@app.route('/pullComplete', methods=['POST'])
def pull_complete():
    n = int(request.form['n'])
    results = [json.loads(work) for work in redis_client.lrange('work_complete', 0, n-1)]
    return jsonify(results), 200

def spawn_worker(node_public_ip):
    global numOfWorkers
    # Create a new EC2 instance
    instance = ec2_resource.create_instances(
        ImageId='ami-0e9128c6f36377edc',
        InstanceType='t2.micro',
        KeyName='worker_1_key',
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=['my-sg-N'],
        UserData='''#!/bin/bash
            sudo apt update
            sudo apt install python3-flask -y
            sudo apt install python3-pip -y
            sudo pip3 install --upgrade pip
            FLASK_APP="app.py"
            nohup flask run --host=0.0.0.0 --port=5000 &>/dev/null &
         ''',
    )[0]

    # Wait until the instance is running
    instance.wait_until_running()

    # Retrieve the public IP address of the instance
    instance.load()
    public_ip = instance.public_ip_address

    # Update the worker count
    numOfWorkers += 1
      

def timer_10_sec_describe_instances():
    if not workQueue.empty() and (datetime.now() - workQueue.queue[0][2]) > timedelta(seconds=15):
        # Implement describe_instances logic here
        instances = []
        if len(instances) < maxNumOfWorkers:
            spawn_worker(get_public_ip())

def timer_10_sec():
    while True:
        if not workQueue.empty() and (datetime.now() - workQueue.queue[0][2]) > timedelta(seconds=15):
            if numOfWorkers < maxNumOfWorkers:
                spawn_worker(get_public_ip())
            # else:
            #     if otherNode.TryGetNodeQuota():
            #         maxNumOfWorkers += 1

def try_get_node_quota():
    global maxNumOfWorkers
    if numOfWorkers < maxNumOfWorkers:
        maxNumOfWorkers -= 1
        return True
    return False

def get_public_ip():
    url = 'https://checkip.amazonaws.com'
    with urllib.request.urlopen(url) as response:
        public_ip = response.read().decode('utf-8').strip()
    return public_ip

spawn_worker(get_public_ip())

# if __name__ == '__main__':
#     # Start the timer_10_sec thread in the background
#     # timer_thread = threading.Thread(target=timer_10_sec)
#     # timer_thread.daemon = True
#     # timer_thread.start()
#     spawn_worker()
#     # app.run()
