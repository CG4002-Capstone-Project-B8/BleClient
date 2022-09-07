from enum import Enum


class TPacketType(Enum):
    PACKET_TYPE_HANDSHAKE = 0
    PACKET_TYPE_ACK = 1
    PACKET_TYPE_NACK = 2
    PACKET_TYPE_DATA = 3


class TClientState(Enum):
    WAIT_FOR_HANDSHAKE_ACK = 0
    SEND_ACK = 1
    WAIT_FOR_DATA = 2
