from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from queue import Queue
import boto3
import paramiko
import urllib.request


app = Flask(__name__)

workQueue = Queue()
workComplete = []
maxNumOfWorkers = 2
numOfWorkers = 0

region_name = 'eu-west-1'
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

@app.route('/workComplete', methods=['POST'])
def work_complete():
    result = request.get_json()  # Get the result sent by the worker
    workComplete.append(result)  # Add the result to the workComplete list
    return jsonify({'message': 'Work completed successfully.'}), 200

def spawn_worker():
    global numOfWorkers
    user_data_script = '''#!/bin/bash
        cd /home/ubuntu
        python3 worker.py {ip_value}
        '''
    # Usage
    node_public_ip = get_public_ip()
    print("public ip: ", node_public_ip)

    # Create a new EC2 instance
    instance = ec2_resource.create_instances(
        ImageId='ami-0178ec22eb0d58e08',
        InstanceType='t2.micro',
        KeyName='worker_1_key',
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=['my-sg-N'],
        UserData=user_data_script.format(ip=node_public_ip),
    )[0]

    # Wait until the instance is running
    instance.wait_until_running()

    # Update the worker count
    numOfWorkers += 1
      

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

def get_public_ip():
    url = 'https://checkip.amazonaws.com'
    with urllib.request.urlopen(url) as response:
        public_ip = response.read().decode('utf-8').strip()
    return public_ip


spawn_worker()

# if __name__ == '__main__':
#     # Start the timer_10_sec thread in the background
#     # timer_thread = threading.Thread(target=timer_10_sec)
#     # timer_thread.daemon = True
#     # timer_thread.start()
#     spawn_worker()
#     # app.run()
