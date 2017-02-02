import sys
import argparse
import json

from strom.editor import BlockGenerator


def main():
    StromCommandLine().main()

class StromCommandLine(object):

    def main(self):
        parser = argparse.ArgumentParser(description='Pipeline/stream-centric data processing tool.')
        parser.add_argument('command', help='Subcommand to run')

        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            exit(1)
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    def blockly(self):
        parser = argparse.ArgumentParser(description='Converts Python classes to blockly descriptions')
        parser.add_argument('--module', help='The Python module within to search for PipelineElements', action='store')
        args = parser.parse_args(sys.argv[2:])

        generator = BlockGenerator()
        print(json.dumps(generator.generate_from_python_file(args.module)))


if __name__ == '__main__':
    main()