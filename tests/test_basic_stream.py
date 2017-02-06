from unittest import TestCase
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


class TestBasicStream(TestCase):

    def test_basic_stream(self):
        sink_result = []

        @stream_sink
        def add_to_result(frame):
            sink_result.append(frame)

        stream = Stream()
        stream.source = range_source(20)
        stream.add(add_number(10))
        stream.add(is_even())
        stream.sink = add_to_result()
        stream.run()

        self.assertListEqual(sink_result, [10, 12, 14, 16, 18, 20, 22, 24, 26, 28])