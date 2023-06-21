import base64
import json
from datetime import datetime

class CustomJSONEncoderWork(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class Work:
    def __init__(self, work_id, iterations, data, created_time):
        self.id = work_id
        self.iterations = iterations
        self.data = data
        self.created_time = created_time

    def to_json(self):
        encoded_data = base64.b64encode(self.data)
        #print("to_json1: " + encoded_data.decode('utf-8'))
        return json.dumps({
            'id': self.id,
            'iterations': self.iterations,
            'data': encoded_data.decode('utf-8'),
            'created_time': self.created_time
        }, cls=CustomJSONEncoderWork)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        decoded_data = base64.b64decode(data['data'])
        return cls(data['id'], data['iterations'], decoded_data, data['created_time'])

class CompletedWork:
    def __init__(self, work_id, value):
        self.id = work_id
        self.value = value

    def to_json(self):
        return json.dumps({
            'id': self.id,
            'value': self.value
        })

    @classmethod
    def from_json(cls, json_str):
        data =  json.loads(json_str)
        print("from_json: " + data['value'])
        return cls(data['id'], data['value'])

    def __str__(self):
        return self.to_json()

    def __repr__(self):
        return self.to_json()