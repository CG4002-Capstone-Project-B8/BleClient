from bluepy.btle import BTLEException
from beetle import Beetle, BeetleDelegate
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# get the MAC addresses here and separate them into player 1 and player 2
# in the order: Player1 -> Player 2, IMU -> Emitter -> Receiver
BEETLE_ADDRESSES = [["d0:39:72:bf:c3:d1", "d0:39:72:bf:cd:1e", "c4:be:84:20:1a:0c"],
                    ["d0:39:72:bf:c3:d1"]]

PLAYER_ONE = 0
PLAYER_TWO = 1

PLAYER_ONE_BEETLES = BEETLE_ADDRESSES[0]
PLAYER_TWO_BEETLES = BEETLE_ADDRESSES[1]


def beetle_thread(beetle_address, player_id, device_id):
    beetle = Beetle(beetle_address, player_id, device_id)
    beetle.setDelegate(BeetleDelegate(beetle))

    print(f"Connecting to Beetle - {beetle_address}")
    while True:
        try:
            beetle.connect()
            break
        except BTLEException as e:
            # print(e)
            print(f"Failed to connect - {beetle_address}, retrying")
            continue

    while True:
        try:
            beetle.run()
        except BTLEException as e:
            print(e, f'- {beetle_address}')
            beetle.resetAttributes()
            beetle.disconnect()
            beetle.reconnect()


def player_process(player_id, player_beetle_addresses):
    with ThreadPoolExecutor(max_workers=len(player_beetle_addresses)) as beetle_thread_executor:
        for i, beetle_address in enumerate(player_beetle_addresses):
            device_id = i + 1
            beetle_thread_executor.submit(beetle_thread, beetle_address, player_id, device_id)


if __name__ == "__main__":
    # with ProcessPoolExecutor(max_workers=2) as process_executor:
    #     process_executor.map(player_process, BEETLE_ADDRESSES)
    # beetle_thread("d0:39:72:bf:c3:d1", 0, 1)
    # beetle_thread("d0:39:72:bf:cd:1e", 0, 2)
    # beetle_thread("c4:be:84:20:1a:0c", 0, 3)
    player_process(PLAYER_ONE, PLAYER_ONE_BEETLES)

    # here we start another process which sends the data to the Ultra 96
