import inspect
import sys
import argparse
import json

from strom import Stream


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

    def graphviz(self):
        from strom.painter import GraphvizDiagram

        parser = argparse.ArgumentParser(description='Draws a diagram for a stream')
        parser.add_argument('--module', help='The Python module which defines the stream', action='store')
        parser.add_argument('--save', help='The output filename', action='store_true')
        args = parser.parse_args(sys.argv[2:])
        module = __import__(args.module, fromlist=[1])
        GraphvizDiagram(module.stream).draw("output_0.dot")


if __name__ == '__main__':
    main()
