# Hybrid 11kW Solar Inverter Data Logger Add-on

This Anenji 11kW hybrid solar inverter (likely the EM11000-48L model) is a powerful, high-frequency unit designed for both off-grid and on-grid applications. It features a pure sine wave output and a built-in 160A dual MPPT solar charge controller, supporting a wide PV input range of 60-500VDC. 

![Solar Inverter 11k](/img/inverter_1.png)
![Solar Inverter 11k](/img/inverter_3.png)

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

![Solar Inverter 11k](/img/adapter.png)

Plugging this cable USB part in your Home Assistant device will create a serial port. The exact port name you can see in your Home Assistant at the menu __Settings > System > Hardware > All Hardware__  and scroll until you see some __tty*__ devices. You have to see something like:

![Solar Inverter 11k](/img/port.png)

The DB9 side of the cable goes into the inverter's DB9 port. That is having the standard DB9 serial configuration with pins 2 (TX),3 (RX) and 5 (GND)

![Solar Inverter 11k](/img/inverter_4.png)

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
