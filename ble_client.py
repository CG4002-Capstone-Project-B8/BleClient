from bluepy.btle import BTLEException
from beetle import Beetle, BeetleDelegate
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# get the MAC addresses here and separate them into player 1 and player 2
BEETLE_ADDRESSES = [["d0:39:72:bf:c3:d1"], ["d0:39:72:bf:c3:d1"]]


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

    print(f"Connected successfully to Beetle - {beetle_address}")

    while True:
        try:
            beetle.run()
        except BTLEException as e:
            print(e)
            beetle.disconnect()
            beetle.reconnect()


def player_process(player_beetle_addresses):
    with ThreadPoolExecutor(max_workers=len(player_beetle_addresses)) as beetle_thread_executor:
        beetle_thread_executor.map(beetle_thread, player_beetle_addresses)


if __name__ == "__main__":
    # with ProcessPoolExecutor(max_workers=2) as process_executor:
    #     process_executor.map(player_process, BEETLE_ADDRESSES)
    beetle_thread("d0:39:72:bf:c3:d1", 0, 1)

    # here we start another process which sends the data to the Ultra 96
