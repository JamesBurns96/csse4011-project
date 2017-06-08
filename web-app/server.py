from flask import Flask, redirect, url_for, request
import random
import ssl

app = Flask(__name__, static_url_path='/public')
app.debug = False

context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain('localhost.cert', 'localhost.key')

devX = 0.0
devY = 0.0
devZ = 0.0

name = ""
confidence = 0.0

sensors = [
    {"x":"0.0", "y":"0.0", "z":"0.0"},
    {"x":"0.0", "y":"0.0", "z":"0.0"},
    {"x":"0.0", "y":"0.0", "z":"0.0"},
    {"x":"0.0", "y":"0.0", "z":"0.0"},
    {"x":"0.0", "y":"0.0", "z":"0.0"},
    {"x":"0.0", "y":"0.0", "z":"0.0"}
]
@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

@app.route("/server/get")
def get_data():
    return 

@app.route("/")
def root():
    return app.send_static_file('index.html')

@app.route("/js/main.js")
def js(time = None):
    return app.send_static_file('js/main.js')

@app.route("/third-party/vis.custom.js")
def vis():
    return app.send_static_file('third-party/vis.custom.js')

@app.route("/data/driver")
def driver():
    global name
    global confidence
    '''names = ["John", "Peter", "Paul", "Jonah", "Mitchell"]
    name = names[random.randint(0, len(names) - 1)]
    confidence = random.randint(0, 1000) / 10.0
    '''
    return '{"name": "' + name + '", "confidence": "' + str(confidence) + '"}'

@app.route("/data/sensor_count")
def sensor_count():
    return '{"count": "' + str(6) + '"}'

@app.route("/data/sensor/set/<sensor>", methods=["POST"])
def sensor_data_set(sensor):
    global sensors
    json = request.get_json()
    data = {
        "x": json["x"],
        "y": json["y"],
        "z": json["z"]
    }
    sensors[int(sensor) - 1] = data
    return '{"message": "ok_data_sensor_' + sensor + '"}'

@app.route("/data/sensor/<sensor>")
def sensor_data(sensor):
    global sensors
    sensor = sensors[int(sensor) - 1]
    '''
    x = str(sensor["x"])
    y = str(sensor["y"])
    z = str(sensor["z"])
    '''
    x = str((random.randint(0, 40000) / 10000.0) - 2.0)
    y = str((random.randint(0, 40000) / 10000.0) - 2.0)
    z = str((random.randint(0, 40000) / 10000.0) - 2.0)
    #'''
    return '{"x": "' + x + '", "y": "' + y + '", "z": "' + z + '"}'

@app.route("/data/device/accelerometer/<x>/<y>/<z>")
def device_accelerometer(x, y, z):
    return '{"message": "ok_accel"}'

@app.route("/data/device/gyro/<x>/<y>/<z>")
def device_gyro(x, y, z):
    global devX
    global devY
    global devZ
    devX = x
    devY = y
    devZ = z
    return '{"message": "ok_gyro"}'

@app.route("/data/device/speed/<speed>")
def device_speed(speed):
    return '{"message": "ok_speed"}'

@app.route("/data/ml", methods=["POST"])
def machine_learning():
    global name
    global confidence
    json = request.get_json()
    name = json["name"]
    confidence = json["confidence"]
    return '{"message": "ok_ml", "data": "' + str(request.get_json()) + '"}'
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', ssl_context=context)