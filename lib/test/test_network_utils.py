"""Unit tests for lib/network_utils."""

from __future__ import unicode_literals

import socket
import subprocess
import unittest

from photon.lib import network_utils


class TestNetworkTester(unittest.TestCase):
    """ Unit tests for the NetworkTester class. """

    def test_instantiation(self):
        """ Test that instantiation creates a command_sock. """
        tester = network_utils.NetworkTester()
        self.assertEqual(tester.command_sock.getsockname(),
                         ('0.0.0.0', 55555))

    def test_command_sock(self):
        """ Test that command_sock has correct defaults. """
        tester = network_utils.NetworkTester()
        result = tester.command_sock.connect_ex(('0.0.0.0', 0))
        # We won't connect successfully, but we should be able to generate
        # the correct connection message.
        self.assertEqual(111, result)

    def test_ping(self):
        """ Test that ping can resolve localhost. """
        tester = network_utils.NetworkTester()
        # ping localhost - should always be able to resolve localhost.
        result = tester.ping({})
        self.assertIsInstance(result, int)


class TestGetTCPSocket(unittest.TestCase):
    """ Test that get_tcp_socket is functioning correctly. """

    def test_creates_socket(self):
        """ Test that we create a socket correctly. """
        sock = network_utils.get_tcp_socket()
        socktype = type(sock)
        sock.close()
        real_type = type(socket.socket())
        self.assertEqual(socktype, real_type)

    def test_sock_type(self):
        """ Test that we're creating a SOCK_STREAM type"""
        sock = network_utils.get_tcp_socket()
        self.assertEqual(sock.type,
                         socket.SOCK_STREAM)


class TestGetLocalDefaultIP(unittest.TestCase):
    """ Check that we get the local default IP. """

    def test_local_ip_found(self):
        """ Test that we find our local IP in the default route. """
        ip_route_show = subprocess.check_output('ip route show'.split())
        decoded_ip_route_show = ip_route_show.decode()
        local_ip = network_utils.get_local_default_ip()
        self.assertIn(local_ip, decoded_ip_route_show)
