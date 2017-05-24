/**
 * \file
 *         Accelerometer Initialiser for TI Sensortag
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
#define ACCEL_READ_PERIOD (CLOCK_SECOND / ACCEL_SAMPLES_PER_SECOND)
/*---------------------------------------------------------------------------*/
static struct etimer et;
/*---------------------------------------------------------------------------*/
struct Accel {
    int xAcc;
    int yAcc;
    int zAcc;
    int xGyro;
    int yGyro;
    int zGyro;
} accelReadings;
/*---------------------------------------------------------------------------*/
PROCESS(accelerometer_process, "accelerometer process");
AUTOSTART_PROCESSES(&accelerometer_process);
/*---------------------------------------------------------------------------*/
static struct ctimer mpu_timer;		//Callback timer
/*---------------------------------------------------------------------------*/
static void init_mpu_reading(void *not_used);
/*---------------------------------------------------------------------------*/
static void
get_mpu_reading()
{
  clock_time_t next = ACCEL_READ_PERIOD;

  accelReadings.xGyro = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_X);
  accelReadings.yGyro = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Y);
  accelReadings.zGyro = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Z);
  accelReadings.xAcc = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_X);
  accelReadings.yAcc = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Y);
  accelReadings.zAcc = mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Z);

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
	
	int humidity_temp_val;
	int humidity_val;

  	PROCESS_BEGIN();

  	etimer_set(&et, CLOCK_SECOND * 2);	//Set event timer for 20s interval.
    init_mpu_reading();

  	while(1) {

    	PROCESS_YIELD();

		//Flash red LED every 2s.
		if(ev == PROCESS_EVENT_TIMER) {
			if(data == &et) {
				leds_toggle(LEDS_RED);
				etimer_reset(&et);		//Reset event timer
			}

		//Check for sensor event
		} else if(ev == sensors_event) {

			//Check for accelerometer reading
		  	if(ev == sensors_event && data == &mpu_9250_sensor) {

                get_mpu_reading();

			}
		}
	}

  PROCESS_END();
}

