# Overview
This is the Internal Comms component which communicates with the Beetles via BLE, collects and sends Beetle sensor data to the Ultra96.

# Setup 

## Beetles Setup
Visit the following [link](https://wiki.dfrobot.com/DFRobot_Bluetooth_4.1__BLE__User_Guide#target_0) to configure BLE specifications on the Beetle (requires Arduino IDE), and obtain the MAC address of each Beetle via AT commands.

Once the MAC address of each Beetle is obtained, open `globals.py` and edit the `BEETLE_ADDRESSES`  variable accordingly. Refer to the `mac_dict` variable to correctly match the Beetles to their respective MAC addresses.

## Bluetooth Setup on Laptop
1. Clone this repository to your relay laptop running on a Linux operating system. Note that the `bluepy` Python package used for BLE communication is only compatible with Linux.

2. Ensure Python (version 3.0 or higher) is installed on the laptop. 
    ```
    python --version
    ```

3. Install the `bluepy` package by running the following commands.
    ```
    sudo apt install python-pip libglib2.0-dev
    sudo pip install bluepy
    ```

4. Install the `bluez` Linux Bluetooth stack on which `bluepy` runs on.
    ```
    sudo apt install bluez
    ```

5. Start Bluetooth on the laptop.
    ```
    sudo systemctl enable bluetooth.service
	sudo systemctl start bluetooth.service
    ```

6. Ensure your laptop's Bluetooth interface is `UP RUNNING` by running the following commands. (X is the number of the interface shown via the `hciconfig` command)
    ```
    sudo hciconfig
    sudo hciconfig hciX up
    ```

## Installing Dependencies
Install the remaining dependencies required for SSH tunnelling to the Ultra96.
```
pip install -r requirements.txt
```

## Creating `.env` file
Create a `.env` file in the current working directory. The file content should be as follows (The values in `<>` are to be replaced with your own values):

```
SUNFIRE_USERNAME=<username>
SUNFIRE_PASSWD=<password>

DATA_SERVER="192.168.95.250"
DATA_SERVER_PORT=10000

DATA_CLIENT="localhost"
DATA_CLIENT_PORT=10000
```

# Running the BLE CLient
```
python3 ble_client.py
```

The BLE Client will first try to establish a SSH tunnel with the `data_server` running on the Ultra96 (External Comms component) and keeps trying until it succeeds. Upon success, the BLE Client then starts connecting to the Beetles to receive sensor data.