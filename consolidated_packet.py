import struct

# device IDs
IMU = 1
EMITTER = 2
RECEIVER = 3


class ConsolidatedPacket:

    PLAYER_ID_SHIFT = 7
    SEND_SHOT_SHIFT = 6
    RECEIVE_SHOT_SHIFT = 5

    def __init__(self):
        self.details = 0
        self.gyro_data = [None] * 3
        self.accel_data = [None] * 3

    def extractBlePacketData(self, packet_attr):
        player_id = packet_attr[2]
        self.details |= player_id << ConsolidatedPacket.PLAYER_ID_SHIFT

        device_id = packet_attr[3]

        # data from IMU
        if device_id == IMU:
            self.gyro_data = list(packet_attr[6:9])
            self.processGyroData()  # perform further division of gyro data as required

            self.accel_data = packet_attr[9:12]
        # data from emitter
        elif device_id == EMITTER:
            self.details |= packet_attr[4] << ConsolidatedPacket.SEND_SHOT_SHIFT
        # data from receiver
        elif device_id == RECEIVER:
            self.details |= packet_attr[5] << ConsolidatedPacket.RECEIVE_SHOT_SHIFT

    def processGyroData(self):
        self.gyro_data[:] = map(lambda d: d / 16384, self.gyro_data)
        self.gyro_data = tuple(self.gyro_data)

    def toBytes(self):
        fmt = 'c6f'
        self.details = self.details.to_bytes(1, 'little')
        packet_bytes = struct.pack(fmt, self.details, *self.gyro_data, *self.accel_data)
        return packet_bytes

