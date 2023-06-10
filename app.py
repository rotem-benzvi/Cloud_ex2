from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

work_items = []
work_id = 0

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    global work_id
    iterations = request.args.get('iterations')
    data = request.get_json()
    work = {
        'id': work_id,
        'data': data,
        'iterations': iterations
    }
    work_items.append(work)
    work_id += 1
    return jsonify({'id': work['id']}), 200

@app.route('/pullCompleted', methods=['POST'])
def pull_completed():
    top = request.args.get('top')
    completed_work = []
    for work in work_items[::-1]:
        if 'result' in work:
            completed_work.append(work)
        if len(completed_work) == int(top):
            break
    return jsonify(completed_work), 200

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run()
