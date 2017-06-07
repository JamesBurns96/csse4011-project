/*
 * CSSE4011 driving profiling project
 * 
 * brief: UDP server/client for rapid transfer of accelerometer
 *        data through to python host program
 *
 * author: Daniel Clark
 */

#include "contiki.h"
#include "contiki-lib.h"
#include "contiki-net.h"
#include <stdio.h>
#include "dev/leds.h"
#include "dev/serial-line.h"
#include "buzzer.h"
#include "cpu/cc26xx-cc13xx/dev/cc26xx-uart.h"
#include "sys/etimer.h"
#include "sys/stimer.h"
#include "sys/timer.h"
#include "sys/rtimer.h"
#include "ieee-addr.h"
#include "button-sensor.h"
#include "dev/watchdog.h"
#include "random.h"
#include "board-peripherals.h"
#include "lib/cc26xxware/driverlib/ioc.h"
#include "ti-lib.h"
#include <stdint.h>
#include "math.h"
#include "contiki.h"
#include "sys/ctimer.h"
#include "dev/leds.h"
#include "dev/watchdog.h"
#include "net/ip/uip.h"
#include "net/ip/uip-debug.h"
#include "net/rpl/rpl.h"
#include "random.h"
#include <ctype.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "sensortag/board-peripherals.h"
#include "sensortag/cc2650/board.h"
#include "lib/cc26xxware/driverlib/gpio.h"

/*-COMPILATION_CONFIG_OPTIONS------------------------------------------------*/
// Toggles which processes are enabled
#define ACCEL_ENABLED                       1
#define TCP_ENABLED                         0
#define UDP_ENABLED                         0

// Toggles whether using etimer or ctimer
#define ETIMER                              1
// Toggles if using James' ghetto driver mods
#define ACCELEROMETER_DRIVERS_MODIFIED      0
// Controls if debug statements are enabled
#define DEBUG_PRINTING                      1

#define HEARTBEAT_PERIOD (2 * CLOCK_SECOND)

//#define BORDER_ROUTER_IP6_ADDR_CHOSEN
#ifndef BORDER_ROUTER_IP6_ADDR_CHOSEN
#warning "PICK AN IP6 ADDR FOR THE BORDER ROUTER"
#endif

#define SAMPLES_PER_PACKET 20
#define ACCEL_SAMPLE_PERIOD (CLOCK_SECOND/SAMPLES_PER_PACKET)

#define SAMPLES_PER_SECOND 20

//#define PAYLOAD_SIZE (7+(SAMPLES_PER_PACKET*12))
#define PAYLOAD_SIZE (8+(SAMPLES_PER_PACKET*6))

#define START_BYTE '('
#define STOP_BYTE ')'

#define DEBUG DEBUG_PRINT
#include "net/ip/uip-debug.h"

#define UIP_IP_BUF   ((struct uip_ip_hdr *)&uip_buf[UIP_LLH_LEN])

#define MAX_PAYLOAD_LEN 200//this has been modified in the router file
#define UIP_CONF_ROUTER 1


#define TAG_ID 1

/*---------------------------------------------------------------------------*/

static struct uip_udp_conn *server_conn;

clock_time_t next = ACCEL_SAMPLE_PERIOD;

#if UIP_CONF_ROUTER
  uip_ipaddr_t ipaddr;
#endif /* UIP_CONF_ROUTER */

/*---------------------------------------------------------------------------*/
#pragma pack(1)
typedef struct AccelData {//12 bytes
    int8_t xAcc;
    int8_t yAcc;
    int8_t zAcc;
    int8_t xGyro;
    int8_t yGyro;
    int8_t zGyro;
}AccelData;
/*---------------------------------------------------------------------------*/
#pragma pack(1)
typedef struct Payload {
    uint8_t startByte;
    uint8_t id;
    uint16_t packetNumber;
    uint32_t timeStamp;//**************************************************************************************************************
    AccelData data[SAMPLES_PER_PACKET];
    uint8_t stopByte;
} Payload;

Payload tcpPayload;
/*---------------------------------------------------------------------------*/

/*---------------------------------------------------------------------------*/
void udp_send_payload(void);
void udp_send_data(void);
void udp_send_data2(void);

/*---------------------------------------------------------------------------*/
static struct uip_udp_conn *server_conn;
static struct etimer buzz;
static struct etimer timeSyncTimer;

uint32_t UTCTime = 0;
static uint32_t timeStamp = 0;
static uint8_t payloadIndex = 0;
static uint8_t count = 0;
int secondTimer = 0;
int sampleCounter = 0;

