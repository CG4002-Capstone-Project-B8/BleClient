from multiprocessing import Value

# get the MAC addresses here and separate them into player 1 and player 2
# in the order: Player1 -> Player 2, IMU -> Emitter -> Receiver
BEETLE_ADDRESSES = [["d0:39:72:bf:c3:d1", "d0:39:72:bf:bf:f6", "d0:39:72:bf:c3:90"],
                    ["c4:be:84:20:1a:0c", "d0:39:72:bf:cd:1e", "d0:39:72:bf:bd:d4"]]

mac_dict = {BEETLE_ADDRESSES[0][0]: 'Player 1 IMU',      BEETLE_ADDRESSES[0][1]: 'Player 1 Emitter',
            BEETLE_ADDRESSES[0][2]: 'Player 1 Receiver', BEETLE_ADDRESSES[1][0]: 'Player 2 IMU',
            BEETLE_ADDRESSES[1][1]: 'Player 2 Emitter',  BEETLE_ADDRESSES[1][2]: 'Player 2 Receiver'}

IMU = 1
EMITTER = 2
RECEIVER = 3
device_dict = {IMU: 'IMU', EMITTER: 'Emitter', RECEIVER: 'Receiver'}

num_currently_connected_beetles = Value('i', 0)
TOTAL_BEETLES = 3
