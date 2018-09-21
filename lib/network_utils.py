"""Network utility classes for testing network connectivity or utilizing networks to
    transfer/receive information without relying on OS packages."""

import ast
import re
import socket
import subprocess
import time
import traceback

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import Optional
    from typing import Tuple
except ImportError:
    pass

OPEN_SOCKET = 0
CLOSE_SOCKET = 1
LISTEN_SOCKET = 2
CONNECT_SOCKET = 3
CLEANUP = 4
RUN_SHELL_COMMAND = 5
PING = 6
LIST_LOCAL_INTERFACES = 7
EXIT = -1

# The dict for SOCKET_RETURNS are the linux errnos that sockets will return, defined in:
# https://elixir.bootlin.com/linux/v4.1/source/include/uapi/asm-generic/errno-base.h
# and in:
# https://elixir.bootlin.com/linux/v4.1/source/include/uapi/asm-generic/errno.h

SOCKET_RETURNS = {
    0: 'Success',
    1: 'Operation not permitted',
    2: 'No such file or directory',
    3: 'No such process',
    4: 'Interrupted system call',
    5: 'Input/output error',
    6: 'No such device or address',
    7: 'Argument list too long',
    8: 'Exec format error',
    9: 'Bad file descriptor',
    10: 'No child processes',
    11: 'Resource temporarily unavailable',
    12: 'Cannot allocate memory',
    13: 'Permission denied',
    14: 'Bad address',
    15: 'Block device required',
    16: 'Device or resource busy',
    17: 'File exists',
    18: 'Invalid cross-device link',
    19: 'No such device',
    20: 'Not a directory',
    21: 'Is a directory',
    22: 'Invalid argument',
    23: 'Too many open files in system',
    24: 'Too many open files',
    25: 'Inappropriate ioctl for device',
    26: 'Text file busy',
    27: 'File too large',
    28: 'No space left on device',
    29: 'Illegal seek',
    30: 'Read-only file system',
    31: 'Too many links',
    32: 'Broken pipe',
    33: 'Numerical argument out of domain',
    34: 'Numerical result out of range',
    35: 'Resource deadlock avoided',
    36: 'File name too long',
    37: 'No locks available',
    38: 'Function not implemented',
    39: 'Directory not empty',
    40: 'Too many levels of symbolic links',
    41: 'Unknown error 41',
    42: 'No message of desired type',
    43: 'Identifier removed',
    44: 'Channel number out of range',
    45: 'Level 2 not synchronized',
    46: 'Level 3 halted',
    47: 'Level 3 reset',
    48: 'Link number out of range',
    49: 'Protocol driver not attached',
    50: 'No CSI structure available',
    51: 'Level 2 halted',
    52: 'Invalid exchange',
    53: 'Invalid request descriptor',
    54: 'Exchange full',
    55: 'No anode',
    56: 'Invalid request code',
    57: 'Invalid slot',
    58: 'Unknown error 58',
    59: 'Bad font file format',
    60: 'Device not a stream',
    61: 'No data available',
    62: 'Timer expired',
    63: 'Out of streams resources',
    64: 'Machine is not on the network',
    65: 'Package not installed',
    66: 'Object is remote',
    67: 'Link has been severed',
    68: 'Advertise error',
    69: 'Srmount error',
    70: 'Communication error on send',
    71: 'Protocol error',
    72: 'Multihop attempted',
    73: 'RFS specific error',
    74: 'Bad message',
    75: 'Value too large for defined data type',
    76: 'Name not unique on network',
    77: 'File descriptor in bad state',
    78: 'Remote address changed',
    79: 'Can not access a needed shared library',
    80: 'Accessing a corrupted shared library',
    81: '.lib section in a.out corrupted',
    82: 'Attempting to link in too many shared libraries',
    83: 'Cannot exec a shared library directly',
    84: 'Invalid or incomplete multibyte or wide character',
    85: 'Interrupted system call should be restarted',
    86: 'Streams pipe error',
    87: 'Too many users',
    88: 'Socket operation on non-socket',
    89: 'Destination address required',
    90: 'Message too long',
    91: 'Protocol wrong type for socket',
    92: 'Protocol not available',
    93: 'Protocol not supported',
    94: 'Socket type not supported',
    95: 'Operation not supported',
    96: 'Protocol family not supported',
    97: 'Address family not supported by protocol',
    98: 'Address already in use',
    99: 'Cannot assign requested address',
    100: 'Network is down',
    101: 'Network is unreachable',
    102: 'Network dropped connection on reset',
    103: 'Software caused connection abort',
    104: 'Connection reset by peer',
    105: 'No buffer space available',
    106: 'Transport endpoint is already connected',
    107: 'Transport endpoint is not connected',
    108: 'Cannot send after transport endpoint shutdown',
    109: 'Too many references: cannot splice',
    110: 'Connection timed out',
    111: 'Connection refused',
    112: 'Host is down',
    113: 'No route to host',
    114: 'Operation already in progress',
    115: 'Operation now in progress',
    116: 'Stale NFS file handle',
    117: 'Structure needs cleaning',
    118: 'Not a XENIX named type file',
    119: 'No XENIX semaphores available',
    120: 'Is a named type file',
    121: 'Remote I/O error',
    122: 'Disk quota exceeded',
    123: 'No medium found',
    124: 'Wrong medium type',
}


