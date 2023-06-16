from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from queue import Queue
import boto3
import paramiko
import argparse
from create_node import create_instance

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

workQueue = Queue()
workComplete = []
maxNumOfWorkers = 2
numOfWorkers = 0
otherNodeIp = None

ec2_resource = boto3.resource('ec2')

otherNode = None  # Replace with the actual implementation of otherNode

@app.route('/getStatus', methods=['GET'])
def get_arguments():
    serverState = {
        'name': Name,
        'kind': Kind,
        'otherNodeIp': otherNodeIp,
        'maxNumOfWorkers': maxNumOfWorkers,
        'numOfWorkers': numOfWorkers,
        'workCompleteSize': len(workComplete),
        'workQueueSize': workQueue.qsize()
    }
    return jsonify(serverState), 200

@app.route('/setOtherNodeIp', methods=['POST'])
def set_other_node_ip():
    global otherNodeIp
    otherNodeIp = request.args.get('ip')
    return jsonify({'message': 'Other node IP set successfully.'}), 200

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
    key_name = request.args.get('keyName')
    security_group = request.args.get('securityGroup')
    node_name = "worker_456"   
    node_kind = "WorkerNode"
    print("spawn_worker: key_name = " + key_name)
    print("spawn_worker: security_group = " + security_group)
    print("spawn_worker: node_name = " + node_name)
    print("spawn_worker: node_kind = " + node_kind)

    public_ip, instance_id = create_instance(key_name, security_group, node_name, node_kind)

    numOfWorkers += 1

    return jsonify({'instance_id': instance_id, 'public_ip': public_ip}), 200

@app.route('/shutdown', methods=['POST'])
def shutdown_os():
    # Execute the shutdown command
    subprocess.run(['sudo', 'shutdown', '-P', 'now'])

    # Return a response indicating that the shutdown command has been initiated
    return jsonify({'message': 'Shutdown initiated successfully.'}), 200

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
