"""Unit tests for flutter_utils."""

from __future__ import unicode_literals

import unittest

from photon.lib import flutter_utils
from photon.lib.time_utils import Timestamp

FLUT_LIST = [{u'connection_id': u'0',
              u'count': u'43690',
              u'flutter_type': 'svc::postman_tcp_info_rcv_space_probe',
              u'tcpi_rcv_space': u'34',
              u'timestamp': Timestamp('2018-01-28 23:17:23.545000')},
             {u'connection_id': u'8291',
              u'count': u'26844',
              u'flutter_type': 'svc::postman_tcp_info_rcv_space_probe',
              u'tcpi_rcv_space': u'33',
              u'timestamp': Timestamp('2018-01-28 23:17:23.545000')},
             {u'connection_id': u'0',
              u'count': u'43690',
              u'flutter_type': 'svc::postman_tcp_info_rcv_space_probe',
              u'tcpi_rcv_space': u'34',
              u'timestamp': Timestamp('2018-01-28 23:20:23.545000')},
             {u'connection_id': u'8291',
              u'count': u'26844',
              u'flutter_type': 'svc::postman_tcp_info_rcv_space_probe',
              u'tcpi_rcv_space': u'33',
              u'timestamp': Timestamp('2018-01-28 23:20:23.545000')}]
TEST_FLUTTER_RAW = [
    [
        'Jan 28 23:17:23.545 000000000CE4 C      flutter ->dump(svc::postman_tcp_info_rcv_space_probe)\r\n',
        'Jan 28 23:17:23.545 000000000CE4 I          flutter     connection_id   tcpi_rcv_space  count\r\n',
        'Jan 28 23:17:23.545 000000000CE4 I          flutter     0   43690   34\r\n',
        'Jan 28 23:17:24.545 000000000CE4 I          flutter     8291    26844   33\r\n',
        'Jan 28 23:17:24.545 000000000CE4 C      flutter <-dump\r\n'],
    [
        'Jan 28 23:20:23.545 000000000CE4 C      flutter ->dump(svc::postman_tcp_info_rcv_space_probe)\r\n',
        'Jan 28 23:20:23.545 000000000CE4 I          flutter     connection_id   tcpi_rcv_space  count\r\n',
        'Jan 28 23:20:23.545 000000000CE4 I          flutter     0   43690   34\r\n',
        'Jan 28 23:20:23.545 000000000CE4 I          flutter     8291    26844   33\r\n',
        'Jan 28 23:20:23.545 000000000CE4 C      flutter <-dump\r\n']
]


class TestFlutter(unittest.TestCase):
    """ Test Flutter is instantiated correctly. """
    flutter = flutter_utils.Flutter(TEST_FLUTTER_RAW)

    def test_good_flutters_name(self):
        """ Test name is expected. """
        self.assertEqual(self.flutter.name,
                         'svc::postman_tcp_info_rcv_space_probe')

    def test_good_flutters_timestamps(self):
        """ Test timestamps is expected. """
        self.assertEqual(self.flutter.timestamps,
                         [Timestamp('Jan 28 23:17:23.545000'),
                          Timestamp('Jan 28 23:20:23.545000')])

    def test_good_flutters_headers(self):
        """ Test headers is expected. """
        self.assertEqual(self.flutter.headers,
                         ['connection_id', 'count', 'tcpi_rcv_space'])

    def test_good_flutters_flutters(self):
        """ Test flutters is expected. """
        self.assertEqual(self.flutter.flutters, FLUT_LIST)


class TestFlutterInstance(unittest.TestCase):
    """ Test FlutterInstance is instantiated correctly. """
    flutter_instance = flutter_utils.FlutterInstance(TEST_FLUTTER_RAW[0])

    def test_good_flutter_flutter_data(self):
        """ Test data is expected. """
        self.assertEqual(self.flutter_instance.flutter_data, FLUT_LIST[0:2])

    def test_good_flutter_headers(self):
        """ Test headers is expected. """
        self.assertEqual(self.flutter_instance.headers,
                         ['connection_id', 'count', 'tcpi_rcv_space'])

    def test_good_flutter_lines(self):
        """ Test lines is expected. """
        self.assertEqual(self.flutter_instance.lines, TEST_FLUTTER_RAW[0])

    def test_good_flutters_name(self):
        """ Test name is expected. """
        self.assertEqual(self.flutter_instance.name,
                         'svc::postman_tcp_info_rcv_space_probe')

    def test_good_flutters_timestamps(self):
        """ Test timestamps is expected. """
        self.assertEqual(self.flutter_instance.timestamp,
                         Timestamp('Jan 28 23:17:23.545000'))
