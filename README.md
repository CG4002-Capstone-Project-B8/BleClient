# Overview
This is the Internal Comms component which communicates with the Beetles via BLE, collects and sends Beetle sensor data to the Ultra96.

# Setup 

## Beetles BLE Setup
After uploading the corresponding Arduino code to each Beetle as specified in the README in the `TheBeetles` folder, we need to configure BLE on the Beetles via what is known as AT commands. The AT commands allow for the configuration of Beetles to be a _Peripheral_ in the BLE specification, as well as obtaining the Beetles' MAC addresses. The following steps detail the steps to correctly set up BLE on the Beetles.
1. Open a `.ino` file on Arduino IDE.
2. Connect the Beetle to the laptop. Click on <button>Tools</button>. Under _Port_, select the USB port connected to the Beetle (Arduino Uno).
3. Open the _Serial Monitor_ by clicking on the button at the top right of the IDE.
4. At the bottom of the _Serial Monitor_, there are two dropdowns. Select _No line ending_ for the first dropdown, and _115200 baud_ for the second dropdown.
5. Type `+++` into the command dialogue and click on _Send_.
6. If you see `Enter AT Mode` on the _Serial Monitor_, you have successfully accessed AT Command mode. Repeat Steps 4-5 if you fail to do so.
7. Select _Both NL & CR_ in the first dropdown, and leave the second dropdown unchanged.
8. Type `AT+SETTING=DEFPERIPHERAL` into the command dialogue and click _Send_.
9. If you see `OK` on the _Serial Monitor_, the command ran successfully. If you see `ERROR CMD`, check if the AT command entered is valid. You can verify your command by referring to the [entire list of AT commands](https://wiki.dfrobot.com/DFRobot_Bluetooth_4.1__BLE__User_Guide) here or entering `AT+HELP=ALL`.
10. Enter the following commands to ensure BLE is configured suitably for the system:
    ```
    AT+ROLE=ROLE_PERIPHERAL
    AT+UART=115200
    AT+MAC=?
    AT+EXIT
    ```
11. The Beetle is now discoverable by other devices and BLE is successfully set up.
12. Repeat these steps for remaining Beetles.

>In Step 10, the `AT+MAC=?` queries the MAC address of the Beetle. Once the MAC address of each Beetle is obtained, open `globals.py` and edit the `BEETLE_ADDRESSES`  variable accordingly. Refer to the `mac_dict` variable to correctly match the Beetles to their respective MAC addresses.

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