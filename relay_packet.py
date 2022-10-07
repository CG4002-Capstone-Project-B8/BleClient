import struct

# device IDs
IMU = 1
EMITTER = 2
RECEIVER = 3


class RelayPacket:

    PLAYER_ID_SHIFT = 7
    SEND_SHOT_SHIFT = 6
    RECEIVE_SHOT_SHIFT = 5

    def __init__(self):
        self.details = 0
        self.gyro_data = [0.0] * 3
        self.accel_data = [0.0] * 3

    # packet attr is in the form
    # (packet_type, seqnum, player_id, device_id, sent_shot, received_shot, gyro_data[0], gyro_data[1], gyro_data[2],
    #  accel_data[0], accel_data[1], accel_data[2], checksum)
    def extractBlePacketData(self, packet_attr):
        player_id = packet_attr[2]
        self.details |= player_id << RelayPacket.PLAYER_ID_SHIFT

        device_id = packet_attr[3]
        if device_id == IMU:  # data from IMU
            self.gyro_data = list(packet_attr[6:9])
            self.processGyroData()  # perform further division of gyro data as required
            self.accel_data = packet_attr[9:12]
        elif device_id == EMITTER:  # data from emitter
            self.details |= packet_attr[4] << RelayPacket.SEND_SHOT_SHIFT
        elif device_id == RECEIVER:  # data from receiver
            self.details |= packet_attr[5] << RelayPacket.RECEIVE_SHOT_SHIFT

    def processGyroData(self):
        self.gyro_data[:] = map(lambda d: d / 16384, self.gyro_data)
        self.gyro_data = tuple(self.gyro_data)

    def toBytes(self):
        fmt = '!c6f'
        self.details = self.details.to_bytes(1, 'little')
        packet_bytes = struct.pack(fmt, self.details, *self.gyro_data, *self.accel_data)
        return packet_bytes


if __name__ == "__main__":
    packet_attr_emitter = (3, 0, 1, 2, 1, 0, 0, 0, 0, 0.0, 0.0, 0.0, b'\x01')
    packet_attr_imu = (3, 0, 1, 1, 0, 0, 32441, 1245, 14531, 4.3, -13.00, 124.5, b'\x22')
    rp = RelayPacket()
    rp.extractBlePacketData(packet_attr_emitter)
    p_bytes = rp.toBytes()
    print(f'{p_bytes}, {len(p_bytes)} bytes sent')

    data = struct.unpack('!c6f', p_bytes)
    print(data)

