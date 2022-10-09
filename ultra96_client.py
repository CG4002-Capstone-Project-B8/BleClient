from dotenv import load_dotenv
import sshtunnel
import os
import socket
import logging
from relay_packet import RelayPacket

NUM_BEETLES_PER_PLAYER = 3


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

    def run(self):
        self.tunnelToUltra96()
        # while True:
            # self.sendPackets()

    def tunnelToUltra96(self):
        with sshtunnel.open_tunnel(
                (Ultra96Client.TUNNEL_DOMAIN_NAME, Ultra96Client.TUNNEL_PORT_NUM),
                ssh_username=self.sunfire_username,
                ssh_password=self.sunfire_passwd,
                local_bind_address=(self.data_client, self.data_client_port),  # the data sent from relay laptop to 127.0.0.1:8000 will be forwarded
                remote_bind_address=(self.data_server, self.data_server_port)  # to the ultra96
        ) as sunfire_tunnel:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                print(f'Connecting to {self.data_client}:{self.data_client_port}')
                s.connect((self.data_client, self.data_client_port))
                print(f'Connected to {self.data_server}:{self.data_server_port}')
                while True:
                    self.sendPackets(s)

    def sendPackets(self, sock):
        # print('ULTRA96_CLIENT: Running, watching player queues')
        if not self.p1_queue.empty():
            print('ULTRA96_CLIENT: Player1 queue has data')
            packet_to_send = RelayPacket()
            ble_packet_attr = self.p1_queue.get()
            packet_to_send.extractBlePacketData(ble_packet_attr)

            packet_bytes = packet_to_send.toBytes()
            packet_tuple = packet_to_send.toTuple()
            sock.sendall(packet_bytes)
            # logging.info(f'Packet sent to Ultra96: {packet_to_send.toTuple()}')
            # logging.info(f'Bytes sent to Ultra96 : {packet_to_send.toBytes()}\n')
            print(f'ULTRA96_CLIENT: Packet sent to Ultra96: {packet_tuple}')
            print(f'ULTRA96_CLIENT: Bytes sent to Ultra96 : {packet_bytes}\n')

        if not self.p2_queue.empty():
            packet_to_send = RelayPacket()
            ble_packet_attr = self.p2_queue.get()
            packet_to_send.extractBlePacketData(ble_packet_attr)

            packet_bytes = packet_to_send.toBytes()
            packet_tuple = packet_to_send.toTuple()
            sock.sendall(packet_bytes)
            # logging.info(f'Packet sent to Ultra96: {packet_to_send.toTuple()}')
            # logging.info(f'Bytes sent to Ultra96 : {packet_to_send.toBytes()}\n')
            print(f'Packet sent to Ultra96: {packet_tuple}')
            print(f'Bytes sent to Ultra96 : {packet_bytes}\n')

