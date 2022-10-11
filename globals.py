from multiprocessing import Value

IMU = 1
EMITTER = 2
RECEIVER = 3
device_dict = {IMU: 'IMU', EMITTER: 'Emitter', RECEIVER: 'Receiver'}

num_currently_connected_beetles = Value('i', 0)
TOTAL_BEETLES = 1
