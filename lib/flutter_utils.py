"""Common functions to parse flutter lines from log files."""

import pandas

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Generator
    from typing import List
    from typing import Optional
except ImportError:
    pass

from photon.lib import time_utils


def _get_columns(line):
    # type: (str) -> List[str]
    """ Parses headers from a header line. """
    columns = [column.strip() for column in line.split('flutter')[-1].split()]
    return columns


class Flutter(object):
    """Manages / manipulates multiple flutter instances."""

    def __init__(self, flutters):
        # type: (Any) -> None
        self._timestamps = set()
        self._headers = set()
        self.flutters = []
        self.name = None

        for flutter_data in flutters:
            flutter_instance = FlutterInstance(flutter_data)
            self._timestamps.add(flutter_instance.timestamp)
            self._headers.update(set(flutter_instance.headers))
            self.flutters.extend(flutter_instance)
            if not self.name:
                self.name = flutter_instance.name

    def __iter__(self):
        # type: () -> Generator[Any]
        return (flutter for flutter in self.flutters)

    def __getitem__(self, index):
        # type: (int) -> Any
        return self.flutters[index]

    def __str__(self):
        # type: () -> str
        return self.name

    def __repr__(self):
        # type: () -> str
        return '< {}({}) at {} >'.format('Flutter', self.name, hex(id(self)))

    @property
    def timestamps(self):
        # type: () -> List[str]
        """ Return timestamps of a flutter set. """
        return sorted(self._timestamps)

    @property
    def headers(self):
        # type: () -> List[str]
        """ Return the column headers of a flutter set. """
        return sorted(self._headers)

    def to_dataframe(self):
        # type: () -> pandas.DataFrame
        """ Return a dataframe of the flutter set. """
        return pandas.DataFrame(self.flutters)


class FlutterInstance(object):
    """ Container for flutter instances.
    Arguments:

        lines(list): lines of a flutter from ->dump to <-dump split by newline.

    Example Input:

        [['Jan 28 23:17:23.545 000000000CE4 C      flutter ->dump(svc::postman_tcp_info_rcv_space_probe)\r\n',
          'Jan 28 23:17:23.545 000000000CE4 I          flutter     connection_id   tcpi_rcv_space  count\r\n',
          'Jan 28 23:17:23.545 000000000CE4 I          flutter     0   43690   34\r\n',
          'Jan 28 23:17:24.545 000000000CE4 I          flutter     8291    26844   33\r\n',
          'Jan 28 23:17:24.545 000000000CE4 C      flutter <-dump\r\n'],
         ['Jan 28 23:20:23.545 000000000CE4 C      flutter ->dump(svc::postman_tcp_info_rcv_space_probe)\r\n',
          'Jan 28 23:20:23.545 000000000CE4 I          flutter     connection_id   tcpi_rcv_space  count\r\n',
          'Jan 28 23:20:23.545 000000000CE4 I          flutter     0   43690   34\r\n',
          'Jan 28 23:20:23.545 000000000CE4 I          flutter     8291    26844   33\r\n',
          'Jan 28 23:20:23.545 000000000CE4 C      flutter <-dump\r\n']]
    """

    def __init__(self, lines):
        # type: (List[str]) -> None
        self.lines = lines
        self.timestamp = time_utils.get_timestamp_from_line(self.lines[0])
        self.name = self._get_flutter_type()
        self.headers = sorted(_get_columns(self.lines[1]))
        self.flutter_data = []
        self._append_flutter_data()

    def __iter__(self):
        # type: () -> Generator[Any]
        return (flutter for flutter in self.flutter_data)

    def __getitem__(self, index):
        # type: (int) -> Any
        return self.flutter_data[index]

    def _get_flutter_type(self):
        # type: () -> List[str]
        """ Gets flutter name from start line. """
        # Flutter name is between ->dump() in the line.
        # Since it starts after the first parenthesis, we want start to be the
        # index of the open paren + 1.
        start = self.lines[0].index('(')+1
        # End index is not inclusive, so we use the index of the close paren.
        end = self.lines[0].index(')')
        return self.lines[0][start:end]

    def _append_flutter_data(self):
        # type: () -> None
        """ Gets flutter data from data lines. """
        # Line 0 is the flutter start
        # line 1 is flutter headers
        # line 2 starts data
        # last line ends flutter, so we want the second to last line (Slice
        # notation is non-inclusive)
        for line in self.lines[2:-1]:
            # Create empty dict and add timestamp and flutter type.
            temp_dict = {'timestamp': self.timestamp,
                         'flutter_type': self.name}
            # Go through the headers and add each header to the dict under it's key.
            for index in range(len(self.headers)):
                temp_dict[self.headers[index]] = _get_columns(line)[index]
            # Append the dict to the main list object.
            self.flutter_data.append(temp_dict)
