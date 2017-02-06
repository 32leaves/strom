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

@stream_barrier
def pass_on_barrier(frames):
    return True

initial_stream = Stream()
initial_stream.source = range_source(20)
initial_stream.add(add_number(10))

even_stream = initial_stream.split()
even_stream.add(is_even())

all_streams_barrier = pass_on_barrier(all_numbers=initial_stream, even_numbers=even_stream)
result_stream = Stream()
result_stream.source = all_streams_barrier
result_stream.sink = print_sink()

stream = result_stream

if __name__ == '__main__':
    stream.run()