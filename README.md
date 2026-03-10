# Hybrid 11kW Solar Inverter Data Logger Add-on

This Anenji 11kW hybrid solar inverter (likely the EM11000-48L model) is a powerful, high-frequency unit designed for both off-grid and on-grid applications. It features a pure sine wave output and a built-in 160A dual MPPT solar charge controller, supporting a wide PV input range of 60-500VDC. 

![Solar Inverter 11k](https://raw.githubusercontent.com/aattila/inverter_11k_modbus-add-on/main/img/inverter_1.png)
![Solar Inverter 11k](https://raw.githubusercontent.com/aattila/inverter_11k_modbus-add-on/main/img/inverter_3.png)

## Key Technical Features

- __Dual PV Inputs__: It can handle up to 11,000W (or 15kW on some sub-models) of solar input across two strings.
- __Flexible Battery Support__: Designed for 48V battery systems, it is compatible with LiFePO4, Lithium, and Lead-Acid batteries, and can even operate in a batteryless mode by powering loads directly from solar and grid.
- __Parallel Capability__: Many versions of this 11kW series support parallel connection of up to 6 units for large-scale power needs.

## Operational Versatility

The unit typically offers four charging modes (Solar First, Utility First, Solar & Utility, and Only Solar) and two output modes (Solar First, Utility First) to optimize energy usage based on your local conditions. It is widely used in residential and small commercial settings for its high conversion efficiency (up to 96%) and robust protection features against overloads and over-temperature. 

## The add-on

This projects is based on Python's __minimalmodbus__ library. It is adapted to Home Assistant as Add-on. Use this add-on when you don't have (or want) the wifi data logger, or when just you want to keep your data private.

## Setup

The inverter has two RS232 ports but thay are phisically connected so they are shared and you have to use only one port!

### RS232 -> USB adapter cable

You need a standard RS232/USB adapter, any cheep one will work ok.

![Solar Inverter 11k](https://raw.githubusercontent.com/aattila/inverter_11k_modbus-add-on/main/img/adapter.png)

Plugging this cable USB part in your Home Assistant device will create a serial port. The exact port name you can see in your Home Assistant at the menu __Settings > System > Hardware > All Hardware__  and scroll until you see some __tty*__ devices. You have to see something like:

![Solar Inverter 11k](https://raw.githubusercontent.com/aattila/inverter_11k_modbus-add-on/main/img/port.png)

The DB9 side of the cable goes into the inverter's DB9 port. That is having the standard DB9 serial configuration with pins 2 (TX),3 (RX) and 5 (GND)

![Solar Inverter 11k](https://raw.githubusercontent.com/aattila/inverter_11k_modbus-add-on/main/img/inverter_4.png)

### The protocol

The inverter uses MODBUS RTU protocol. The slave address is configurable and it is set by default to __1__. This can be changed in the inverter's setup menu!

## Installation and configuration

1. Configure and setup an MQTT broker in Home Assistant
2. Install this Add-on and configure the serial port and the mqtt
3. Start the add-on
4. Check the logs
5. If `Enable HA Auto-Discovery` is active, it triggers the publishing of auto discovery sensor configs in Home Assistant. The devices should be added automatically. For this just check the MQTT integration
6. Add the device sensors to the dashboard

## What you get

The protocool is reverse engineered so it not contains all of the available data, but it has all the essential data the is reguraly checked/used such:

- Battery Status (Voltage, Current, Charge/Discharge Power, SoC)
- Grid Status (Voltage, Power)
- Output Status (L1 and L2 Voltage, Current, Power, Load)
- Solar Panel Status (PV 1 and PV2 Voltage, Current, Power)
- Energy per day
- Energy per year

## Dasboards

You can add your mqtt entities to the Home Assistant Energy dashboard.

![Energy Dashboard](https://raw.githubusercontent.com/aattila/inverter_11k_modbus-add-on/main/img/energy.png)

or by using the custom button card something like this:

![Energy Dashboard](https://raw.githubusercontent.com/aattila/inverter_11k_modbus-add-on/main/img/dashboard.png)

The dashboard code for the Solar Power:

```
show_name: false
show_icon: true
type: custom:button-card
entity: sensor.inverter_1_total_pv_power
icon: mdi:solar-power
show_state: true
grid_options:
  columns: 3
  rows: 2
styles:
  card:
    - height: 120px
  icon:
    - width: 70px
    - justify-self: center
    - color: >
        [[[ 

        if (states['sensor.inverter_1_total_pv_power'].state < 10) return
        'grey';

        if (states['sensor.inverter_1_total_pv_power'].state < 1000) return
        'red';

        if (states['sensor.inverter_1_total_pv_power'].state < 2500) return
        '#ff6f22';

        if (states['sensor.inverter_1_total_pv_power'].state >= 2500) return
        'green';

        ]]]
```

## For more robustness

In case ig you are using multiple USB serial devices you will facing with the following problems:

- Not enough power on the PC's USB hub or it is limited, so your USB adapter will randomly kicked off.
- After a restart or after a HA OS update (that is restart too) the mapped USB serial port such /dev/ttyUSB0 will rearranged and your adapters will get another ports that is configured in the HA add-on.

So, in this situation or if you want to introduce more robustness in your setup you need to change your adapters with something more industrial such Serial to Ethernet adatpters.

This [waveshare serial to eth adapter](https://www.waveshare.com/wiki/RS232/485/422_TO_POE_ETH_(B)#Software) is tested with succes.

![Solar Inverter 11k](https://raw.githubusercontent.com/aattila/inverter_11k_modbus-add-on/main/img/ws-eth.jpg)
![Solar Inverter 11k](https://raw.githubusercontent.com/aattila/inverter_11k_modbus-add-on/main/img/ws-poe.jpg)

To configure this adapters:

- First setup the adapter. The default access is 192.168.1.200 with no password, set the DHCP in case if you want and set the baud rate. There is NO need to set the Modbus TCP to RTU protocoll, so leave that field untouched or set None!
- In HA at the add-on configuration panel set the adapter IP address and port and specify a local serial port (/tmp/vcom0 an example) where the TCP stream will be mapped (and vice-versa)
- Pay attention for the serial port when you are using multiple devices such this, so those needs to be different for each device eg. /tmp/vcom0, /tmp/vcom1, ...

