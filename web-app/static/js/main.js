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

        updateVectorGraph(data.vectorElement, data.rx, data.ry, data.rz, "device_gyro");

        $.get({
            url: "/data/device/gyro/" + rx + "/" + ry + "/" + rz
        }).done(function(data) {
            // Do nothing
        })
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

    if (sensor == "device_gyro") {
        // Don't use get requests for the device data
        return;
    }

    (function($dataX, $dataY, $dataZ, x, y, z, vectorElement, sensor) {
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
            })

            setTimeout(getSensorData, 1000);
        }

        getSensorData();
    })($dataX, $dataY, $dataZ, x, y, z, vectorElement, sensor);
}

function createVectorGraph(vectorElement, v1, v2, v3, sensor) {
    var min = 0.0;
    var max = 2.0;

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
