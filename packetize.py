import struct

from constants import TPacketType

CHECKSUM_POS = 21


def get_checksum(byte_seq):
    checksum = b'\x00'[0]
    for b in byte_seq:
        checksum ^= b
    return checksum


# packet_type will be passed in as TPacketType.value, ack_seqnum is 0 or 1 and player_device_id will be b'\x01'
def serialize(packet_type, ack_seqnum, player_device_id):
    fmt = 'BBc18sc2s'
    packet = struct.pack(fmt, packet_type, ack_seqnum, player_device_id, bytes(18), bytes(1), bytes(2))

    packet_arr = bytearray(packet)
    packet_arr[CHECKSUM_POS] = get_checksum(packet[:CHECKSUM_POS])

    packet = bytes(packet_arr)
    return packet


def deserialize(packet):
    fmt = '<BBc3h3fc2s'
    return struct.unpack(fmt, packet)


def isInvalidPacket(data):
    packet_type = data[0]
    if isInvalidPacketType(packet_type):
        print("Invalid packet type")
        return True

    expected_checksum = get_checksum(data[:CHECKSUM_POS])
    received_checksum = data[CHECKSUM_POS]
    if received_checksum != expected_checksum:
        print("Invalid checksum")
        return True

    return False


def isInvalidPacketType(packet_type):
    valid_types = [t.value for t in TPacketType]
    return packet_type not in valid_types
