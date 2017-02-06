import inspect
from queue import Queue
import functools


class PipelineElement:
    """Pipeline elements are the objects which constitute a pipeline. Please see the documentation of strom.py for more
    details about this concept.
    """
    def __init__(self, handler, args, kwargs):
        self._handler = handler
        self._handler_args = args
        self._handler_kwargs = kwargs

    def call_handler(self, *args):
        # if the handler's first argument is called self, then chances are we've decorated a class method which expects
        # the object instance as first parameter. Let's make sure it gets that one.
        args_for_handler = []
        handler_signature = inspect.signature(self._handler, follow_wrapped=False)
        if 'self' in handler_signature.parameters:
            args_head, *args_tail = self._handler_args
            args_for_handler = [args_head] + list(args) + args_tail
        else:
            args_for_handler = args + self._handler_args

        return self._handler(*args_for_handler, **self._handler_kwargs)

    def __str__(self):
        return super().__str__() if self._handler is None else self._handler.__name__


class Stream(PipelineElement):
    """A stream collects, transports and transforms data maintained in frames.
    """

    def __init__(self, name=None, source=None, sink=None):
        """Creates a new stream from a source
        """
        self.name = name
        self.source = source
        self.sink = sink
        self.elements = []

    def __str__(self):
        if self.name is None:
            return "Stream->%s" % str(self.source)
        else:
            return self.name

    def add(self, element):
        """Adds an element (transformer or gate) to the stream.
        """
        self.elements.append(element)

    def get_frame(self):
        """Asks the source for another frame, floats is through transformer, gates and other stream elements and returns
         it. Calling this method on a closed stream will raise an exception.
        """
        frame = self.source.get_frame()

        # transform frame with all elements
        for element in self.elements:
            if frame is None: break
            frame = element.transform(frame)

        return frame

    def is_closed(self):
        """Checks if the source can deliver any more frames."""
        return self.source.is_closed()

    def split(self):
        class SplitSourceContext:
            def __init__(self, origin):
                self.frames = Queue()
                self._origin = origin

            def closer(self):
                return self._origin.is_closed() and self.frames.empty()

            def source(self):
                return self.frames.get_nowait()

            @stream_transformer
            def transformer(self, frame):
                self.frames.put_nowait(frame)
                return frame

        my_split = SplitSourceContext(self)
        split_transformer = my_split.transformer()
        split_transformer.is_split_stream = True
        self.add(split_transformer)
        result = Stream()
        result.source = stream_source(my_split.source, all_at_once=False, closer=my_split.closer)()
        result.source.is_split_source = True
        split_transformer.split_stream = result
        return result

    def run(self):
        """Processes all frames the source is willing to give, meaning this method calls get_frame and feeds it to the
        sink until the source is closed.
        """
        while not self.is_closed():
            frame = self.get_frame()
            if frame is not None:
                self.sink.process(frame)


class SourceIsClosedException(Exception):
    """Exception used to denote that a source can no longer deliver frames."""
    pass


def stream_source(method=None, all_at_once=False, closer=None):
    # If called without method, we've been called with optional arguments.
    # We return a decorator with the optional arguments filled in.
    # Next time round we'll be decorating method.
    if method is None:
        return functools.partial(stream_source, all_at_once=all_at_once, closer=closer)
    @functools.wraps(method)
    def f(*args, **kwargs):
        return Source(method, args, kwargs, all_at_once, closer)
    return f


class Source(PipelineElement):
    """A source delivers frames into a stream."""

    def __init__(self, handler, args, kwargs, all_at_once=False, closer=None):
        super().__init__(handler, args, kwargs)
        self.all_at_once = all_at_once
        self.closer = closer
        self._data = None
        if not all_at_once and closer is None:
            raise ValueError('Sources which are not all_at_once must have a closer')

    def is_closed(self):
        """Determines if this source can deliver any more frames. Once a source is closed, it must not re-open again."""
        if self.all_at_once:
            return not(self._data is None or self._data)
        else:
            return self.closer()

    def get_frame(self):
        """Returns another frame. This method may block until the next frame becomes available. Calling this method on
        a closed source raises an exception.
        """
        if self.is_closed():
            raise SourceIsClosedException()

        if self.all_at_once:
            if self._data is None:
                self._data = self.call_handler()
            return self._data.pop(0)
        else:
            return self.call_handler()