def get_tcp_socket(interface='', port=0):
    # type: (str, int) -> socket.socket
    """Gets a socket if it exists or creates one and adds it to the managed sockets.

    Arguments:
        interface (str): hostname or ipv4 address. Default of '' will assign to 0.0.0.0
                         (default gateway of host)
        port (int): port number to attempt to bind. Default of 0 will use OS
                    default to pick one for you.

    Returns:
        sock (socket.socket): A TCP Socket.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((interface, port))
    return sock


def get_local_default_ip():
    # type: () -> str
    """Get the local default IP address."""
    default_ip = None
    result = subprocess.check_output('ip route show'.split())
    decoded_result = result.decode('utf-8')

    # Example of ip route show output:
    # default via 10.204.116.1 dev ens160 onlink
    # 10.204.116.0/22 dev ens160  proto kernel  scope link  src 10.204.116.216
    # 172.17.0.0/16 dev docker0  proto kernel  scope link  src 172.17.0.1 linkdown
    for line in decoded_result.splitlines():
        # First we have to find out which interface is our default
        if 'default' in line:
            # Pulls the dev from this line:
            # default via 10.204.116.1 dev ens160 onlin
            default_match = re.search(r'dev (?P<source_interface>\w+)', line)
            default_interface = default_match.groupdict().get('source_interface')
            # Skip this first line so we don't get a false positive for the next one.
            continue
        # Now we find which interface is the link for that dev:
        # 10.204.116.0/22 dev ens160  proto kernel  scope link  src 10.204.116.216
        if default_interface and default_interface in line:
            # Pull the src from this line: src 10.204.116.216
            default_match = re.search(r'src (?P<ip_addr>\w+.\w+.\w+.\w+)', line)
            default_ip = default_match.groupdict().get('ip_addr')
    return default_ip


class NetworkTester(object):
    """Class for general network testing purposes like checking ports are open,
        interfaces are up, etc."""

    def __init__(self, listener=False):
        # type: (bool) -> None
        """Object to manage and maintain socket information and interacting with them."""
        self.COMMANDS = {}
        self.sockets = {}
        self.listener = listener
        self.command_sock = get_tcp_socket('0.0.0.0', 55555)
        self.COMMANDS[OPEN_SOCKET] = self.open_socket
        self.COMMANDS[CLOSE_SOCKET] = self.close_socket
        self.COMMANDS[LISTEN_SOCKET] = self.listen_socket
        self.COMMANDS[CONNECT_SOCKET] = self.connect_socket
        self.COMMANDS[CLEANUP] = self.cleanup
        self.COMMANDS[RUN_SHELL_COMMAND] = self.run_shell_command
        self.COMMANDS[PING] = self.ping
        self.COMMANDS[LIST_LOCAL_INTERFACES] = self.list_local_interfaces

    def __enter__(self):
        # type: () -> NetworkTester
        """Instantiation of the context manager functionality."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Any, Any, Any) -> None
        """Context management cleanup."""
        # We might get an OSError if the socket isn't connected.
        # If we do, the finally block is all that will be needed.
        try:
            self.command_sock.shutdown(socket.SHUT_RDWR)
        except OSError as err:
            # If it's not connected, we don't care - that's not abnormal.
            if err.errno == 107:
                pass
        finally:
            self.cleanup({})
            self.command_sock.close()

    def get_managed_socket(self, interface='', port=0):
        # type: (str, int) -> socket.socket
        """Gets a socket if it exists or creates one and adds it to the managed sockets."""
        # Make sure the port is an int.
        port = int(port)
        address_key = '{}:{}'.format(interface, port)
        sock = self.sockets.get(address_key)
        if not sock:
            sock = get_tcp_socket(interface=interface, port=port)
        self.sockets[address_key] = sock
        return sock

    def cleanup(self, command_dict):
        # type: (Dict[Any, Any]) -> Dict[Any, Any]
        """Clean up and close all connections."""
        # We call all our commands the same way for simplicity and ease of use
        # but we may not always use the command_dict, like for cleanup.
        # pylint: disable=unused-argument
        for sock in self.sockets.values():
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except socket.error as err:
                # If the endpoint wasn't connected, it's fine, we still want to close() it.
                # See socket return codes in SOCKET_RETURNS.
                if err.errno == 107:
                    continue
            sock.close()
        for sockname in list(self.sockets):
            self.sockets.pop(sockname)
        return self.sockets

    def send_command(self, command_dict):
        # type: (Dict[Any, Any]) -> str
        """Send a string command."""
        self.command_sock.sendall(str(command_dict).encode('utf-8'), 2)
        start_time = time.time()
        # Time out after 3 seconds, or break when we get our response.
        while time.time() - start_time < 3:
            response = self.command_sock.recv(1024)
            if response:
                break
        stripped_response = response.strip()
        response_string = '{}'.format(stripped_response.decode('utf-8'))
        return ast.literal_eval(response_string)

    def open_socket(self, command_dict):
        # type: (Dict[Any, Any]) -> str
        """Open a socket and add it to our sockets dict."""
        sock = None
        interface = command_dict.get('interface')
        port = command_dict.get('port')
        if interface and port:
            int_port = int(port)
            sock = self.get_managed_socket(interface=interface, port=int_port)
        return str(sock)

    def close_socket(self, command_dict):
        # type: (Dict[Any, Any]) -> str
        """Close a socket and remove from our socket dict."""
        interface = command_dict.get('interface')
        port = str(command_dict.get('port'))
        sock = self.sockets.get(':'.join([interface, port]))
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except socket.error as err:
                if err.errno == 107:
                    pass
            sock.close()
            self.sockets.pop(':'.join([interface, port]))
        return str(sock)

    def listen_socket(self, command_dict):
        # type: (Dict[Any, Any]) -> str
        """Set a socket in listen mode."""
        interface = command_dict.get('interface')
        port = command_dict.get('port')
        result = False
        if interface and port:
            int_port = int(port)
            sock = self.get_managed_socket(interface=interface, port=int_port)
        if sock:
            try:
                sock.listen(1)
                result = True
            except socket.error:
                result = False
        return result

    def connect_socket(self, command_dict):
        # type: (Dict[Any, Any]) -> str
        """Connect a socket to another socket that's set as a listener."""
        interface = command_dict.get('interface')
        port = command_dict.get('port')
        target_interface = command_dict.get('target_interface')
        target_port = command_dict.get('target_port')
        # Assume the worst first:
        status = 6  # "No such device or address"
        if all([interface, port, target_interface, target_port]):
            _, status = self.resilient_connect(interface, port, target_interface, target_port)
        return SOCKET_RETURNS.get(status)

    def run_command(self, command_dict):
        # type: (Dict[Any, Any]) -> str
        """Run a command on a remote NetowrkTester."""
        command = self.COMMANDS.get(command_dict.get('command'))
        result = command(command_dict)
        return result

    def run_shell_command(self, command_dict):
        # type: (Dict[Any, Any]) -> str
        # For sake of consistency in passing commands and accessing commands, the
        # commands will still be part of the class.  Not all will use self.
        # pylint: disable=no-self-use
        """Run a shell command via the NetworkTester instance and return the result."""
        shell_command = command_dict.get('shell_command')
        if not shell_command:
            result = None
        else:
            result = subprocess.check_output(shell_command.split())
        return result

    def list_local_interfaces(self, command_dict):
        # type: (Dict[Any, Any]) -> Dict[str, Any]
        """List the local interfaces via the NetworkTester instance and return the result."""
        # For sake of consistency in passing commands and accessing commands, the
        # commands will still be part of the class.  Not all will use self or
        # command_dict
        # pylint: disable=no-self-use
        # # pylint: disable=unused-argument
        local_interfaces = {}
        ctrl = socket.gethostname().split('-')[-1]
        result = subprocess.check_output('purenetwork list'.split())
        for line in result.splitlines():
            str_line = line.decode('utf-8')
            if ctrl in str_line:
                ethnum = str_line.split()[0].split('.')[-1]
                ipaddr = str_line.split()[3]
                # Get rid of interfaces that don't have IP addresses.
                if ipaddr == '-':
                    continue
                local_interfaces[ethnum] = ipaddr
        return local_interfaces

    def listen(self, timeout=360):
        # type: (int) -> None
        """Set a NetworkTester in listen mode so it will listen for commands to execute."""
        temp_sock = get_tcp_socket(interface=get_local_default_ip(), port=55555)
        temp_sock.listen(1)
        command_sock, _ = temp_sock.accept()
        self.command_sock = command_sock
        start = time.time()
        # We'll listen for default before we close on our own..
        while (time.time() - start) < timeout:
            command = self.command_sock.recv(1024)
            command_dict = ast.literal_eval(command.decode('utf-8'))
            if command_dict.get('command') == EXIT:
                # If we get exit, try to cleanup, and return errors if any.
                break
            try:
                result = self.run_command(command_dict)
                command_dict['response'] = 0
                command_dict['result'] = result
                command_response = str(command_dict).encode('utf-8')
                self.command_sock.sendall(command_response)
            # Since we're a listener on a remote site, we want to know on the local
            # connection what issue we hit, so we send the stacktrace back rather than
            # just exploding and going away.
            # pylint: disable=broad-except
            except Exception:
                trace = traceback.format_exc()
                command_dict['response'] = 1
                command_dict['exception'] = trace
                command_response = str(command_dict).encode('utf-8')
                self.command_sock.sendall(command_response)

    def resilient_connect(self, socket_addr, socket_port, target_addr, target_port):
        # type: (str, str, str, str) -> Tuple[socket.socket, str]
        """Attempt to connect to a socket with additional tries.
            When connecting to a socket, it won't always succeed the first time, or may take some
            time to connect. this function allows some resiliency in attempting to get the socket
            and establish a connection.
        """
        time_to_try = 3
        start = time.time()
        # Try this for 3 seconds.  This is a constant for now since it's forever in
        # this context.
        while (time.time() - start) < time_to_try:
            sock = self.get_managed_socket(interface=socket_addr, port=int(socket_port))
            # break if we get our socket.
            if sock:
                break
        start = time.time()
        # Try this for 3 seconds.  This is a constant for now since it's forever in
        # this context.
        while (time.time() - start) < time_to_try:
            status = sock.connect_ex((target_addr, int(target_port)))
            # Break if we connect
            if status == 0:
                break
        return sock, status

    def ping(self, command_dict):
        # type: (Dict[Any, Any]) -> Optional[str]
        """Subprocesses ping and returns the output in a usable manner."""
        # For sake of consistency in passing command    s and accessing commands, the
        # commands will still be part of the class.  Not all will use self.
        # pylint: disable=no-self-use
        interface = command_dict.get('source_interface') or 'lo'
        target = command_dict.get('target_interface') or '127.0.0.1'
        count = command_dict.get('count') or 3
        allow_fragmenting = command_dict.get('allow_fragmenting') or False
        size = command_dict.get('size') or 1500
        interval_time = command_dict.get('interval_time') or 0.2
        # Regex for ping results match either of these cases:
        # 3 packets transmitted, 3 received, 0% packet loss, time 1998ms
        # 4 packets transmitted, 0 received, +1 errors, 100% packet loss, time 3010ms
        ping_success = re.compile(r'(?P<num_transmitted>\w+) packets transmitted, (?P<num_received>\w+) received,(\s+\+(?P<errors>\w) errors,)? (?P<packet_loss>\w+)% packet loss, time (?P<time>\w+)ms')
        # Take off 28 for header information so our actual packet size is the size requested.
        target_size = size - 28
        # the syntax for -M is a little backwards - if we want it to STOP fragmenting it's "do",
        # if we want it to allow fragmenting it's "don't"
        fragment_str = 'dont' if allow_fragmenting else 'do'
        command_str = 'ping -i {interval_time} -c {count} -M {fragment} -s {size} -I {interface} {target}'
        command = command_str.format(count=count,
                                     fragment=fragment_str,
                                     size=target_size,
                                     interface=interface,
                                     target=target,
                                     interval_time=interval_time)
        # Set result to None to start with - that's what we'll return if we get
        # no matches for success.
        result = None
        # Return the results regardless of status code for parsing:
        try:
            resp = subprocess.check_output(command.split()).splitlines()
        except subprocess.CalledProcessError as ping_exc:
            resp = ping_exc.output.splitlines()

        match_dict = None
        for line in resp:
            match_out = ping_success.search(str(line))
            # If we have a match for ping_success, we want the time from it.
            if match_out:
                match_dict = match_out.groupdict()
                result = int(match_dict.get('time'))
                break
        return result


if __name__ == '__main__':
    with NetworkTester() as TESTER:
        TESTER.listen()
