var cameraPositions = [
    {
        horizontal: 1,
        vertical: 0.5,
        distance: 1.5
    },
    {
        horizontal: 1,
        vertical: 0.5,
        distance: 1.5
    },
    {
        horizontal: 1,
        vertical: 0.5,
        distance: 1.0
    }
];

var sensors = {};
var vectorGraphs = [];

$(document).ready(function() {
    setupSensors();
    setupPrediction();
    setupDeviceGyro();
    setupDeviceSpeed();
})

/**
 * DEVICE SENSORS
 */

function setupDeviceGyro() {
    if (window.DeviceOrientationEvent) {
        window.addEventListener("deviceorientation", function () {
            tilt(event.beta, event.gamma, event.alpha);
        }, true);
    } else if (window.DeviceMotionEvent) {
        window.addEventListener('devicemotion', function () {
            tilt(event.acceleration.x * 2, event.acceleration.y * 2, event.acceleration.z * 2);
        }, true);
    } else {
        window.addEventListener("MozOrientation", function () {
            tilt(orientation.x * 50, orientation.y * 50, orientation.z * 50);
        }, true);
    }

    function tilt(rx, ry, rz) {
        rx = Math.floor(rx * 1000) / 1000;
        ry = Math.floor(ry * 1000) / 1000;
        rz = Math.floor(rz * 1000) / 1000;

        var data = sensors["device_gyro"];

        data.x.append(new Date().getTime(), rx);
        data.y.append(new Date().getTime(), ry);
        data.z.append(new Date().getTime(), rz);

        if (data.x.length > 50) {
            data.x.shift();
        }
        if (data.y.length > 50) {
            data.y.shift();
        }
        if (data.z.length > 50) {
            data.z.shift();
        }

        data.dataX.html(rx);
        data.dataY.html(ry);
        data.dataZ.html(rz);

        updateVectorGraph(data.vectorElement, rx, ry, rz, "device_gyro");

        $.get({
            url: "/data/device/gyro/" + rx + "/" + ry + "/" + rz
        }).done(function(data) {
            // Do nothing
        })
    }
}

function setupDeviceSpeed() {
    var lastLong = null;
    var lastLat = null;
    var lastTime = null;
    var speed = null;

    if (navigator.geolocation) {
        getPosition();
    }

    function getPosition() {
        navigator.geolocation.getCurrentPosition(handlePosition, null, {enableHighAccuracy: true});

        setTimeout(getPosition, 250);
    }

    function handlePosition(pos) {
        var lat = pos.coords.latitude;
        var long = pos.coords.longitude;
        var now = Date.now();

    if (lastLong != null && lastLat != null && lastTime != null && now != lastTime) {
            var tempSpeed = distance(lat, long, lastLat, lastLong) / ((now - lastTime) / 1000.0);   

            if (tempSpeed != null && !isNaN(tempSpeed)) {
                speed = tempSpeed / (3600 * 1000);
                speed = speed * 10000000;
            }
        }

        if (speed != null && speed != 0) {
            var data = sensors["device_speed"];

            data.x.append(new Date().getTime(), speed);

            if (data.x.length > 50) {
                data.x.shift();
            }

            data.dataX.html(speed + "km/h");

            updateVectorGraph(data.vectorElement, speed, 0, 0, "device_speed");

            $.get({
                url: "/data/device/speed/" + speed
            }).done(function(data) {
                // Do nothing
            })
        }

        lastLong = long;
        lastLat = lat;
        lastTime = now;
    }
    
    function distance(lat1, long1, lat2, long2) {
        if (lat1 == lat2 && long1 == long2) {
            return null;
        }
        var R = 6371000; // metres (Earth radius)
        var dLat = (lat2 - lat1) * Math.PI / 180.0;
        var dLon = (long2 - long1) * Math.PI / 180.0;
        var a = Math.sin(dLat / 2.0) * Math.sin(dLat / 2.0) +
            Math.cos(lat1 * Math.PI / 180.0) * Math.cos(lat2 * Math.PI / 180.0) *
            Math.sin(dLon / 2.0) * Math.sin(dLon / 2.0);
        var c = 2.0 * Math.atan2(Math.sqrt(a), Math.sqrt(1.0 - a));
        var d = R * c;
        var dist = Math.abs(d);
        return dist;
    }
}

/**
 * PREDICTION FUNCTIONS
 */

function setupPrediction() {
    $driverName = $("#driver-name");
    $driverConfidence = $("#driver-confidence");

    function getDriverData() {
        $.get({
            url: "/data/driver",
            dataType: "json"
        }).done(function(data) {
            $driverName.html(data.name);
            $driverConfidence.html(data.confidence + "%")
        })

        setTimeout(getDriverData, (Math.random() * 5 + 2) * 1000);
    }

    getDriverData();
}


/**
 * SENSOR TAG FUNCTIONS
 */

function setupSensors() {
    $.get({
        url: "/data/sensor_count",
        dataType: "json"
    }).done(function(data) {
        for (var sensor = 1; sensor <= data.count; sensor++) {
            if (sensor > 1) {
                createNewSensor(sensor);
            }

            configureSensor(sensor);
        }

        createNewSensor("device_gyro");
        configureSensor("device_gyro");

        createNewSensor("device_speed");
        configureSensor("device_speed");
    })
}

