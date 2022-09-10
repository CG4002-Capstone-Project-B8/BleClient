import struct

from constants import TPacketType

CHECKSUM_POS = 19

PACKET_TYPE_SHIFT = 6
SEQNUM_SHIFT = 5
PLAYER_ID_SHIFT = 4
DEVICE_ID_SHIFT = 2

PACKET_TYPE_MASK = (3 << PACKET_TYPE_SHIFT)
SEQNUM_MASK = (1 << SEQNUM_SHIFT)
PLAYER_ID_MASK = (1 << PLAYER_ID_SHIFT)
DEVICE_ID_MASK = (3 << DEVICE_ID_SHIFT)


def get_checksum(byte_seq):
    checksum = b'\x00'[0]
    for b in byte_seq:
        checksum ^= b
    return checksum


def createPacket(packet_type, ack_seqnum, player_id, device_id):
    details = detailsAsBytes(packet_type.value, ack_seqnum, player_id, device_id)
    return serialize(details)


# details will be passed in as a bytes object
def serialize(details):
    # fmt = 'BBc18sc2s' - this is the format for the old packet
    fmt = 'c18sc'
    packet = struct.pack(fmt, details, bytes(18), bytes(1))

    packet_arr = bytearray(packet)
    packet_arr[CHECKSUM_POS] = get_checksum(packet[:CHECKSUM_POS])

    packet = bytes(packet_arr)
    return packet


def deserialize(packet):
    fmt = '<c3h3fc'
    packet_attr = struct.unpack(fmt, packet)

    # packet_attr returns a tuple, details is the first element ([0]) of the tuple (a bytes object)
    # to get the first (and only) byte of the bytes object, another [0] is added
    details = packet_attr[0][0]
    details = interpretDetails(details)

    # remove first element of the tuple
    packet_attr = packet_attr[1:]

    return details + packet_attr


def detailsAsBytes(packet_type, ack_seqnum, player_id, device_id):
    details = 0
    details |= packet_type << PACKET_TYPE_SHIFT
    details |= ack_seqnum << SEQNUM_SHIFT
    details |= player_id << PLAYER_ID_SHIFT
    details |= device_id << DEVICE_ID_SHIFT
    return details.to_bytes(1, 'little')


def interpretDetails(details):
    packet_type = details >> PACKET_TYPE_SHIFT
    seqnum = (details & SEQNUM_MASK) >> SEQNUM_SHIFT
    player_id = (details & PLAYER_ID_MASK) >> PLAYER_ID_SHIFT
    device_id = (details & DEVICE_ID_MASK) >> DEVICE_ID_SHIFT
    return packet_type, seqnum, player_id, device_id


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
