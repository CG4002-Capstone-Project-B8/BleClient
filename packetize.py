import struct

from constants import TPacketType

CHECKSUM_POS = 19

PACKET_TYPE_SHIFT = 6
SEQNUM_SHIFT = 5
PLAYER_ID_SHIFT = 4
DEVICE_ID_SHIFT = 2
SEND_SHOT_SHIFT = 1
RECEIVE_SHOT_SHIFT = 0

PACKET_TYPE_MASK = (3 << PACKET_TYPE_SHIFT)
SEQNUM_MASK = (1 << SEQNUM_SHIFT)
PLAYER_ID_MASK = (1 << PLAYER_ID_SHIFT)
DEVICE_ID_MASK = (3 << DEVICE_ID_SHIFT)
SEND_SHOT_MASK = (0x01 << SEND_SHOT_SHIFT)
RECEIVE_SHOT_MASK = (0x01 << RECEIVE_SHOT_SHIFT)


def getChecksum(byte_seq):
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

    # debugging purposes only
    print("Sending: ", interpretDetails(details[0]))

    packet_arr = bytearray(packet)
    packet_arr[CHECKSUM_POS] = getChecksum(packet[:CHECKSUM_POS])

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

    # new bits introduced for status of player
    sent_shot = (details & SEND_SHOT_MASK) >> SEND_SHOT_SHIFT
    if sent_shot:
        print("Sent shot!\n")

    received_shot = (details & RECEIVE_SHOT_MASK) >> RECEIVE_SHOT_SHIFT
    if received_shot:
        print("Received shot!\n")

    return packet_type, seqnum, player_id, device_id, sent_shot, received_shot


def isInvalidPacket(data):
    # packet_type = data[0] >> PACKET_TYPE_SHIFT
    # if isInvalidPacketType(packet_type):
    #    print("Invalid packet type")
    #    return False

    # if getChecksum(data) != 0:
    #    print("Invalid checksum")
    #    return False

    return False


def isInvalidPacketType(packet_type):
    valid_types = [TPacketType.PACKET_TYPE_ACK.value, TPacketType.PACKET_TYPE_DATA.value]
    return packet_type not in valid_types
