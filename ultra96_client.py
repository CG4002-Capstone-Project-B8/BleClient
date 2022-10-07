from dotenv import load_dotenv
import sshtunnel
import os
import socket
from consolidated_packet import ConsolidatedPacket

NUM_BEETLES_PER_PLAYER = 3


class Client:

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

    def run(self):
        self.tunnel_to_ultra96()

    def tunnel_to_ultra96(self):
        with sshtunnel.open_tunnel(
                (Client.TUNNEL_DOMAIN_NAME, Client.TUNNEL_PORT_NUM),
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
        if self.p1_queue.qsize() >= NUM_BEETLES_PER_PLAYER:
            cp1 = ConsolidatedPacket()
            for _ in range(NUM_BEETLES_PER_PLAYER):
                ble_packet_attr = self.p1_queue.get_nowait()
                cp1.extractBlePacketData(ble_packet_attr)
            sock.sendall(cp1.toBytes())

        if self.p2_queue.qsize() >= NUM_BEETLES_PER_PLAYER:
            cp2 = ConsolidatedPacket()
            for _ in range(NUM_BEETLES_PER_PLAYER):
                ble_packet_attr = self.p1_queue.get_nowait()
                cp2.extractBlePacketData(ble_packet_attr)
            sock.sendall(cp2.toBytes())
