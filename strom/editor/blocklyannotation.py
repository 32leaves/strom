import inspect

def is_blockly(function):
    """Checks if a function has a blockly decorator"""
    return 'is_blockly' in dir(function) and function.is_blockly


def get_blockly_arg_name(function):
    """Returns the name of blockly function arg"""
    return function.blockly_name or function.__name__


def get_blockly_arg_type(function):
    """Returns the type of blockly function arg"""
    return function.blockly_type

def get_blockly_functions(element):
    return [func[1] for func in inspect.getmembers(element) if is_blockly(func[1])]