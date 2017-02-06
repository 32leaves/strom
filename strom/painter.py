import itertools
import svgwrite
from svgwrite.container import Style

from strom.model import Transformer, Gate, Stream, Barrier

PADDING_Y = 10


class Symbol:
    """Represents a symbol in the diagram"""

    def __init__(self, origin, svg, bounding_box=None, take_up=None, leave_off=None):
        """
        Creates a new symbol for drawing on the diagram.

        :param origin: The original stream element which led to the creation of this symbol
        :param svg: The SVG content of this symbol
        :param bounding_box: a tuple with the width and height of this symbol
        :param take_up: the point (x, y) at which the left-center point of this symbol should be aligned.
            This point is relative to boundingBox where (0, 0) is the upper left corner and (width, height) the lower
            right one.
        :param leave_off: the point (x, y) at which the left-center point next symbol should be aligned.
            This point is relative to boundingBox where (0, 0) is the upper left corner and (width, height) the lower
            right one.
        """
        self.origin = origin
        self.svg = svg
        self.bounding_box = bounding_box
        self.take_up = take_up
        self.leave_off = leave_off
        self.predecessors = []
        self.successors = []
        self.absolute_position = None

    def was_added(self):
        """Returns true if this symbol has already been added to a drawing, i.e. has an absolute position"""
        return self.absolute_position is not None

    def succeeds(self, other_symbol, name=None):
        """Establishes a succession relationship with another symbol"""
        self.predecessors.append((other_symbol, name))
        other_symbol.successors.append((self, name))

    def precedes(self, other_symbol, name=None):
        """Establishes a precession relationship with another symbol"""
        self.successors.append((other_symbol, name))
        other_symbol.predecessors.append((self, name))


class GraphvizDiagram:
    """Creates a graphviz diagram of the stream configurations."""

    def __init__(self, stream: Stream):
        self._stream = stream

    def draw(self, filename=None):
        """Generates the graphviz code and returns it or writes it to a file"""
        symbols = GraphvizDiagram._create_symbols(self._stream)
        edges = set(itertools.chain.from_iterable([GraphvizDiagram._draw_edges(s) for s in symbols]))

        code = "digraph G {\n"
        code += '\trankdir=LR;\n\t'
        code += ';\n\t'.join(set([s.svg for s in symbols])) + ';\n\n\t'
        code += ';\n\t'.join(edges) + ';\n\n'
        code += "}"

        if filename is not None:
            with open(filename, 'w+') as f:
                f.write(code)
            return None
        else:
            return code

    @staticmethod
    def _draw_edges(symbol):
        """Returns a list of outgoing edges converted to Graphviz"""
        def produce_edge(source, target):
            result = '%s -> %s' % (GraphvizDiagram._get_node_id(source.origin), GraphvizDiagram._get_node_id(target[0].origin))
            if target[1] is not None:
                result += ' [label="%s"]' % target[1]
            return result

        return [produce_edge(symbol, target) for target in symbol.successors]

    @staticmethod
    def _create_symbols(stream, draw_source=True):
        """Generates graphviz symbols for all elements of this stream"""
        # start with source
        last_element = None
        symbols = []

        # only draw there source if we should draw it, there is one, and the source is not from a stream_split
        if draw_source and stream.source is not None and not ('is_split_source' in dir(stream.source) and stream.source.is_split_source):
            # check if source is a barrier and create symbol streams
            if isinstance(stream.source, Barrier):
                source = GraphvizDiagram._draw_barrier(stream.source)
                last_element = source
                symbols.append(source)

                for stream_name, prebarrier_stream in stream.source.get_streams().items():
                    prebarrier_symbols = GraphvizDiagram._create_symbols(prebarrier_stream, draw_source=True)
                    if prebarrier_symbols:
                        last_element.succeeds(prebarrier_symbols[-1], stream_name)
                        symbols += prebarrier_symbols
            else:
                source = GraphvizDiagram._draw_source(stream.source)
                last_element = source
                symbols.append(source)

        # add elements
        for element in stream.elements:
            symbol = None
            if isinstance(element, Gate):
                symbol = GraphvizDiagram._draw_gate(element)
            elif isinstance(element, Transformer) and 'is_split_stream' in dir(element) and element.is_split_stream:
                symbol = GraphvizDiagram._draw_split_stream(element)

                stream_symbols = GraphvizDiagram._create_symbols(element.split_stream, draw_source=False)
                if stream_symbols:
                    stream_symbols[0].succeeds(symbol)
                    symbols += stream_symbols
            elif isinstance(element, Transformer):
                symbol = GraphvizDiagram._draw_transformer(element)

            if last_element is not None:
                symbol.succeeds(last_element)
            symbols.append(symbol)
            last_element = symbol

        # add sink
        if not ('is_barrier' in dir(stream.sink) and stream.sink.is_barrier):
            sink = GraphvizDiagram._draw_sink(stream.sink)
            if last_element:
                    sink.succeeds(last_element)
            symbols.append(sink)

        return symbols

    @staticmethod
    def _get_node_id(element):
        return '%s_%s' % (type(element).__name__, str(id(element)))

    @staticmethod
    def _draw_source(source):
        return Symbol(source, '%s [shape=circle, label="%s"]' % (GraphvizDiagram._get_node_id(source), str(source)))

    @staticmethod
    def _draw_barrier(source):
        return Symbol(source, '%s [shape=assembly, label="\\n\\n%s"]' % (GraphvizDiagram._get_node_id(source), str(source)))

    @staticmethod
    def _draw_gate(gate):
        return Symbol(gate, '%s [shape=parallelogram, label="%s"]' % (GraphvizDiagram._get_node_id(gate), str(gate)))

    @staticmethod
    def _draw_split_stream(split):
        return Symbol(split, '%s [shape=primersite, label=""]' % GraphvizDiagram._get_node_id(split))

    @staticmethod
    def _draw_transformer(transformer):
        return Symbol(transformer, '%s [shape=box, label="%s"]' % (GraphvizDiagram._get_node_id(transformer), str(transformer)))

    @staticmethod
    def _draw_sink(sink):
        return Symbol(sink, '%s [shape=cds, label="%s"]' % (GraphvizDiagram._get_node_id(sink), str(sink)))
