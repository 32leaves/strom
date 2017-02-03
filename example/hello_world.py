from strom import *

@stream_source(all_at_once=True)
def range_source(up_until=20):
    return list(range(up_until))

@stream_transformer
def add_number(frame, number=0):
    return frame + number

@stream_gate(fatal=False)
def is_even(frame):
    return frame % 2 == 0

@stream_sink
def print_sink(frame):
    print(frame)

stream = Stream()
stream.source = range_source(20)
stream.add(add_number(10))
stream.add(is_even())
stream.sink = print_sink()

if __name__ == '__main__':
    stream.run()