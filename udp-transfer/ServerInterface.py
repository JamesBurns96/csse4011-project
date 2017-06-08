import requests as req
import json


def update_server_driver(name, confidence):
    js = json.dumps({'name': name, 'confidence': confidence})
    print js

    s = req.Session()
    r = req.Request('POST', 'https://localhost:5000/data/ml')
    prepped = r.prepare()
    prepped.headers['Content-Type'] = 'application/json'
    prepped.body = js
    prepped.headers['Content-Length'] = len(js)

    resp = s.send(prepped, verify=False)
    print resp.status_code
    print resp.text
    print resp.raw


if __name__ == '__main__':
    update_server_driver('dan', 5)
