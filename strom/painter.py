import svgwrite

from strom.model import Transformer, Gate, Stream


class RailroadDiagram:
    """Draws railroad diagrams of stream configurations."""

    def __init__(self, stream: Stream):
        self._stream = stream

    def draw(self, filename=None):
        """Draws the railroad diagram returns it as SVG."""
        canvas = svgwrite.Drawing('diagram.svg', profile='tiny')
        self._draw(canvas, draw_source = True)
        if filename is None:
            return canvas.tostring()
        else:
            canvas.saveas(filename, pretty=True)

    def _draw(self, canvas, draw_source=True, origin=(0,0)):
        """Internal draw method used for drawing streams. This function can be used for drawing split streams."""
        xpos = origin[0]
        ypos = origin[1]
        # draw source
        if draw_source:
            self._draw_source(canvas, origin, self._stream.source)
        post_source_line_length = 10
        canvas.add(canvas.line(origin, (xpos + post_source_line_length, ypos)))
        xpos += post_source_line_length

        # draw elements
        for element in self._stream.elements:
            add_to_xpos = 0
            if isinstance(element, Gate):
                add_to_xpos = self._draw_gate(canvas, (xpos, ypos), element)
            elif isinstance(element, Transformer) and 'is_split_stream' in dir(element) and element.is_split_stream:
                add_to_xpos = self._draw_split_stream(canvas, (xpos, ypos), element)
            elif isinstance(element, Transformer):
                add_to_xpos = self._draw_gate(canvas, (xpos, ypos), element)
            xpos += add_to_xpos

        # draw sink


    def _draw_source(self, canvas, origin, source):
        """Draws a source on the curent position of the canvas"""
        canvas.add(canvas.circle(center=origin, r=10))
        return 10

    def _draw_gate(self, canvas, origin, gate):
        """Draws a gate on the current position of the canvas"""
        x, y = origin
        canvas.add(canvas.line(origin, (x + 5, y)))
        canvas.add(canvas.line((x + 5, y), (x + 17, y + 10)))
        canvas.add(canvas.line((x + 15, y + 6), (x + 15, y)))
        canvas.add(canvas.line((x + 15, y), (x + 20, y)))
        return 20
