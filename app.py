from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from queue import Queue
import boto3
import paramiko

app = Flask(__name__)

workQueue = Queue()
workComplete = []
maxNumOfWorkers = 2
numOfWorkers = 0

Name = 'DeafultName'
Kind = 'DefaultKind'

region_name = 'eu-west-1'
ec2_resource = boto3.resource('ec2', region_name=region_name)

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

def spawn_worker():
    global numOfWorkers
    global ec2_resource
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

print("I've made it here")

#spawn_worker()

if __name__ == '__main__':
    # Start the timer_10_sec thread in the background
    # timer_thread = threading.Thread(target=timer_10_sec)
    # timer_thread.daemon = True
    # timer_thread.start()
    # spawn_worker()
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-name')
    parser.add_argument('-kind')
    args = parser.parse_args()
    Name = args.name
    Kind = args.kind

    app.run()
