/**
 * \file
 *         Humidity Sensor Interface program for sensortag
 *         
 * \author
 *         mds
 */

#include "contiki.h"
#include "sys/etimer.h"
#include "sys/ctimer.h"
#include "dev/leds.h"
#include "dev/watchdog.h"
#include "random.h"
#include "board-peripherals.h"

#include "ti-lib.h"

#include <stdio.h>
#include <stdint.h>

#define ACCEL_SAMPLES_PER_SECOND 10
#define ACCEL_SAMPLE_PERIOD (CLOCK_SECOND/ACCEL_SAMPLES_PER_SECOND)

#define START_BYTE '('
#define STOP_BYTE ')'

#define TAG_ID 0

/*---------------------------------------------------------------------------*/
static struct etimer et;

static uint16_t timeStamp = 0;
static uint8_t payloadIndex = 0;
/*---------------------------------------------------------------------------*/
PROCESS(accelerometer_process, "accelerometer process");
AUTOSTART_PROCESSES(&accelerometer_process);

/*---------------------------------------------------------------------------*/
typedef struct AccelData {
    uint8_t xAcc;
    uint8_t yAcc;
    uint8_t zAcc;
    uint8_t xGyro;
    uint8_t yGyro;
    uint8_t zGyro;
}AccelData;
/*---------------------------------------------------------------------------*/
typedef struct Payload {
    uint8_t startByte;
    uint8_t id;
    uint16_t timeStamp;
    AccelData data[ACCEL_SAMPLES_PER_SECOND];
    uint8_t stopByte;
} Payload;

Payload tcpPayload;
/*---------------------------------------------------------------------------*/
static struct ctimer mpu_timer;		//Callback timer
/*---------------------------------------------------------------------------*/
static void init_mpu_reading(void *not_used);
/*---------------------------------------------------------------------------*/
static void
payload_print(void)
{
    printf("xAcc: %d, yAcc: %d, zAcc: %d, xGyro: %d, yGyro: %d, zGyro: %d\n\r",
        tcpPayload.data[payloadIndex].xAcc, tcpPayload.data[payloadIndex].yAcc,
        tcpPayload.data[payloadIndex].zAcc, tcpPayload.data[payloadIndex].xGyro,
        tcpPayload.data[payloadIndex].yGyro, tcpPayload.data[payloadIndex].zGyro);
}
/*---------------------------------------------------------------------------*/
static void
tcp_payload_init(void)
{
    tcpPayload.startByte = START_BYTE;
    tcpPayload.id = TAG_ID;
    tcpPayload.stopByte = STOP_BYTE;
    tcpPayload.timeStamp = timeStamp;
}
/*---------------------------------------------------------------------------*/
static void
get_mpu_reading()
{
    clock_time_t next = ACCEL_SAMPLE_PERIOD;

    tcpPayload.data[payloadIndex].xGyro
            = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_X);
    tcpPayload.data[payloadIndex].yGyro
            = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Y);
    tcpPayload.data[payloadIndex].zGyro
            = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Z);
    tcpPayload.data[payloadIndex].xAcc
            = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_X);
    tcpPayload.data[payloadIndex].yAcc
            = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Y);
    tcpPayload.data[payloadIndex].zAcc
            = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Z);
    SENSORS_DEACTIVATE(mpu_9250_sensor);

    ctimer_set(&mpu_timer, next, init_mpu_reading, NULL);
}
/*---------------------------------------------------------------------------*/
static void
init_mpu_reading(void *not_used)
{
  mpu_9250_sensor.configure(SENSORS_ACTIVE, MPU_9250_SENSOR_TYPE_ALL);
}
/*---------------------------------------------------------------------------*/
PROCESS_THREAD(accelerometer_process, ev, data) {
	
  	PROCESS_BEGIN();

  	etimer_set(&et, CLOCK_SECOND * 2);	//Set event timer for 20s interval.
    init_mpu_reading(NULL);
    tcp_payload_init();
  	
    
    while(1) {

    	PROCESS_YIELD();

		//Flash red LED every 2s.
		if(ev == PROCESS_EVENT_TIMER) {

			if(data == &et) {
				leds_toggle(LEDS_RED);
				etimer_set(&et, CLOCK_SECOND * 2);		//Reset event timer
			}

		//Check for sensor event
		} else if(ev == sensors_event) {

			//Check for Humidity reading
		  	if(ev == sensors_event && data == &hdc_1000_sensor) {

                get_mpu_reading();

                payload_print();

			}
		}
	}

  PROCESS_END();
}
