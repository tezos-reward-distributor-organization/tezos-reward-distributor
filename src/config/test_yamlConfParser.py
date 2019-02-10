from unittest import TestCase

from config.yaml_conf_parser import YamlConfParser

document = """
none: [~, null]
bool: [true, false, on, off]
int: 42
float: 3.14159
list: [LITE, RES_ACID, SUS_DEXT]
dict: {hp: 13, sp: 5}
"""


class TestYamlConfParser(TestCase):
    def test_parse(self):
        appConfParser = YamlConfParser(document)
        conf_obj = appConfParser.parse()

        self.assertEqual(conf_obj['none'], [None, None])
        self.assertEqual(conf_obj['bool'], [True, False, True, False])
        self.assertEqual(conf_obj['list'], ['LITE', 'RES_ACID', 'SUS_DEXT'])
        self.assertEqual(conf_obj['dict']['hp'], 13)
        self.assertEqual(conf_obj['int'], 42)

        appConfParser.validate()