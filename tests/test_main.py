'''
Tests for the main.py
'''
import json

from main import get_stats
import unittest


class TestMain(unittest.TestCase):
    
    def test_make_graph(self):
        '''Tests the make_graph function'''
        with open('./tests/mock_data.json', 'r') as file:
            data = json.load(file)
        print(get_stats(data))


if __name__ == '__main__':
    unittest.main()
