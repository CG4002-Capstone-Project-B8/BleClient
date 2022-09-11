from bluepy.btle import DefaultDelegate, Peripheral, BTLEException
import struct
from constants import TPacketType, TClientState
import packetize


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

    def __init__(self, macAddress, player_id, device_id):
        self.mac_address = macAddress
        self.char_handle = None
        self.delegate = None
        self.peripheral = None

        self.ack_seqnum = 0
        self.player_id = player_id
        self.device_id = device_id

        self.accel_data = [None] * 3
        self.gyro_data = [None] * 3

        self.state = TClientState.WAIT_FOR_HANDSHAKE_ACK
        self.buffer = bytes(0)
        self.current_buffer_length = 0

    def setDelegate(self, delegate):
        self.delegate = delegate

    def waitForNotifications(self):
        self.peripheral.waitForNotifications(1.0)

    def connect(self):
        self.peripheral = Peripheral(self.mac_address)

        serial_service = self.peripheral.getServiceByUUID(Beetle.SERIAL_SERVICE_UUID)
        serial_char = serial_service.getCharacteristics(Beetle.SERIAL_CHAR_UUID)[0]
        serial_char_handle = serial_char.getHandle()
        self.char_handle = serial_char_handle

        self.peripheral.writeCharacteristic(serial_char_handle, Beetle.NOTIFICATIONS_ON, True)
        self.peripheral.setDelegate(self.delegate)
        self.initiateHandshake()

    def disconnect(self):
        self.peripheral.disconnect()

    def reconnect(self):
        print(f"Attempting to reconnect to Beetle - {self.mac_address}")
        while True:
            try:
                self.connect()
                break
            except BTLEException as btle_ex:
                print(btle_ex, " (reconnecting)")
                continue

    def initiateHandshake(self):
        print(f"Starting handshake with Beetle - {self.mac_address}")

        handshake_packet_to_send = packetize.createPacket(TPacketType.PACKET_TYPE_HANDSHAKE,
                                                          self.ack_seqnum,
                                                          self.player_id,
                                                          self.device_id)
        self.peripheral.writeCharacteristic(self.char_handle, val=handshake_packet_to_send)

    def run(self):
        while True:
            # if self.state == TClientState.WAIT_FOR_HANDSHAKE_ACK:
            #     print(f"Starting handshake with Beetle - {self.mac_address}")
            # self.initiateHandshake()
            self.waitForNotifications()

    def debugData(self, data):
        self.buffer += data

        if len(self.buffer) >= 200:
            for i in range(10):
                segment = self.buffer[i*20:(i*20 + 20)]
                self.handleData(segment)
            self.buffer = bytes(0)

    def checkBuffer(self, data):
        if self.current_buffer_length == 0:
            self.buffer = data
            self.current_buffer_length = len(data)

        deficit_length = Beetle.PACKET_SIZE - self.current_buffer_length

        # negative deficit means we have extra bytes in the buffer, we want to immediately
        # clear out the buffer, reliable protocol (prevent any loss of data)
        while deficit_length < 0:
            self.handleData(self.buffer[:self.PACKET_SIZE])
            self.buffer = self.buffer[self.PACKET_SIZE:]
            deficit_length = Beetle.PACKET_SIZE - len(self.buffer)

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
        # if self.state != TClientState.WAIT_FOR_DATA:
        #     print("Not waiting for data in this state")
        #     return

        # for debugging
        print(f'Packet received from {self.mac_address}:')
        print(data)

        if packetize.isInvalidPacket(data):
            self.sendNack()
            return
        else:
            # deserialize data, get a tuple
            packet_attr = packetize.deserialize(data)
            print(f'Packet attributes: {packet_attr}')
            packet_type = packet_attr[0]

            self.state = TClientState.SEND_ACK
            if packet_type == TPacketType.PACKET_TYPE_DATA.value:
                self.processData(packet_attr)
                self.sendAck()
            elif packet_type == TPacketType.PACKET_TYPE_ACK.value:
                self.sendAck()
                print("Three-way Handshake complete!")

    def processData(self, packet_attr):
        self.ack_seqnum = packet_attr[1]

        accel_data = list(packet_attr[4:7])
        self.accel_data = accel_data

        gyro_data = list(packet_attr[7:10])
        self.gyro_data = gyro_data

        # Sending of data to Ultra96 (enqueueing to Queue) will be done here

    def sendAck(self):
        if self.state != TClientState.SEND_ACK:
            print("Unable to send ACK in this state")
            return

        ack_packet_to_send = packetize.createPacket(TPacketType.PACKET_TYPE_ACK,
                                                    self.ack_seqnum,
                                                    self.player_id,
                                                    self.device_id)
        self.peripheral.writeCharacteristic(self.char_handle, val=ack_packet_to_send)

        self.state = TClientState.WAIT_FOR_DATA

    def sendNack(self):
        nack_packet_to_send = packetize.createPacket(TPacketType.PACKET_TYPE_NACK,
                                                     self.ack_seqnum,
                                                     self.player_id,
                                                     self.device_id)
        self.peripheral.writeCharacteristic(self.char_handle, val=nack_packet_to_send)
