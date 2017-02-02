from strom.model import Source
from strom.model import blockly


class CsvSource(Source):
    """Uses pandas.read_csv to load a CSV file and return it as frames."""

    @blockly(type='String')
    def set_filename(self, value):
        self._filename = None

    @blockly(type='String')
    def set_separator(self, value):
        self._separator = value

    def __init__(self):
        self._filename = None
        self._separator = None
        self._frames = None

    def get_frame(self):
        import pandas
        super().get_frame()

        if self._frames is None:
            sep = self._separator or ';'
            self._frames = pandas.read_csv(self._filename, sep=sep)

        return self._frames.pop(self._frames.index[0])

