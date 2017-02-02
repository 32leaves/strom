from queue import Queue


def blockly(name=None, type=None):
    """Class attribute dectorator for supplying blockly generation metadata."""
    def decorator(func):
        func.blockly_type = type
        func.blockly_name = name
        func.is_blockly = True
        return func

    return decorator


class PipelineElement:
    """Pipeline elements are the objects which constitute a pipeline. Please see the documentation of strom.py for more
    details about this concept.
    """

    @blockly(name='name', type='String')
    def set_name(self, value):
        self._name = value

    def __init__(self):
        self._name = None


class Stream(PipelineElement):
    """A stream collects, transports and transforms data maintained in frames.
    """

    def __init__(self):
        """Creates a new stream from a source
        """
        self.source = None
        self.elements = []

    def add(self, element):
        """Adds an element (transformer or gate) to the stream.
        """
        element._set_stream(self)
        self.elements.append(element)

    def get_frame(self):
        """Asks the source for another frame, floats is through transformer, gates and other stream elements and returns
         it. Calling this method on a closed stream will raise an exception.
        """
        frame = self.source.get_frame()

        # transform frame with all elements
        for element in self.elements:
            frame = element.transform(frame)

        return frame

    def is_closed(self):
        """Checks if the source can deliver any more frames."""
        return self.source.is_closed()


class SourceIsClosedException(Exception):
    """Exception used to denote that a source can no longer deliver frames."""
    pass


class Source(PipelineElement):
    """A source delivers frames into a stream."""

    def is_closed(self):
        """Determines if this source can deliver any more frames. Once a source is closed, it must not re-open again."""
        return False

    def get_frame(self):
        """Returns another frame. This method may block until the next frame becomes available. Calling this method on
        a closed source raises an exception.
        """
        if self.is_closed():
            raise SourceIsClosedException()

        return None


class Sink(PipelineElement):
    """A sink draws from a stream and stores/displays the frames."""

    def __init__(self):
        self.stream = None

    def tick(self):
        """Each call to this method processes a single frame. When this method returns False, no more calls to this method
        are necessary (but still allowed).
        """
        if self.stream.is_closed():
            return False
        else:
            self._process_frame(self.stream.get_frame())
            return True

    def _process_frame(self, frame):
        """Subclasses should override this method to process the frames dripping out of the stream."""
        raise NotImplementedError()


class TransformerInUseException(Exception):
    """Exception thrown by transformer instances when they are assigned to two streams."""
    pass


class Transformer(PipelineElement):
    """Transformer alter/modify/act on a frame within a stream."""

    def __init__(self):
        self._stream = None

    def _set_stream(self, stream):
        """Not intended for public consumption. This method is called internally when it is assigned to a stream."""
        if self._stream is not None:
            raise TransformerInUseException()
        else:
            self._stream = stream

    def transform(self, frame):
        raise NotImplementedError()


class Gate(Transformer):
    """Gates check frames for certain properties/qualities. A gate can be fatal, meaning that it brings the whole stream
    down if a single frame fails to pass, non-fatal meaning that frames which don't pass are dropped, and divergent
    meaning that frames which don't pass are put in another stream.

    This class is not intended to be overiden directly. Rather override it's direct descendants FatalGate, NonFatalGate
    and DivergentGate, depending on which behavior is desired.
    """

    def transform(self, frame):
        raise NotImplementedError()

    def _check(self, frame):
        """Subclasses should override this to perform checks on a frame. If the check fails, return a string with an
        error message. If the check passes return None.
        """
        raise NotImplementedError()


class GateFailedException(Exception):
    """Raised by fatal gates when a check fails."""

    def __init__(self, message):
        super().__init__(message)


class FatalGate(Gate):
    def transform(self, frame):
        result = self._check(frame)
        if result is not None:
            # TODO: add logging here
            raise GateFailedException(result)

        return frame


class NonFatalGate(Gate):
    def transform(self, frame):
        result = self._check(frame)
        if result is not None:
            # TODO: add logging here
            return None
        else:
            return frame


class DivergentGate(Gate, Source):
    def __init__(self):
        self._frameQueue = Queue()

    def transform(self, frame):
        result = self._check(frame)
        if result is not None:
            # TODO: add logging here
            self._frameQueue.put_nowait(frame)
            return None
        else:
            return frame

    def get_frame(self):
        if self.is_closed():
            raise SourceIsClosedException()
        return self._frameQueue.get(True)

    def is_closed(self):
        return self._frameQueue.empty() and self._stream.is_closed()

