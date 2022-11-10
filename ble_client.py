from bluepy.btle import BTLEException
from beetle import Beetle, BeetleDelegate
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Queue, Process
from ultra96_client import Ultra96Client
from globals import p1_connected_beetles, p2_connected_beetles, BEETLE_ADDRESSES, mac_dict, PLAYER_ONE, PLAYER_TWO, is_connected_to_u96
import time

PLAYER_ONE_BEETLES = BEETLE_ADDRESSES[0]
PLAYER_TWO_BEETLES = BEETLE_ADDRESSES[1]


def beetle_thread(beetle_address, player_id, device_id, player_queue):
    beetle = Beetle(beetle_address, player_id, device_id, player_queue)
    beetle.setDelegate(BeetleDelegate(beetle))

    print(f"Connecting to Beetle - {mac_dict[beetle_address]}")
    while True:
        try:
            beetle.connect()
            break
        except BTLEException as e:
            print(f"Failed to connect - {mac_dict[beetle_address]}, retrying")
            time.sleep(1)
            continue

    while True:
        try:
            while True:
                beetle.run()
                print(f'P1: {p1_connected_beetles.value} beetles , P2: {p2_connected_beetles.value} beetles')
        except BTLEException as e:
            print(f'Beetle disconnected - {mac_dict[beetle_address]}')
            beetle.disconnect()
            beetle.reconnect()
        except KeyboardInterrupt as kbi:
            print(f"Exiting - {mac_dict[beetle_address]}")
            beetle.disconnect()
            exit()           


def player_process(player_id, player_beetle_addresses, player_queue):
    with ThreadPoolExecutor(max_workers=len(player_beetle_addresses)) as beetle_thread_executor:
        for i, beetle_address in enumerate(player_beetle_addresses):
            device_id = i + 1
            beetle_thread_executor.submit(beetle_thread, beetle_address, player_id, device_id, player_queue)


def client_process(player_one_queue, player_two_queue):
    ultra96_client = Ultra96Client(player_one_queue, player_two_queue)
    ultra96_client.run()


def main():
    print("Starting game...")
    p1_queue = Queue()
    p2_queue = Queue()

    p1 = Process(target=player_process, args=(PLAYER_ONE, PLAYER_ONE_BEETLES, p1_queue))
    p2 = Process(target=player_process, args=(PLAYER_TWO, PLAYER_TWO_BEETLES, p2_queue))
    u96 = Process(target=client_process, args=(p1_queue, p2_queue))

    print("Starting process for Ultra96 Client")
    u96.start()

    # don't connect to the Beetles until connection to the Ultra96 server is successful
    while not is_connected_to_u96.value:
        time.sleep(0.5)

    print("Starting process for Player 1")
    p1.start()

    print("Starting process for Player 2")
    p2.start()

    u96.join()
    p1.join()
    p2.join()


if __name__ == "__main__":
    main()
