from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from queue import Queue

app = Flask(__name__)

workQueue = Queue()
workComplete = []
maxNumOfWorkers = 0
numOfWorkers = 0

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

def spawn_worker():
    global numOfWorkers
    # Implement spawning of worker logic here
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