function createNewSensor(sensor) {
    $new = $("#sensor-1").clone()

    $new.attr("id", "sensor-" + sensor);
    $new.find(".sensor-name").first().html("Sensor " + sensor);
    $new.find(".show-hide-toggle").first().attr("data-target", "#sensor-" + sensor + "-collapse");
    $new.find(".collapse").first().attr("id", "sensor-" + sensor + "-collapse");
    
    $new.appendTo($("#sensor-1").parent());
}

function configureSensor(sensor) {
    $sensor = $("#sensor-" + sensor);

    $dataX = $sensor.find(".data-x").first();
    $dataY = $sensor.find(".data-y").first();
    $dataZ = $sensor.find(".data-z").first();

    chartElement = $sensor.find(".chart").first().get(0);
    chartElement.setAttribute("width", $(chartElement.parentNode).width());

    vectorElement = $sensor.find(".vector").first().get(0);

    var x = new TimeSeries();
    var y = new TimeSeries();
    var z = new TimeSeries();

    createVectorGraph(vectorElement, 1, 0, 0, sensor);

    if ($(window).width() > 992) {
        chartElement.setAttribute("height", $(chartElement.parentNode).height());
    }

    var chart = new SmoothieChart({minValue: -2, maxValue: 2});

    if (sensor == "device_gyro") {
        chart = new SmoothieChart({minValue: -180, maxValue: 180});
    }

    if (sensor == "device_speed") {
        chart = new SmoothieChart({minValue: 0, maxValue: 100});
    }

    chart.addTimeSeries(x, { strokeStyle: 'rgba(0, 255, 0, 1)', fillStyle: 'rgba(0, 255, 0, 0.2)', lineWidth: 3 });
    chart.addTimeSeries(y, { strokeStyle: 'rgba(255, 0, 0, 1)', fillStyle: 'rgba(255, 0, 0, 0.2)', lineWidth: 3 });
    chart.addTimeSeries(z, { strokeStyle: 'rgba(0, 0, 255, 1)', fillStyle: 'rgba(0, 0, 255, 0.2)', lineWidth: 3 });
    chart.streamTo(chartElement, 500);

    sensors[sensor] = {
        sensor: $sensor,
        dataX: $dataX,
        dataY: $dataY,
        dataZ: $dataZ,
        x: x,
        y: y,
        z: z,
        chart: chart,
        chartElement: chartElement,
        vectorElement: vectorElement    
    };

    if (sensor == "device_gyro" || sensor == "device_speed") {
        // Don't use get requests for the device data
        return;
    }

    (function($dataX, $dataY, $dataZ, x, y, z, vectorElement, sensor) {
        var lastX = null;
        var lastY = null;
        var lastZ = null;

        function getSensorData() {
            $.get({
                url: "/data/sensor/" + sensor,
                dataType: "json"
            }).done(function(data) {
                var rx = data.x;
                var ry = data.y;
                var rz = data.z;

                x.append(new Date().getTime(), rx);
                y.append(new Date().getTime(), ry);
                z.append(new Date().getTime(), rz);

                if (x.length > 50) {
                    x.shift();
                }
                if (y.length > 50) {
                    y.shift();
                }
                if (z.length > 50) {
                    z.shift();
                }

                $dataX.html(rx);
                $dataY.html(ry);
                $dataZ.html(rz);

                updateVectorGraph(vectorElement, rx, ry, rz, sensor);

                lastX = rx;
                lastY = ry;
                lastZ = rz;
            })

            setTimeout(getSensorData, 1000);
        }

        getSensorData();
    })($dataX, $dataY, $dataZ, x, y, z, vectorElement, sensor);
}

function createVectorGraph(vectorElement, v1, v2, v3, sensor) {
    var min = 0.0;
    var max = 2.0;

    var horizontal = 1;
    var vertical = 0.5;
    var distance = 1.5;

    if (sensor == "device_speed") {
        max = 100.0
        vertical = 50.0;
    }

    options = {
        zMin: -max,
        zMax: max,
        yMin: -max,
        yMax: max,
        xMin: -max,
        xMax: max,
        cameraPosition: {
            horizontal: 1,
            vertical: 0.5,
            distance: 1.5
        },
        width:  $(vectorElement.parentNode).width() + "px",
        height: $(vectorElement.parentNode).width() + "px",
        style: 'line',
        showPerspective: true,
        showGrid: true,
        showShadow: false,
        keepAspectRatio: true,
        verticalRatio: 1,
        tooltip: true,
    };

    var graph = new vis.Graph3d(vectorElement);
    graph.setOptions(options);
    graph.on('cameraPositionChange', function(e){
        vectorGraphs[sensor].cameraPosition = {
            horizontal: e.horizontal,
            vertical: e.vertical,
            distance: e.distance
        }
    });

    var data = new vis.DataSet();
    data.add({id:0, x:0, y:0, z:0, style:0});
    data.add({id:1, x:v1, y:v2, z:v3});

    graph.setData(data);

    vectorGraphs[sensor] = {
        graph: graph,
        cameraPosition: options.cameraPosition, 
        data: data
    }
}

function updateVectorGraph(vectorElement, v1, v2, v3, sensor) {
    var graphConfig = vectorGraphs[sensor];

    var data = graphConfig.data;
    data.update({id:1, x:v1, y:v2, z:v3});
}
