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

#define ACCEL_SAMPLES_PER_SECOND 10
#define ACCEL_SAMPLE_PERIOD (CLOCK_SECOND/ACCEL_SAMPLES_PER_SECOND)

#define START_BYTE '('
#define STOP_BYTE ')'

#define TCP_PORT 42069
#define UDP_CLIENT_PORT 42070
#define UDP_SERVER_PORT 42070

#define HEARTBEAT_PERIOD (2 * CLOCK_SECOND)

//#define BORDER_ROUTER_IP6_ADDR_CHOSEN
#ifndef BORDER_ROUTER_IP6_ADDR_CHOSEN
#warning "PICK AN IP6 ADDR FOR THE BORDER ROUTER"
#endif

#define TAG_ID 0


/*---------------------------------------------------------------------------*/
#define ACCEL_ENABLED
#define TCP_ENABLED
#define UDP_ENABLED
/*---------------------------------------------------------------------------*/
static struct etimer heartbeat, tcp_et;

static uip_ipaddr_t addr;

static struct uip_udp_conn *server_conn;

static uint16_t timeStamp = 0;
static uint8_t payloadIndex = 0;
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
    uint8_t xAcc;
    uint8_t yAcc;
    uint8_t zAcc;
    uint8_t xGyro;
    uint8_t yGyro;
    uint8_t zGyro;
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
/*---------------------------------------------------------------------------*/
static struct ctimer mpu_timer;		//Callback timer
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

    payloadIndex = 0;
}
/*---------------------------------------------------------------------------*/
static void
get_mpu_reading()
{

    // Get all sensor data from accelerometer
    tcpPayload.data[payloadIndex].xGyro
            = (uint8_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_X);
    tcpPayload.data[payloadIndex].yGyro
            = (uint8_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Y);
    tcpPayload.data[payloadIndex].zGyro
            = (uint8_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Z);
    tcpPayload.data[payloadIndex].xAcc
            = (uint8_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_X);
    tcpPayload.data[payloadIndex].yAcc
            = (uint8_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Y);
    tcpPayload.data[payloadIndex].zAcc
            = (uint8_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Z);

    SENSORS_DEACTIVATE(mpu_9250_sensor);

    // increase payload index 
    payloadIndex = ++payloadIndex % ACCEL_SAMPLES_PER_SECOND;

    ctimer_set(&mpu_timer, next, init_mpu_reading, NULL);
}
/*---------------------------------------------------------------------------*/
static void
init_mpu_reading(void *not_used)
{
  mpu_9250_sensor.configure(SENSORS_ACTIVE, MPU_9250_SENSOR_TYPE_ALL);
}
/*---------------------------------------------------------------------------*/
#ifdef ACCEL_ENABLED
PROCESS_THREAD(accelerometer_process, ev, data)
{
	
  	PROCESS_BEGIN();

  	etimer_set(&heartbeat, HEARTBEAT_PERIOD);	//Set event timer for 20s interval.
    init_mpu_reading(NULL);
    tcp_payload_init();
  	
    
    while(1) {

    	PROCESS_YIELD();

		//Flash red LED every 2s.
		if(ev == PROCESS_EVENT_TIMER) {

			if(data == &heartbeat) {
				leds_toggle(LEDS_RED);
				etimer_reset(&heartbeat);		//Reset event timer
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
#endif
/*---------------------------------------------------------------------------*/
#ifdef TCP_ENABLED
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
#ifdef UDP_ENABLED
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
