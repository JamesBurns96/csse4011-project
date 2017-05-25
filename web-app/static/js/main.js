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

var vectorGraphs = [];

$(document).ready(function() {
    setupSensors();
    setupPrediction();
})

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
            console.log(data);
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
                $new = $("#sensor-1").clone()

                $new.attr("id", "sensor-" + sensor);
                $new.find(".sensor-name").first().html("Sensor " + sensor);
                $new.find(".show-hide-toggle").first().attr("data-target", "#sensor-" + sensor + "-collapse");
                $new.find(".collapse").first().attr("id", "sensor-" + sensor + "-collapse");
                
                $new.appendTo($("#sensor-1").parent());
            }

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

            (function($dataX, $dataY, $dataZ, x, y, z, vectorElement, sensor) {
                setInterval(function() {
                    var rx = Math.floor((Math.random() * 2) * 10000) / 10000;
                    var ry = Math.floor((Math.random() * 2) * 10000) / 10000;
                    var rz = Math.floor((Math.random() * 2) * 10000) / 10000;

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
                }, 750);
            })($dataX, $dataY, $dataZ, x, y, z, vectorElement, sensor);
            
            var chart = new SmoothieChart();
            chart.addTimeSeries(x, { strokeStyle: 'rgba(0, 255, 0, 1)', fillStyle: 'rgba(0, 255, 0, 0.2)', lineWidth: 3 });
            chart.addTimeSeries(y, { strokeStyle: 'rgba(255, 0, 0, 1)', fillStyle: 'rgba(255, 0, 0, 0.2)', lineWidth: 3 });
            chart.addTimeSeries(z, { strokeStyle: 'rgba(0, 0, 255, 1)', fillStyle: 'rgba(0, 0, 255, 0.2)', lineWidth: 3 });
            chart.streamTo(chartElement, 500);
        }
    })
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
