from dotenv import load_dotenv
import sshtunnel
import os
import socket
import time
from globals import IMU, EMITTER, RECEIVER
from math import sqrt
from relay_packet import RelayPacket

MAGNITUDE_THRESHOLD = 1.5
NUM_PACKETS = 50


class Ultra96Client:

    TUNNEL_DOMAIN_NAME = 'stu.comp.nus.edu.sg'
    TUNNEL_PORT_NUM = 22

    def __init__(self, player_one_queue, player_two_queue):
        load_dotenv()

        # initialize Sunfire credentials
        self.sunfire_username = os.environ.get('SUNFIRE_USERNAME')
        self.sunfire_passwd = os.environ.get('SUNFIRE_PASSWD')

        # initialize data server credentials
        self.data_server = os.environ.get('DATA_SERVER')
        self.data_server_port = int(os.environ.get('DATA_SERVER_PORT'))

        # initialize data client credentials
        self.data_client = os.environ.get('DATA_CLIENT')
        self.data_client_port = int(os.environ.get('DATA_CLIENT_PORT'))

        # initialize data queues
        self.p1_queue = player_one_queue
        self.p2_queue = player_two_queue

        # configure log files
        # logging.basicConfig(filename="ultra96_logs.txt", level=logging.INFO, filemode="w", format="%(message)s")
        self.p1_can_send = False
        self.p1_counter = 0
        self.p2_can_send = False
        self.p2_counter = 0

    def run(self):
        # self.tunnelToUltra96()
        self.runInDebugMode()

    def runInDebugMode(self):
        while True:
            self.debugQueues()

    def tunnelToUltra96(self):
        print('Opening SSH tunnel...')
        with sshtunnel.open_tunnel(
                (Ultra96Client.TUNNEL_DOMAIN_NAME, Ultra96Client.TUNNEL_PORT_NUM),
                ssh_username=self.sunfire_username,
                ssh_password=self.sunfire_passwd,
                local_bind_address=(self.data_client, self.data_client_port),  # the data sent from relay laptop to 127.0.0.1:8000 will be forwarded
                remote_bind_address=(self.data_server, self.data_server_port)  # to the ultra96
        ) as sunfire_tunnel:
            while True:  # reconnect when server shuts down
                while True:  # reconnect until data_server is reachable
                    sunfire_tunnel.check_tunnels()
                    if not (False in sunfire_tunnel.tunnel_is_up.values()):
                        break
                    print(f'data_server is not reachable, retrying...')
                    time.sleep(1)
                    sunfire_tunnel.restart()

                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        print(f'Connecting to {self.data_client}:{self.data_client_port}')
                        s.connect((self.data_client, self.data_client_port))
                        print(f'Connected to {self.data_server}:{self.data_server_port}')
                        while True:
                            self.checkPlayerQueues(s)
                except BrokenPipeError:
                    print('data_server closed connection. Trying to reconnect...')

    def checkPlayerQueues(self, sock):
        if not self.p1_queue.empty():
            print('ULTRA96_CLIENT: Player1 queue has data')
            p1_packet, p1_device_id = extractFromQueue(self.p1_queue)

            if p1_device_id == EMITTER or p1_device_id == RECEIVER:
                sendPacket(sock, p1_packet)
                return

            if not self.p1_can_send and p1_device_id == IMU:
                accel_x, accel_y, accel_z = p1_packet.accel_data
                accel_magnitude = calculateAccelMagnitude(accel_x, accel_y, accel_z)

                if accel_magnitude > MAGNITUDE_THRESHOLD:
                    self.p1_can_send = True

            if self.p1_can_send and self.p1_counter < NUM_PACKETS:
                sendPacket(sock, p1_packet)
                self.p1_counter += 1
                if self.p1_counter >= NUM_PACKETS:
                    self.p1_can_send = False
                    self.p1_counter = 0

        if not self.p2_queue.empty():
            print('ULTRA96_CLIENT: Player2 queue has data')
            p2_packet, p2_device_id = extractFromQueue(self.p2_queue)

            if p2_device_id == EMITTER or p2_device_id == RECEIVER:
                sendPacket(sock, p2_packet)
                return

            if not self.p2_can_send and p2_device_id == IMU:
                accel_x, accel_y, accel_z = p2_packet.accel_data
                accel_magnitude = calculateAccelMagnitude(accel_x, accel_y, accel_z)

                if accel_magnitude > MAGNITUDE_THRESHOLD:
                    self.p2_can_send = True

            if self.p2_can_send and self.p2_counter < NUM_PACKETS:
                sendPacket(sock, p2_packet)
                self.p2_counter += 1
                if self.p2_counter >= NUM_PACKETS:
                    self.p2_can_send = False
                    self.p2_counter = 0

    def debugQueues(self):
        if not self.p1_queue.empty():
            print('ULTRA96_CLIENT: Player1 queue has data')
            p1_packet, p1_device_id = extractFromQueue(self.p1_queue)
            printPacket(p1_packet)

        if not self.p2_queue.empty():
            print('ULTRA96_CLIENT: Player2 queue has data')
            p2_packet, p2_device_id = extractFromQueue(self.p2_queue)
            printPacket(p2_packet)


def extractFromQueue(player_queue):
    packet_to_send = RelayPacket()
    ble_packet_attr = player_queue.get()

    device_id = ble_packet_attr[3]
    packet_to_send.extractBlePacketData(ble_packet_attr)
    return packet_to_send, device_id


def sendPacket(sock, packet_to_send):
    packet_bytes = packet_to_send.toBytes()
    packet_tuple = packet_to_send.toTuple()

    # if len(test_queue) < 200:
    #     test_queue.append(packet_tuple)
    # elif not has_saved:
    #     d = np.array(test_queue)
    #     np.save('relay_imu_data', d)
    #     has_saved = True

    sock.sendall(packet_bytes)

    print(f'ULTRA96_CLIENT: Packet sent to Ultra96: {packet_tuple}')
    print(f'ULTRA96_CLIENT: Bytes sent to Ultra96 : {packet_bytes}\n')


def printPacket(packet_to_send):
    print(f'ULTRA96_CLIENT: Packet sent to Ultra96: {packet_to_send.toTuple()}')
    print(f'ULTRA96_CLIENT: Bytes sent to Ultra96 : {packet_to_send.toBytes()}\n')


def calculateAccelMagnitude(x, y, z):
    return sqrt((x * x) + (y * y) + (z * z))
