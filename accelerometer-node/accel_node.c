/**
 * \file
 *         Driver profiling program for sensortag. Features include:
 *          - accelerometer interfacing
 *          - tcp client
 *          - udp server
 *         
 * \author
 *         James Burns
 *         s4354912
 */

#include "contiki.h"
#include "contiki-lib.h"
#include "contiki-net.h"

#include "sys/etimer.h"
#include "sys/ctimer.h"

#include "dev/leds.h"
#include "dev/watchdog.h"

#include "net/ip/uip.h"
#include "net/ip/uip-debug.h"
#include "net/rpl/rpl.h"

#include "random.h"
#include "board-peripherals.h"

#include "ti-lib.h"

#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ACCEL_SAMPLES_PER_SECOND 20
#define ACCEL_SAMPLE_PERIOD ((1.0*CLOCK_SECOND)/(1.0*ACCEL_SAMPLES_PER_SECOND))

#define START_BYTE '('
#define STOP_BYTE ')'

#define TCP_PORT 42069
#define UDP_CLIENT_PORT 42070
#define UDP_SERVER_PORT 42071

#define HEARTBEAT_PERIOD 1 * CLOCK_SECOND

//#define BORDER_ROUTER_IP6_ADDR_CHOSEN
#ifndef BORDER_ROUTER_IP6_ADDR_CHOSEN
#warning "PICK AN IP6 ADDR FOR THE BORDER ROUTER"
#endif

#define TAG_ID 0



/*-COMPILATION_CONFIG_OPTIONS------------------------------------------------*/
// Toggles which processes are enabled
#define ACCEL_ENABLED                       1
#define TCP_ENABLED                         1
#define UDP_ENABLED                         1

// Toggles whether using etimer or ctimer
#define ETIMER                              1
// Toggles if using James' ghetto driver mods
#define ACCELEROMETER_DRIVERS_MODIFIED      0
// Controls if debug statements are enabled
#define DEBUG_PRINTING                      1
/*---------------------------------------------------------------------------*/
static struct etimer heartbeat;
#if ETIMER
static struct etimer tcp_et, accel_et;
#endif

static uip_ipaddr_t addr;

static struct uip_udp_conn *server_conn;

static uint16_t timeStamp = 0;
static uint8_t payloadIndex = 0;
static uint8_t count = 0;
clock_time_t next = ACCEL_SAMPLE_PERIOD;
/*---------------------------------------------------------------------------*/
PROCESS(accelerometer_process, "accelerometer process");
PROCESS(tcp_client_process, "tcp client process");
PROCESS(udp_server_process, "udp server process");
AUTOSTART_PROCESSES(&accelerometer_process);
// Probable startup order: tcp -> udp -> accelerometer
/*---------------------------------------------------------------------------*/
#pragma pack(1)
typedef struct AccelData {
    int16_t xAcc;
    int16_t yAcc;
    int16_t zAcc;
    int16_t xGyro;
    int16_t yGyro;
    int16_t zGyro;
}AccelData;
/*---------------------------------------------------------------------------*/
#pragma pack(1)
typedef struct Payload {
    uint8_t startByte;
    uint8_t id;
    uint16_t timeStamp;
    AccelData data[ACCEL_SAMPLES_PER_SECOND];
    uint8_t stopByte;
} Payload;

Payload tcpPayload;
#pragma message("May want to consider having a queue of payloads")
/*---------------------------------------------------------------------------*/
#if ETIMER == 0
static struct ctimer mpu_timer;		//Callback timer
#endif
/*---------------------------------------------------------------------------*/
static void init_mpu_reading(void *not_used);
/*---------------------------------------------------------------------------*/
/**
 * @brief   Protocol called when UDP packets are received
 * @param   None
 * @return  None
 */
static void
tcpip_handler(void)
{

    char *appdata;

    if(uip_newdata()) {
        appdata = (char *)uip_appdata;
        appdata[uip_datalen()] = '\0';
#warning "Consider giving this a checksum or start/stop bytes"
        timeStamp = (uint16_t)(appdata[0] | appdata[1]);
    }

    /*
    // Code from the tcp example if I ever wanna accept incoming tcp packets
    // Gotta make a variable called str if I ever wanna do this
    if(uip_newdata()) {
        str = uip_appdaata;
        str[uip_datalen()] = '\0';
        printf("Response from the server: '%s'\n\r", str);
    }

    */
    return;
}
/*---------------------------------------------------------------------------*/
static void
tcp_timeout_handler(void)
{
    uip_send((char*)&tcpPayload, sizeof(struct Payload));
}
/*---------------------------------------------------------------------------*/
static void
payload_print(void)
{
    printf("xAcc: %d, yAcc: %d, zAcc: %d, xGyro: %d, yGyro: %d, zGyro: %d\n\r",
        tcpPayload.data[payloadIndex].xAcc, tcpPayload.data[payloadIndex].yAcc,
        tcpPayload.data[payloadIndex].zAcc,
        (int)((1.0 * tcpPayload.data[payloadIndex].xGyro) / (65536/500)),
        (int)((1.0 * tcpPayload.data[payloadIndex].yGyro) / (65546/500)),
        (int)((1.0 * tcpPayload.data[payloadIndex].zGyro) / (65536/500)));
}
/*---------------------------------------------------------------------------*/
static void
tcp_payload_init(void)
{
    tcpPayload.startByte = START_BYTE;
    tcpPayload.id = TAG_ID;
    tcpPayload.stopByte = STOP_BYTE;
    tcpPayload.timeStamp = timeStamp;

    payloadIndex = 0;
}
/*---------------------------------------------------------------------------*/
static void
get_mpu_reading()
{

#if ACCEL_DRIVERS_MODIFIED

    // Get all sensor data from accelerometer    
    tcpPayload.data[payloadIndex].xGyro
            = (int16_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_X);
    tcpPayload.data[payloadIndex].yGyro
            = (int16_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Y);
    tcpPayload.data[payloadIndex].zGyro
            = (int16_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Z);
    tcpPayload.data[payloadIndex].xAcc
            = (int16_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_X);
    tcpPayload.data[payloadIndex].yAcc
            = (int16_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Y);
    tcpPayload.data[payloadIndex].zAcc
            = (int16_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Z);

#else

    uint16_t *accRead;
    
    accRead= (uint16_t *)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO);

    tcpPayload.data[payloadIndex].xGyro = accRead[0];
    tcpPayload.data[payloadIndex].yGyro = accRead[1];
    tcpPayload.data[payloadIndex].zGyro = accRead[2];

    accRead= (uint16_t *)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC);
    
    tcpPayload.data[payloadIndex].xAcc = accRead[0];
    tcpPayload.data[payloadIndex].yAcc = accRead[1];
    tcpPayload.data[payloadIndex].zAcc = accRead[2];