/*---------------------------------------------------------------------------*/
//PROCESS(buzzer_process, "buzzer process");
PROCESS(udp_server_process, "UDP server process");
AUTOSTART_PROCESSES(&resolv_process,&udp_server_process);




/*---------------------------------------------------------------------------*/
/**
 * @brief   Protocol called when UDP packets are received
 * @param   None
 * @return  None
 */
static void
tcpip_handler(void)
{

    if (uip_newdata()) {
      ((char*)uip_appdata)[uip_datalen()] = 0;
      PRINTF("Server received: %d (RSSI: %d) from ", *(int*)uip_appdata, (signed short)packetbuf_attr(PACKETBUF_ATTR_RSSI));

      UTCTime = *(uint32_t*)uip_appdata;

      timeStamp = UTCTime;          
      tcpPayload.timeStamp = UTCTime;
      //tcpPayload.packetNumber = 0;

      //udp_send_data();
      PRINT6ADDR(&UIP_IP_BUF->srcipaddr);

      uip_ipaddr_copy(&server_conn->ripaddr, &UIP_IP_BUF->srcipaddr);
    }
}
/*---------------------------------------------------------------------------*/
static void
payload_print(void)
{
    /*printf("xAcc: %d, yAcc: %d, zAcc: %d, xGyro: %d, yGyro: %d, zGyro: %d\n\r",
        tcpPayload.data[payloadIndex].xAcc, tcpPayload.data[payloadIndex].yAcc,
        tcpPayload.data[payloadIndex].zAcc,
//        (int)((1.0 * tcpPayload.data[payloadIndex].xGyro) / (65536/500)),
//        (int)((1.0 * tcpPayload.data[payloadIndex].yGyro) / (65536/500)),
//        (int)((1.0 * tcpPayload.data[payloadIndex].zGyro) / (65536/500)));
        tcpPayload.data[payloadIndex].xGyro, tcpPayload.data[payloadIndex].yGyro,
        tcpPayload.data[payloadIndex].zGyro);*/
}
/*---------------------------------------------------------------------------*/
static void
tcp_payload_init(void)
{
    tcpPayload.startByte = START_BYTE;
    tcpPayload.id = TAG_ID;
    tcpPayload.stopByte = STOP_BYTE;
    tcpPayload.timeStamp = timeStamp;
    tcpPayload.packetNumber = 0;

    payloadIndex = 0;
}
/*---------------------------------------------------------------------------*/
static void
get_mpu_reading()
{

#if ACCELEROMETER_DRIVERS_MODIFIED == 0

    // Get all sensor data from accelerometer    
    /*
    tcpPayload.data[payloadIndex].xGyro
            = (int8_t)((mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_X) * 1.0) / (2 * 65536/500.0));
    tcpPayload.data[payloadIndex].yGyro
            = (int8_t)((mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Y) * 1.0) / (2 * 65536/500.0));
    tcpPayload.data[payloadIndex].zGyro
            = (int8_t)((mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Z) * 1.0) / (2 * 65536/500.0));
    tcpPayload.data[payloadIndex].xAcc
            = (int8_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_X);
    tcpPayload.data[payloadIndex].yAcc
            = (int8_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Y);
    tcpPayload.data[payloadIndex].zAcc
            = (int8_t)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Z);
            */
    tcpPayload.data[payloadIndex].xGyro
            = (int8_t)(mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_X) / 200);
    tcpPayload.data[payloadIndex].yGyro
            = (int8_t)(mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Y) / 200);
    tcpPayload.data[payloadIndex].zGyro
            = (int8_t)(mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO_Z) / 200);
    tcpPayload.data[payloadIndex].xAcc
            = (int8_t)(mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_X) / 2);
    tcpPayload.data[payloadIndex].yAcc
            = (int8_t)(mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Y) / 2);
    tcpPayload.data[payloadIndex].zAcc
            = (int8_t)(mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC_Z) / 2);

#else

    uint16_t *accRead;
    
    accRead= (uint16_t *)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_GYRO);

    tcpPayload.data[payloadIndex].xGyro = accRead[0];
    tcpPayload.data[payloadIndex].yGyro = accRead[1];
    tcpPayload.data[payloadIndex].zGyro = accRead[2];

    accRead= (uint16_t *)mpu_9250_sensor.value(MPU_9250_SENSOR_TYPE_ACC);
    tcpPayload.timeStamp = timeStamp;
    tcpPayload.data[payloadIndex].xAcc = accRead[0];
    tcpPayload.data[payloadIndex].yAcc = accRead[1];
    tcpPayload.data[payloadIndex].zAcc = accRead[2];
