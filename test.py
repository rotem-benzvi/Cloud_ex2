#import the requests library
from flask import Flask, request
import requests
import os
import random


#create a function that given ip and iterations will send a PUT request to /enqueue with a random small binary data (16 – 256 KB)
def send_work(ip, port, iterations):
    # TODO, change back to random.randint(16, 256)
    #data = os.urandom(random.randint(16, 256) * 1024)
    data = os.urandom(random.randint(1,2) * 8)
    print('Sending work to ' + ip + ' with ' + str(iterations) + ' iterations.' + ' Data: ' + str(data))
    respons = requests.put('http://' + ip + ':' + port + '/enqueue?iterations=' + str(iterations), data=data)
    print(respons.text)

#create a function that given ip and top will send a POST request to /pullCompleted with top as a query parameter
def pull_completed_internal(ip, port, top):
    print('Pulling completed work from ' + ip + ' with top ' + str(top))
    respons = requests.post('http://' + ip + ':' + port + '/pullCompleted?top=' + str(top))
    print(respons.text)
    return respons.json()

#create a function that given ip call /getStatus and return the response
def get_status(ip, port):
    response = requests.get('http://' + ip + ':' + port + '/getStatus')
    print("get_status: " + str(response.status_code))
    print(response.text)
    return response.json()

def get_work(ip, port):
    print("get_work: " + ip + ":" + port)
    try:
        response = requests.get("http://" + ip + ":" + port + "/giveMeWork", timeout=2)
        if response != None and response.status_code == 200:
            return Work.from_json(response.text)
    except requests.exceptions.Timeout:
        print("get_work: Timeout error")

    return None

def completed_work(ip, port, work_id, result):
    # Send the result to the node with the given IP, using http request to port 5000 and endppoint /workCompleted
    # Write your code here
    completedWork = CompletedWork(work_id, result)
    print("completed_work: " + completedWork.to_json())
    try:
        response = requests.post("http://" + ip + ":" + port + "/workCompleted", json=completedWork.to_json())
        if respons != None:
            print("completed_work (status code" + response.status_code + "): " + response.text)
    except requests.exceptions.Timeout:
        print("completed_work: Timeout error")


if __name__ == '__main__':
    # create code that parse arguments ip, type and number and set variables
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', help='Specify the ip')
    parser.add_argument('-type', help='Specify the type')
    parser.add_argument('-value', help='Specify the value')
    parser.add_argument('-port', help='Specify the number', default='5000')
    parser.add_argument('-wokr_id', help='Specify the number')
    args = parser.parse_args()

    node_1_ip = args.ip
    type = args.type
    value = int(args.value)
    port = args.port
    wokr_id = args.wokr_id

    print("#########################################")
    
    if type == "send":
        for i in range(0, int(value)):
            send_work(node_1_ip, port, random.randint(5, 30))

    if type == "pull":
        pull_completed_internal(node_1_ip, port, int(value))

    if type == "status":
        get_status(node_1_ip, port)

    if type == "work":
        get_work(node_1_ip, port)

    if type == "completed":
        completed_work(node_1_ip, port, wokr_id, value)

    print("#########################################")

        