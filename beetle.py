from bluepy.btle import DefaultDelegate, Peripheral, BTLEException
import struct
import time
from constants import TPacketType
import packetize
import csv
from globals import num_currently_connected_beetles, TOTAL_BEETLES, device_dict, IMU, EMITTER, RECEIVER


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

        # attributes for state management and fragmentation
        self.buffer = bytes(0)
        self.current_buffer_length = 0

        # attribute for timeout
        self.send_time = time.perf_counter()

        # for measuring throughput
        self.start_time = None
        self.end_time = None
        self.num_packets_received = 0
        # self.num_packets_dropped = 0
        # self.num_packets_fragmented = 0

        # for communication with Ultra 96
        self.queue = player_queue
        self.can_enqueue_data = False
        self.packet_attr = None

        # for collection of AI data
        if self.device_id == IMU:
            self.csv_file = open('imu.csv', 'w', encoding='UTF8', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.headers = ['accX', 'accY', 'accZ', 'gyroX', 'gyroY', 'gyroZ']
            self.csv_writer.writerow(self.headers)

    def setDelegate(self, delegate):
        self.delegate = delegate

    def waitForNotifications(self):
        self.peripheral.waitForNotifications(1.5)

    def setCanEnqueue(self):
        self.can_enqueue_data = (num_currently_connected_beetles.value == TOTAL_BEETLES)

    def connect(self):
        # initiate a connection to Beetle
        self.peripheral = Peripheral(self.mac_address)

        # the above line running indicates a successful connection to the Beetle
        print(f"Connected successfully to Beetle - {device_dict[self.device_id]}")
        num_currently_connected_beetles.value += 1

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

    def resetAttributes(self):
        self.ack_seqnum = 0

        self.num_packets_received = 0
        self.start_time = 0
        self.end_time = 0

    def disconnect(self):
        self.peripheral.disconnect()
        num_currently_connected_beetles.value -= 1

    def reconnect(self):
        print(f"Attempting to reconnect to Beetle - {device_dict[self.device_id]}")
        while True:
            try:
                self.connect()
                break
            except BTLEException as e:
                print(e, "(Reconnecting...)")
                continue

    def initiateHandshake(self):
        print(f"Starting handshake with Beetle - {device_dict[self.device_id]}")

        handshake_packet_to_send = packetize.createPacket(TPacketType.PACKET_TYPE_HANDSHAKE,
                                                          self.ack_seqnum,
                                                          self.player_id,
                                                          self.device_id)
        self.peripheral.writeCharacteristic(self.char_handle, val=handshake_packet_to_send)

        self.send_time = time.perf_counter()

    def run(self):
        if time.perf_counter() - self.send_time > Beetle.TIMEOUT:
            print(f"Timeout, re-initiating handshake with Beetle - {device_dict[self.device_id]}")
            self.initiateHandshake()

        self.setCanEnqueue()
        self.waitForNotifications()

    def debugData(self, data):
        self.buffer += data

        if len(self.buffer) >= 200:
            for i in range(10):
                segment = self.buffer[i*20:(i*20 + 20)]
                self.handleData(segment)
            self.buffer = bytes(0)

    def checkBuffer(self, data):
        # buffer might be empty after the fragmentation has been handled so it is filled with the current data
        if self.current_buffer_length == 0:
            self.buffer = data
            self.current_buffer_length = len(data)

        # check if current buffer has a lack of bytes, meaning a packet has been fragmented
        deficit_length = Beetle.PACKET_SIZE - self.current_buffer_length

        # if deficit_length != 0:
        #     self.num_packets_fragmented += 1

        # negative deficit means we have extra bytes in the buffer, we want to immediately
        # clear out the buffer, reliable protocol (prevent any loss of data)
        while deficit_length < 0:
            self.handleData(self.buffer[:self.PACKET_SIZE])
            self.buffer = self.buffer[self.PACKET_SIZE:]
            deficit_length = Beetle.PACKET_SIZE - len(self.buffer)

        # add the first deficit_length bytes from data to the buffer
        self.buffer += data[:deficit_length]

        if len(self.buffer) == self.PACKET_SIZE:
            # data here has length == PACKET_SIZE, handle it
            self.handleData(self.buffer)

            # clear out the buffer
            self.buffer = self.buffer[self.PACKET_SIZE:]
            self.current_buffer_length = len(self.buffer)

        # there is excess data received which has not been processed, store it in the buffer
        if deficit_length > 0:
            self.buffer = data[deficit_length:]
            self.current_buffer_length = len(self.buffer)

    def handleData(self, data):
        # for debugging
        print(f'Raw bytes received from {device_dict[self.device_id]}:')
        print(data)

        # drop corrupted packets
        if packetize.isInvalidPacket(data):
            return

        packet_attr = packetize.deserialize(data)
        print(f'Packet attributes: {packet_attr} - {device_dict[self.device_id]}')
        packet_type = packet_attr[0]

        if packet_type == TPacketType.PACKET_TYPE_DATA.value:
            if not self.start_time:
                self.start_time = time.perf_counter()

            self.processData(packet_attr)
        elif packet_type == TPacketType.PACKET_TYPE_ACK.value:
            self.sendHandshakeAck()
            print(f"Three-way Handshake complete! Ready to receive data - {device_dict[self.device_id]}")

    def processData(self, packet_attr):
        # for throughput calculation
        self.num_packets_received += 1
        self.showThroughput()

        self.ack_seqnum = packet_attr[1]
        self.packet_attr = packet_attr

        self.enqueueData()

        # write data to csv file for AI component
        if self.device_id == IMU:
            processed_gyro_data = tuple(map(lambda x: x / 131, list(packet_attr[6:9])))
            row = [*packet_attr[9:12], *processed_gyro_data]
            self.csv_writer.writerow(row)

    def enqueueData(self):
        print(f"Current queue size: {self.queue.qsize()}")
        # Don't enqueue unless all beetles are connected
        if not self.can_enqueue_data:
            print(f"Cannot enqueue because not all Beetles are connected - {device_dict[self.device_id]}")
            return

        # Don't enqueue if no shot was sent
        if self.device_id == EMITTER and not self.packet_attr[4]:
            # print(f"Cannot enqueue because player did not send shot - {device_dict[self.device_id]}")
            return

        # Don't enqueue if no shot was received
        if self.device_id == RECEIVER and not self.packet_attr[5]:
            # print(f"Cannot enqueue because player did not get shot - {device_dict[self.device_id]}")
            return

        self.queue.put(self.packet_attr)
        print(f"Enqueued data: {self.packet_attr} - {device_dict[self.device_id]}")

    def sendHandshakeAck(self):
        ack_packet_to_send = packetize.createPacket(TPacketType.PACKET_TYPE_ACK,
                                                    self.ack_seqnum,
                                                    self.player_id,
                                                    self.device_id)
        self.peripheral.writeCharacteristic(self.char_handle, val=ack_packet_to_send)

        self.send_time = time.perf_counter()

    def sendNack(self):
        nack_packet_to_send = packetize.createPacket(TPacketType.PACKET_TYPE_NACK,
                                                     self.ack_seqnum,
                                                     self.player_id,
                                                     self.device_id)
        self.peripheral.writeCharacteristic(self.char_handle, val=nack_packet_to_send)

        self.send_time = time.perf_counter()

    def showThroughput(self):
        self.end_time = time.perf_counter()
        total_time = self.end_time - self.start_time
        throughput = (self.num_packets_received * Beetle.PACKET_SIZE * 8) / (1000 * total_time)

        print(f"Time elapsed:", "{:.2f},".format(total_time))
        print(f"Received {self.num_packets_received} packets - {device_dict[self.device_id]}")
        # print(f"Dropped {self.num_packets_dropped} packets - {device_dict[self.device_id]}")
        # print(f"{self.num_packets_fragmented} packets fragmented - {device_dict[self.device_id]}")
        print(f"Throughput of Beetle - {device_dict[self.device_id]} =", "{:.3f}".format(throughput), "kbps")
