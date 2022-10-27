from bluepy.btle import DefaultDelegate, Peripheral, BTLEException
import struct
import time
from constants import TPacketType
import packetize
import csv
from globals import p1_connected_beetles, p2_connected_beetles, TOTAL_BEETLES, EMITTER, RECEIVER, mac_dict, PLAYER_ONE, PLAYER_TWO, NUM_BEETLES_PER_PLAYER


class BeetleDelegate(DefaultDelegate):
    def __init__(self, beetle):
        DefaultDelegate.__init__(self)
        self.beetle = beetle

    def handleNotification(self, cHandle, data):
        self.beetle.checkBuffer(data)


class Beetle:

    SERIAL_SERVICE_UUID = "0000dfb0-0000-1000-8000-00805f9b34fb"
    SERIAL_CHAR_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"

    NOTIFICATIONS_ON = struct.pack('BB', 0x01, 0x00)

    PACKET_SIZE = 20

    # timeout value of 2 seconds
    TIMEOUT = 2

    def __init__(self, mac_address, player_id, device_id, player_queue):
        # attributes to identify each beetle uniquely
        self.mac_address = mac_address
        self.player_id = player_id
        self.device_id = device_id

        # attributes needed for Beetle connection
        self.char_handle = None
        self.delegate = None
        self.peripheral = None

        self.ack_seqnum = 0
        self.handshake_done = False

        # attribute for handling fragmentation
        self.buffer = bytes(0)

        # attribute for timeout
        self.receive_time = 0

        # for measuring throughput
        self.start_time = None
        self.end_time = None
        self.num_packets_received = 0
        # self.num_packets_dropped = 0
        # self.num_packets_fragmented = 0

        # for communication with Ultra 96
        self.has_disconnected_before = False
        self.queue = player_queue
        self.can_enqueue_data = False
        self.packet_attr = None

        # for collection of AI data
        # if self.device_id == IMU:
        #     self.csv_file = open('imu.csv', 'w', encoding='UTF8', newline='')
        #     self.csv_writer = csv.writer(self.csv_file)
        #     self.headers = ['accX', 'accY', 'accZ', 'gyroX', 'gyroY', 'gyroZ']
        #     self.csv_writer.writerow(self.headers)
        #     self.num_rows = 0

    def setDelegate(self, delegate):
        self.delegate = delegate

    def waitForNotifications(self):
        self.peripheral.waitForNotifications(1.5)

    def setCanEnqueue(self):
        total_num_beetles = p1_connected_beetles.value + p2_connected_beetles.value
        self.can_enqueue_data = (total_num_beetles >= TOTAL_BEETLES)

    def connect(self):
        # initiate a connection to Beetle
        self.peripheral = Peripheral(self.mac_address)

        # the above line running indicates a successful connection to the Beetle
        print(f"Connected successfully to Beetle - {mac_dict[self.mac_address]}")

        # obtain GATT service and characteristic handle for Serial characteristic
        serial_service = self.peripheral.getServiceByUUID(Beetle.SERIAL_SERVICE_UUID)
        serial_char = serial_service.getCharacteristics(Beetle.SERIAL_CHAR_UUID)[0]
        serial_char_handle = serial_char.getHandle()
        self.char_handle = serial_char_handle

        # enable notifications for Serial characteristic
        self.peripheral.writeCharacteristic(serial_char_handle, Beetle.NOTIFICATIONS_ON, True)
        self.peripheral.setDelegate(self.delegate)

        # start Three-way handshake
        self.initiateHandshake()
        self.incrementPlayerBeetleCount()
        
        # if all beetles for the player have been connected/reconnected, enqueue a connected packet
        if self.allPlayerBeetlesConnected():
            # connected_tuple = (TPacketType.PACKET_TYPE_CONNECTED.value, 0, self.player_id, self.device_id, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, b'\x00')
            connected_tuple = (TPacketType.PACKET_TYPE_CONNECTED.value, 0, self.player_id, 1, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, b'\x00')
            print("Connected enqueue", connected_tuple)
            self.queue.put(connected_tuple)

    def resetAttributes(self):
        self.ack_seqnum = 0

        self.num_packets_received = 0
        self.start_time = 0
        self.end_time = 0

        self.buffer = bytes(0)

        self.receive_time = 0
        self.handshake_done = False

    def disconnect(self):
        self.resetAttributes()

        # disconnect_tuple = (TPacketType.PACKET_TYPE_DISCONNECTED.value, 0, self.player_id, self.device_id, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, b'\x00')
        disconnect_tuple = (TPacketType.PACKET_TYPE_DISCONNECTED.value, 0, self.player_id, 1, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, b'\x00')
        print("Enqueue disconnect", disconnect_tuple)
        self.queue.put(disconnect_tuple)

        self.peripheral.disconnect()
        self.decrementPlayerBeetleCount()

    def reconnect(self):
        print(f"Attempting to reconnect to Beetle - {mac_dict[self.mac_address]}")
        while True:
            try:
                self.connect()
                break
            except BTLEException as e:
                print(f"Failed to reconnect, retrying - {mac_dict[self.mac_address]}")
                continue

    def initiateHandshake(self):
        # print(f"Sending Handshake to Beetle - {mac_dict[self.mac_address]}")
        self.peripheral.writeCharacteristic(self.char_handle, val=bytes('H', 'utf-8'))

    def run(self):
        # this is to make sure no double handshake is sent upon turning off and on the Beetle
        if self.receive_time == 0:
            self.receive_time = time.perf_counter()

        # if laptop hasn't received data from Beetle in a while, try reset the Beetle
        if time.perf_counter() - self.receive_time > Beetle.TIMEOUT:
            self.handshake_done = False
            # self.buffer = bytes(0)

            print(f"Timeout, reconnecting to Beetle - {mac_dict[self.mac_address]}")
            raise BTLEException

        self.setCanEnqueue()
        self.waitForNotifications()

    def checkBuffer(self, data):
        # received data at this time
        self.receive_time = time.perf_counter()

        self.buffer += data
        if len(self.buffer) >= self.PACKET_SIZE:
            self.handleData(self.buffer[:self.PACKET_SIZE])
            self.buffer = self.buffer[self.PACKET_SIZE:]

    def handleData(self, data):
        # for debugging
        # print(f'Raw bytes received from {mac_dict[self.mac_address]}:', data)

        # drop corrupted packets
        if packetize.isInvalidPacket(data):
            return

        packet_attr = packetize.deserialize(data)
        # print(f'Packet attributes: {packet_attr} - {mac_dict[self.mac_address]}')
        packet_type = packet_attr[0]

        if packet_type == TPacketType.PACKET_TYPE_DATA.value:
            if not self.start_time:
                self.start_time = time.perf_counter()

            self.processData(packet_attr)
        elif packet_type == TPacketType.PACKET_TYPE_ACK.value and not self.handshake_done:
            # print(f"Received Ack from Beetle - {mac_dict[self.mac_address]}")
            self.sendHandshakeAck()
            # print(f"Three-way Handshake complete! Ready to receive data - {mac_dict[self.mac_address]}")
            self.handshake_done = True

    def processData(self, packet_attr):
        # for throughput calculation
        self.num_packets_received += 1
        # self.showThroughput()

        self.ack_seqnum = packet_attr[1]
        self.packet_attr = packet_attr

        self.enqueueData()

        # write data to csv file for AI component
        # if self.device_id == IMU and self.num_rows <= 200:
        #    processed_gyro_data = tuple(map(lambda x: x / 131, list(packet_attr[6:9])))
        #    row = [*packet_attr[9:12], *processed_gyro_data]
        #    self.csv_writer.writerow(row)
        #    self.num_rows += 1

    def enqueueData(self):
        # print(f"Current queue size: {self.queue.qsize()}")

        # Don't enqueue unless all beetles are connected
        if not self.can_enqueue_data:
            # print(f"Cannot enqueue because not all Beetles are connected - {mac_dict[self.mac_address]}")
            return

        # Don't enqueue if no shot was sent
        if self.device_id == EMITTER and not self.packet_attr[4]:
            return

        # Don't enqueue if no shot was received
        if self.device_id == RECEIVER and not self.packet_attr[5]:
            return

        self.queue.put(self.packet_attr)
        # print(f"Enqueued data: {self.packet_attr} - {mac_dict[self.mac_address]}")

    def sendHandshakeAck(self):
        self.peripheral.writeCharacteristic(self.char_handle, val=bytes('A', 'utf-8'))

    def sendNack(self):
        self.peripheral.writeCharacteristic(self.char_handle, val=bytes('N', 'utf-8'))

    def incrementPlayerBeetleCount(self):
        if self.player_id == PLAYER_ONE:
            p1_connected_beetles.value += 1
        elif self.player_id == PLAYER_TWO:
            p2_connected_beetles.value += 1

    def decrementPlayerBeetleCount(self):
        if self.player_id == PLAYER_ONE:
            p1_connected_beetles.value -= 1
        elif self.player_id == PLAYER_TWO:
            p2_connected_beetles.value -= 1

    def allPlayerBeetlesConnected(self):
        if self.player_id == PLAYER_ONE:
            return p1_connected_beetles.value == NUM_BEETLES_PER_PLAYER
        elif self.player_id == PLAYER_TWO:
            return p2_connected_beetles.value == NUM_BEETLES_PER_PLAYER

    def showThroughput(self):
        self.end_time = time.perf_counter()
        total_time = self.end_time - self.start_time
        throughput = self.num_packets_received / total_time

        print(f"Time elapsed:", "{:.2f},".format(total_time))
        # print(f"Received {self.num_packets_received} packets - {mac_dict[self.mac_address]}")
        # print(f"Dropped {self.num_packets_dropped} packets - {mac_dict[self.mac_address]}")
        # print(f"{self.num_packets_fragmented} packets fragmented - {mac_dict[self.mac_address]}")
        print(f"Throughput of Beetle - {mac_dict[self.mac_address]} =", "{:.3f}".format(throughput), "packets/s")
