from unittest import TestCase

from strom import stream_source
from strom.model import Source
from strom import stream_transformer
from strom.model import Transformer
from strom import stream_gate
from strom.model import Gate, GateFailedException
from strom import stream_sink
from strom.model import Sink
from strom import stream_barrier
from strom.model import Barrier
from strom import Stream


class TestSource(TestCase):

    def test_creation(self):
        @stream_source(closer=lambda: False)
        def my_source(foobar=None):
            return foobar

        my_source_instance = my_source(10)

        self.assertTrue(isinstance(my_source_instance, Source))
        self.assertEqual(my_source_instance.get_frame(), 10)

    def test_all_at_once(self):
        content = list(range(10))

        @stream_source(all_at_once=True)
        def my_source():
            return content

        my_source_instance = my_source()
        self.assertEqual(my_source_instance.get_frame(), 0)
        self.assertEqual(my_source_instance.get_frame(), 1)


class TestTransformer(TestCase):

    def test_creation_named(self):
        @stream_transformer
        def add_number(frame, number=0):
            return frame + number

        my_transformer = add_number(number=42)
        self.assertTrue(isinstance(my_transformer, Transformer))
        self.assertEqual(my_transformer.transform(10), 52)

    def test_creation_unnamed(self):
        @stream_transformer
        def add_number(frame, number):
            return frame + number

        my_transformer = add_number(42)
        self.assertTrue(isinstance(my_transformer, Transformer))
        self.assertEqual(my_transformer.transform(10), 52)


class TestGate(TestCase):

    def test_default_non_fatal_gate(self):
        @stream_gate
        def check_greater_than_zero(frame):
            return frame > 0

        my_gate = check_greater_than_zero()
        self.assertTrue(isinstance(my_gate, Gate))
        self.assertEqual(my_gate.transform(10), 10)
        self.assertEqual(my_gate.transform(0), None)

    def test_non_fatal_gate(self):
        @stream_gate(fatal=False)
        def check_greater_than_zero(frame):
            return frame > 0

        my_gate = check_greater_than_zero()
        self.assertTrue(isinstance(my_gate, Gate))
        self.assertEqual(my_gate.transform(10), 10)
        self.assertEqual(my_gate.transform(0), None)

    def test_fatal_gate(self):
        @stream_gate(fatal=True)
        def check_greater_than_zero(frame):
            return frame > 0

        my_gate = check_greater_than_zero()
        self.assertTrue(isinstance(my_gate, Gate))
        self.assertEqual(my_gate.transform(10), 10)
        self.assertRaises(GateFailedException, my_gate.transform, -1)


class TestSink(TestCase):

    def test_process_calls_handler(self):
        @stream_sink
        def does_nothing(frame):
            pass

        my_sink = does_nothing()
        self.assertTrue(isinstance(my_sink, Sink))
        self.assertRaises(ValueError, my_sink.tick)

    def test_process_calls_handler(self):
        tick_mark = []
        @stream_sink
        def sets_tick_mark(frame):
            tick_mark.append(frame)

        my_sink = sets_tick_mark()
        my_sink.process(42)
        self.assertListEqual(tick_mark, [42], 'Sink did not properly process get_frame result')


class TestStream(TestCase):
    @stream_source(all_at_once=True)
    def get_the_truth(self):
        return [42]

    def test_stream_invokes_source(self):
        stream = Stream()
        stream.source = self.get_the_truth()
        self.assertEqual(stream.get_frame(), 42)

    def test_stream_invokes_transformer(self):
        frames_seen = []
        @stream_transformer
        def add_to_frames_seen(frame):
            frames_seen.append(frame)
            return frame + 10

        stream = Stream()
        stream.source = self.get_the_truth()
        stream.add(add_to_frames_seen())

        self.assertEqual(stream.get_frame(), 52)
        self.assertListEqual(frames_seen, [42])

    def test_stream_runs_to_sink(self):
        sink_result = []

        @stream_sink
        def add_to_list(frame):
            sink_result.append(frame)

        stream = Stream()
        stream.source = self.get_the_truth()
        stream.sink = add_to_list()
        stream.run()

        self.assertListEqual(sink_result, [42])

    def test_stream_split(self):
        @stream_source(all_at_once=True)
        def up_to_ten():
            return list(range(11))

        original_sink_result = []
        @stream_sink
        def add_to_original_list(frame):
            original_sink_result.append(frame)

        sink_result = []
        @stream_sink
        def add_to_list(frame):
            sink_result.append(frame)

        stream = Stream()
        stream.source = up_to_ten()
        split_stream = stream.split()
        stream.sink = add_to_original_list()

        split_stream.sink = add_to_list()

        stream.run()
        split_stream.run()

        self.assertListEqual(original_sink_result, sink_result)


class TestBarrier(TestCase):

    @stream_source(all_at_once=True)
    def source_up_to_ten(self):
        return list(range(10))

    def test_barrier_always_open(self):
        stream_a = Stream(source=self.source_up_to_ten())
        stream_b = Stream(source=self.source_up_to_ten())
        stream_b.add(stream_transformer(lambda f: f + 1)())

        @stream_barrier
        def always_open(streams):
            return True

        my_barrier = always_open(stream_a=stream_a, stream_b=stream_b)
        first_frame = my_barrier.get_frame()
        self.assertIsNotNone(first_frame)
        self.assertIn('stream_a', first_frame)
        self.assertEqual(0, first_frame['stream_a'])
        self.assertIn('stream_b', first_frame)
        self.assertEqual(1, first_frame['stream_b'])

    def test_drop_until_in_synch(self):
        @stream_transformer
        def greater_five_plus_one(frame):
            if frame < 5:
                return frame + 1
            else:
                return frame

        stream_a = Stream(source=self.source_up_to_ten())
        stream_b = Stream(source=self.source_up_to_ten())
        stream_b.add(greater_five_plus_one())

        @stream_barrier
        def drop_until_equal(streams):
            latest_frame = streams[-1]
            frame_values = list(latest_frame.values())
            master = frame_values.pop()
            all_equal = all([x == master for x in frame_values])
            if all_equal:
                return True
            else:
                streams.pop()
                return False

        my_barrier = drop_until_equal(stream_a=stream_a, stream_b=stream_b)

        # first five frames should be None
        for i in range(5):
            frame = my_barrier.get_frame()
            self.assertIsNone(frame)

        # next frames should have equal values in both streams
        for i in range(5):
            frame = my_barrier.get_frame()
            self.assertIn('stream_a', frame)
            self.assertIn('stream_b', frame)
            self.assertEqual(frame['stream_a'], frame['stream_b'])

        # after asking for ten frames the barrier should be closed
        self.assertTrue(my_barrier.is_closed())
