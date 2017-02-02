from unittest import TestCase
from strom import Source
from strom import blockly
from strom.editor import BlockGenerator


class BlockGeneratorTest(TestCase):

    def test_source_block_generation(self):
        class MySourceBlock(Source):

            @blockly(name='foo', type='String')
            def set_foo(self, value):
                pass

        generator = BlockGenerator()
        block = generator.generate(MySourceBlock())

        self.assertEqual(block['type'], 'source_MySourceBlock')
        self.assertTrue('type' in block.keys(), 'Block does not have a type')
        self.assertTrue('args0' in block.keys(), 'Block does not have args')
        self.assertEqual(len(block['args0']), 2)
        self.assertEqual(block['args0'][0]['name'], 'name')
        self.assertEqual(block['args0'][0]['check'], 'String')
        self.assertEqual(block['args0'][1]['name'], 'foo')
        self.assertEqual(block['args0'][1]['check'], 'String')

