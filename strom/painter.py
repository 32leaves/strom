import itertools
import svgwrite
from svgwrite.container import Style

from strom.model import Transformer, Gate, Stream

PADDING_Y = 10

class Symbol:
    """Represents a symbol in the diagram"""

    def __init__(self, origin, svg, bounding_box, take_up, leave_off):
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

    def succeeds(self, other_symbol):
        """Establishes a succession relationship with another symbol"""
        self.predecessors.append(other_symbol)
        other_symbol.successors.append(self)

    def precedes(self, other_symbol):
        """Establishes a precession relationship with another symbol"""
        self.successors.append(other_symbol)
        other_symbol.predecessors.append(self)


class RailroadDiagram:
    """Draws railroad diagrams of stream configurations."""

    def __init__(self, stream: Stream):
        self._stream = stream

    def draw(self, filename=None):
        """Draws the railroad diagram returns it as SVG."""
        dwg = svgwrite.Drawing('diagram.svg', profile='tiny', debug=False)

        symbols = RailroadDiagram._create_symbols(self._stream, dwg, True)
        # linked_symbols = RailroadDiagram._link_symbols(symbols, dwg)

        symbols_group = RailroadDiagram._layout_symbols(symbols, dwg)
        symbols_group.translate(PADDING_Y, PADDING_Y)
        dwg.add(symbols_group)

        decoration = RailroadDiagram._add_page_decoration(self._stream, dwg)
        dwg.add(decoration)

        if filename is None:
            return dwg.tostring()
        else:
            dwg.saveas(filename, pretty=True)

    @staticmethod
    def _add_page_decoration(stream, dwg):
        # TODO: implement some fancy page decoration and metadata stuff
        return dwg.g()

    @staticmethod
    def _layout_symbols(linked_symbols, dwg):
        result = dwg.g()

        # walk DAG looking for sinks and sources
        def find_sinks(symbol):
            if not symbol.successors:
                return [symbol]
            else:
                all_successor_sinks = [find_sinks(s) for s in symbol.successors]
                return set(itertools.chain.from_iterable(all_successor_sinks))

        def find_sources(symbol):
            if not symbol.predecessors:
                return [symbol]
            else:
                all_predecessor_sources = [find_sources(s) for s in symbol.predecessors]
                return set(itertools.chain.from_iterable(all_predecessor_sources))

        # it's sufficient to start from any symbol to find all sinks as this is a DAG
        sinks = find_sinks(linked_symbols[0])
        # go back from all sinks to find all DAG sources
        sources = set(itertools.chain.from_iterable([find_sources(s) for s in sinks]))

        # sort sources by their dag_height
        # TODO: not sure this actually works ... there might well be a bug in this one, particullarly when it comes to barriers
        def find_dag_height(source, height=0):
            new_height = height + source.bounding_box[1]
            if source.successors:
                return max([find_dag_height(successor, new_height) for successor in source.successors])
            else:
                return new_height
        sorted(sources, key=find_dag_height)

        # add symbols to drawing starting with the sources
        def add_symbol_and_successors(symbol, offset=None):
            if symbol.was_added(): return

            # compute initial offset (if offset = None)
            if offset is None:
                offset = (0, 0.5 * symbol.bounding_box[1])

            # add symbol itself
            symbol_position = (offset[0] - symbol.take_up[0], offset[1] - symbol.take_up[1])
            symbol.absolute_position = symbol_position
            symbol_svg = symbol.svg
            symbol_svg.translate(tx=symbol_position[0], ty=symbol_position[1])
            result.add(symbol_svg)

            # add successors
            leave_off_position = (symbol_position[0] + symbol.leave_off[0], symbol_position[1] + symbol.leave_off[1])
            print("%s Offset=(%f, %f) LO=(%f, %f)" % (type(symbol.origin).__name__, symbol_position[0], symbol_position[1], leave_off_position[0], leave_off_position[1]))
            max_height = 0
            for successor in symbol.successors:
                yspace_used = add_symbol_and_successors(successor, offset=leave_off_position)
                if yspace_used > max_height: max_height = yspace_used
            return max_height

        # add all symbols starting with the sources
        y_position = 0
        for source in sources:
            y_position += add_symbol_and_successors(source) + PADDING_Y

        return result

    @staticmethod
    def _link_symbols(symbols, dwg):
        """Links a list of symbols and possibly creates new ones if it encounters a barrier."""
        previous_symbol = None
        for symbol in symbols:
            if previous_symbol is not None:
                symbol.succeeds(previous_symbol)
            previous_symbol = symbol
            # TODO: check for barriers and trigger their symbol creation
        return symbols

    @staticmethod
    def _create_symbols(stream, dwg, draw_source=True):
        """Transforms the stream to a set of symbols."""

        # start with source
        symbols = []
        if draw_source and stream.source is not None:
            symbols.append(RailroadDiagram._draw_source(dwg, stream.source))

        # add elements
        for element in stream.elements:
            symbol = None
            if isinstance(element, Gate):
                symbol = RailroadDiagram._draw_gate(dwg, element)
            elif isinstance(element, Transformer) and 'is_split_stream' in dir(element) and element.is_split_stream:
                symbol = RailroadDiagram._draw_split_stream(dwg, element)
                stream_symbols = RailroadDiagram._create_symbols(element.split_stream, dwg, False)
                if stream_symbols:
                    stream_symbols[0].succeeds(symbol)
            elif isinstance(element, Transformer):
                symbol = RailroadDiagram._draw_transformer(dwg, element)

            if symbol is not None:
                if symbols: symbol.succeeds(symbols[-1])
                symbols.append(symbol)

        # add sink
        symbols.append(RailroadDiagram._draw_sink(dwg, stream.sink))

        return symbols


    @staticmethod
    def _draw_source(dwg, source):
        """Draws a source on the current position of the dwg"""
        result = dwg.g(stroke='black', fill='none')
        circle = dwg.circle(center=(5, 5), r=5)
        result.add(circle)
        result.add(dwg.line((10, 5), (15, 5)))
        return Symbol(source, result, (15, 10), (0, 5), (15, 5))

    @staticmethod
    def _draw_transformer(dwg, transformer):
        """Draws the symbol of a transformer"""
        result = dwg.rect((0, 0), (30, 10), rx=5, ry=5, fill='none', stroke='black')
        return Symbol(transformer, result, (30, 10), (0, 5), (30, 5))

    @staticmethod
    def _draw_gate(dwg, gate):
        """Draws a gate on the current position of the dwg"""
        result = dwg.path('M0 0 h5 l10 2.5 m0 -2.5 h5', stroke='black')
        return Symbol(gate, result, (20, 2.5), (0, 0), (20, 0))

    @staticmethod
    def _draw_sink(dwg, sink):
        """Draws the symbol of a sink"""
        result = dwg.path(d='M0 0 h5 s 10 0, 10 10', fill='none', stroke='black')
        return Symbol(sink, result, (15, 10), (0, 0), (15, 10))

    @staticmethod
    def _draw_split_stream(dwg, stream):
        """Draws the symbol of a stream splitting in two"""
        result = dwg.g()
        return Symbol(stream, result, (15, 15), (0, 0), (15, 10))
