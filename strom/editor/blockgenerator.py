from strom import PipelineElement, Source, Stream, FatalGate, NonFatalGate, DivergentGate, Transformer, Sink
from .blocklyannotation import is_blockly, get_blockly_arg_name, get_blockly_arg_type, get_blockly_functions
import inspect


class BlockGenerator:
    """Generates a blockly JSON description for a pipeline element."""

    def generate_from_python_file(self, modulename):
        """Loads a Python file/module and generates blockly blocks for all PipelineElements"""
        # load module and find all classes within it
        module = __import__(modulename, fromlist=['foo'])
        classesInModule = inspect.getmembers(module, inspect.isclass)

        # try to create instances of all classes in the module
        instancesOfAllClasses = []
        for clasz in classesInModule:
            try:
                instancesOfAllClasses.append(clasz[1]())
            except:
                pass

        return [ self.generate(element) for element in instancesOfAllClasses if isinstance(element, PipelineElement) ]

    def generate(self, element):
        """Generates the JSON description for a pipeline element."""
        if not isinstance(element, PipelineElement):
            raise TypeError('Element is not a PipelineElement instance')

        if isinstance(element, Source):
            return self._generate_source_block(element)
        elif isinstance(element, Stream):
            return self._generate_stream_block(element)
        elif isinstance(element, FatalGate):
            return self._generate_fatal_gate_block(element)
        elif isinstance(element, NonFatalGate):
            return self._generate_non_fatal_gate_block(element)
        elif isinstance(element, DivergentGate):
            return self._generate_divergent_gate_block(element)
        elif isinstance(element, Transformer):
            return self._geneate_transformer_block(element)
        elif isinstance(element, Sink):
            return self._generate_sink_block(element)
        else:
            raise TypeError('Unknown type %s. This is a bug in the implementation.' % str(type(element)))

    def _generate_source_block(self, element):
        """Generates the blockly description for a source block and returns it as dictionary"""
        return {
            'type': "source_%s" % str(type(element).__name__),
            'args0': [{
                'type' : 'input_dummy',
                'name' : str(type(element).__name__)
            }] + self._build_attributes(element),
            'nextStatement': 'null',
            'colour': 120
        }

    def _build_attributes(self, element):
        """Generates a blockly args dict for all blockly-decorated functions of the element."""
        def build_attribute(attr):
            return {
                'type': 'input_value',
                'name': attr[0],
                'check': attr[1]
            }

        blocklyFunctions = get_blockly_functions(element)
        attributes = { get_blockly_arg_name(func): get_blockly_arg_type(func) for func in blocklyFunctions }
        return [ build_attribute(attr) for attr in attributes.items() ]