#endif

#if ETIMER == 0
    SENSORS_DEACTIVATE(mpu_9250_sensor);
    ctimer_set(&mpu_timer, next, init_mpu_reading, NULL);
#endif
    // increase payload index 
    payloadIndex = ((payloadIndex + 1) % SAMPLES_PER_PACKET);

    ++count;

}
/*---------------------------------------------------------------------------*/
static void
init_mpu_reading(void *not_used)
{
  mpu_9250_sensor.configure(SENSORS_ACTIVE, MPU_9250_SENSOR_TYPE_ALL);
}
/*---------------------------------------------------------------------------*/
static void
print_local_addresses(void)
{
  int i;
  uint8_t state;

  PRINTF("Server IPv6 addresses: ");
  for(i = 0; i < UIP_DS6_ADDR_NB; i++) {
    state = uip_ds6_if.addr_list[i].state;
    if(uip_ds6_if.addr_list[i].isused &&
       (state == ADDR_TENTATIVE || state == ADDR_PREFERRED)) {
      PRINT6ADDR(&uip_ds6_if.addr_list[i].ipaddr);
      PRINTF("\n\r");
    }
  }
}
/*---------------------------------------------------------------------------*/
PROCESS_THREAD(udp_server_process, ev, data)
{


  PROCESS_BEGIN();
  PRINTF("UDP server started\n\r");

#if RESOLV_CONF_SUPPORTS_MDNS
  resolv_set_hostname("contiki-udp-server");
#endif

#if UIP_CONF_ROUTER
  uip_ip6addr(&ipaddr, 0xaaaa, 0, 0, 0, 0, 0, 0, 0);
  uip_ds6_set_addr_iid(&ipaddr, &uip_lladdr);
  uip_ds6_addr_add(&ipaddr, 0, ADDR_AUTOCONF);
#endif /* UIP_CONF_ROUTER */
  NETSTACK_RADIO.set_value(RADIO_PARAM_TXPOWER,5);
//NETSTACK_RADIO.set_value(RADIO_PARAM_CHANNEL, 13);

  print_local_addresses();

  //Create UDP socket and bind to port 3000
  server_conn = udp_new(NULL, UIP_HTONS(7005), NULL);
  udp_bind(server_conn, UIP_HTONS(4003));

  init_mpu_reading(NULL);
  tcp_payload_init();
  etimer_set(&buzz, CLOCK_SECOND/SAMPLES_PER_SECOND);	//Set event timer for 0.1s interval.
  etimer_set(&timeSyncTimer, CLOCK_SECOND);

  while(1) {
    PROCESS_YIELD();

	  //Wait for tcipip event to occur
    if(ev == tcpip_event) {
      tcpip_handler();
    }
    if(ev == PROCESS_EVENT_TIMER) {

			if(data == &buzz) {
        
        //udp_send_data2();     

        get_mpu_reading();

        payload_print();
        sampleCounter++;

        //if a new packet has been loaded with all the samples needed
        //send the udp packet
        if (sampleCounter == SAMPLES_PER_PACKET) {
          sampleCounter = 0;
          tcpPayload.packetNumber++;
          udp_send_payload();
        }             

        etimer_reset(&buzz);
        
      } else if (data == &timeSyncTimer) {
        leds_toggle(LEDS_RED);
        timeStamp++;
        tcpPayload.timeStamp = timeStamp;
        etimer_reset(&timeSyncTimer);
      }
    }
  }

  PROCESS_END();
}
/*---------------------------------------------------------------------------*/
void udp_send_payload(void) {

  printf("sending packet update to pc");

  PRINT6ADDR(&ipaddr);
  PRINTF("\n");

  uip_ipaddr_copy(&ipaddr, &UIP_IP_BUF->srcipaddr);

  uip_udp_packet_send(server_conn, &tcpPayload, PAYLOAD_SIZE);
}

void udp_send_data(void) {    

    printf("sending packet update to pc");

    PRINT6ADDR(&UIP_IP_BUF->srcipaddr);
    PRINTF("\n");

    uip_ipaddr_copy(&server_conn->ripaddr, &UIP_IP_BUF->srcipaddr);

    uip_udp_packet_send(server_conn, &tcpPayload, PAYLOAD_SIZE);
}

void udp_send_data2(void) {    

    printf("sending packet update to pc");

    PRINT6ADDR(&ipaddr);
    PRINTF("\n");

    uip_ipaddr_copy(&ipaddr, &UIP_IP_BUF->srcipaddr);

    uip_udp_packet_send(server_conn, &UTCTime, 4);
}