#endif

#if ETIMER == 0
    SENSORS_DEACTIVATE(mpu_9250_sensor);
    ctimer_set(&mpu_timer, next, init_mpu_reading, NULL);
#endif
    // increase payload index 
    payloadIndex = ((payloadIndex + 1) % ACCEL_SAMPLES_PER_SECOND);

    ++count;

}
/*---------------------------------------------------------------------------*/
static void
init_mpu_reading(void *not_used)
{
  mpu_9250_sensor.configure(SENSORS_ACTIVE, MPU_9250_SENSOR_TYPE_ALL);
}
/*---------------------------------------------------------------------------*/
#if ACCEL_ENABLED
#pragma message("Accelerometer task compilation enabled")
PROCESS_THREAD(accelerometer_process, ev, data)
{
	
  	PROCESS_BEGIN();

  	etimer_set(&heartbeat, HEARTBEAT_PERIOD);	//Set event timer for 20s interval.
  	etimer_set(&accel_et, ACCEL_SAMPLE_PERIOD);	//Set event timer for 20s interval.
    init_mpu_reading(NULL);
    tcp_payload_init();
  	
    
    while(1) {

    	PROCESS_YIELD();

		//Flash red LED every 2s.
		if(ev == PROCESS_EVENT_TIMER) {

			if(data == &heartbeat) {
				leds_toggle(LEDS_RED);
#if DEBUG_PRINTING
                printf("Count: %d\n\r", count);
#endif
                count = 0;
				etimer_reset(&heartbeat);		//Reset event timer
			}
#if ETIMER
            else if(data == &accel_et) {

                get_mpu_reading();
#if DEBUG_PRINTING
                payload_print();
#endif
                
				etimer_reset(&accel_et);		//Reset event timer

            }
#else
		//Check for sensor event
		} else if(ev == sensors_event) {

			//Check for Humidity reading
		  	if(ev == sensors_event && data == &mpu_9250_sensor) {

                get_mpu_reading();
#if DEBUG_PRINTING
                payload_print();
#endif
			}
#endif
		}
	}

  PROCESS_END();
}
#endif
/*---------------------------------------------------------------------------*/
#if TCP_ENABLED
#pragma message("TCP task compilation enabled")
PROCESS_THREAD(tcp_client_process, ev, data)
{

    PROCESS_BEGIN();
    printf("tcp client process started\n\r");

    uip_ip6addr(&addr, 0xaaaa, 0, 0, 0, 0, 0, 0, 0);

    tcp_connect(&addr, UIP_HTONS(TCP_PORT), NULL);

    printf("Connecting...\n\r");

    PROCESS_WAIT_UNTIL(ev == tcpip_event);

    if(uip_aborted() || uip_timedout() || uip_closed()) {

        printf("Could not establish connection\n\r");

    } else if(!uip_connected()) {

        printf("Unexpected behaviour while connecting\n\r");

    } else {

        printf("Connected\n\r");

        while(1) {

            if(etimer_expired(&tcp_et)) {

                tcp_timeout_handler();
                etimer_reset(&tcp_et);

            } else if(ev == tcpip_event) {

                //tcpip_handler();

            }

        }

    }

    PROCESS_END();

}
#endif
/*---------------------------------------------------------------------------*/
#if UDP_ENABLED
#pragma message("UDP task compilation enabled")
PROCESS_THREAD(udp_server_process, ev, data)
{

    PROCESS_BEGIN();

#warning "Check if I even need this. Test with/without"
    NETSTACK_MAC.off(1);

    server_conn = udp_new(NULL, UIP_HTONS(UDP_CLIENT_PORT), NULL);

    if(server_conn == NULL) {
        printf("No UDP connection available. Exiting the process.\n\r");
        PROCESS_EXIT();
    }
    udp_bind(server_conn, UIP_HTONS(UDP_SERVER_PORT));

    while(1) {

        PROCESS_YIELD();

        if(ev == tcpip_event) {
            tcpip_handler();
        }

    }

    PROCESS_END();
}
#endif