def stream_sink(method=None):
    # If called without method, we've been called with optional arguments.
    # We return a decorator with the optional arguments filled in.
    # Next time round we'll be decorating method.
    if method is None:
        return functools.partial(stream_sink)
    @functools.wraps(method)
    def f(*args, **kwargs):
        return Sink(method, args, kwargs)
    return f


class Sink(PipelineElement):
    """A sink draws from a stream and stores/displays the frames."""

    def __init__(self, handler, args, kwargs):
        super().__init__(handler, args, kwargs)

    def process(self, frame):
        """Each call to this method processes a single frame."""
        self.call_handler(frame)


class TransformerInUseException(Exception):
    """Exception thrown by transformer instances when they are assigned to two streams."""
    pass


def stream_transformer(method=None):
    # If called without method, we've been called with optional arguments.
    # We return a decorator with the optional arguments filled in.
    # Next time round we'll be decorating method.
    if method is None:
        return functools.partial(stream_source)
    @functools.wraps(method)
    def f(*args, **kwargs):
        return Transformer(method, args, kwargs)
    return f


class Transformer(PipelineElement):
    """Transformer alter/modify/act on a frame within a stream."""

    def __init__(self, handler, args, kwargs):
        super().__init__(handler, args, kwargs)

    def transform(self, frame):
        return self.call_handler(frame)


def stream_gate(method=None, fatal=False):
    # If called without method, we've been called with optional arguments.
    # We return a decorator with the optional arguments filled in.
    # Next time round we'll be decorating method.
    if method is None:
        return functools.partial(stream_gate, fatal=fatal)
    @functools.wraps(method)
    def f(*args, **kwargs):
        return Gate(method, args, kwargs, fatal)
    return f


class Gate(Transformer):
    """Gates check frames for certain properties/qualities. A gate can be fatal, meaning that it brings the whole stream
    down if a single frame fails to pass, or non-fatal meaning that frames which don't pass are dropped.
    """

    def __init__(self, handler, args, kwargs, fatal=False):
        super().__init__(handler, args, kwargs)
        self._is_fatal = fatal

    def transform(self, frame):
        frame_passes_gate = self.call_handler(frame)
        if not frame_passes_gate:
            if self._is_fatal:
                raise GateFailedException("Frame %s did not pass gate %s" % (str(frame), str(self)))
            else:
                return None
        else:
            return frame


class GateFailedException(Exception):
    """Raised by fatal gates when a check fails."""

    def __init__(self, message):
        super().__init__(message)


def stream_barrier(method=None):
    # If called without method, we've been called with optional arguments.
    # We return a decorator with the optional arguments filled in.
    # Next time round we'll be decorating method.
    if method is None:
        return functools.partial(stream_barrier)

    @functools.wraps(method)
    def f(*args, **kwargs):
        return Barrier(method, args, kwargs)

    return f


class Barrier(Source):
    """Barriers are the basic synchronization construct of strom. A barrier function gets a dictionary of queues, one
    queue for each stream which ends at this barrier. The barrier function can then decide when to open/close the barrier
    by returning True or False, or to modify the queues at will (e.g. drop frames from it). When the barrier is open, each
    framing coming out of it will draw a single frame of each queue and assemble them in a dictionary."""

    def __init__(self, handler, args, kwargs):
        super().__init__(handler, args, {}, closer=lambda x: False)
        self._streams = kwargs
        self._queue = []

        # register sinks with all streams in kwargs
        @stream_sink
        def error_sink(frame):
            raise Exception('Streams ending in a barrier must not be run')

        for name, stream in self._streams.items():
            my_sink = error_sink()
            my_sink.is_barrier = True
            stream.sink = my_sink

    def get_streams(self):
        """Returns a dictionary of streams registered at this barrier"""
        return self._streams

    def get_frame(self):
        frame = self._query_frame_from_streams()
        self._queue.append(frame)

        if self._is_barrier_open():
            return self._queue.pop(0)
        else:
            None

    def _query_frame_from_streams(self):
        """Calls get_frame on all registered open streams and assembles a dictionary from it"""
        return {name: (None if stream.is_closed() else stream.get_frame()) for name, stream in self._streams.items()}

    def _is_barrier_open(self):
        return self.call_handler(self._queue)

    def is_closed(self):
        # we are closed when all source streams are closed
        return all([stream.is_closed() for _, stream in self._streams.items()])
