"""Unit tests for cisco_utils.py."""

from photon.lib import cisco_utils


MGMT0 = """
mgmt0 is up
    Hardware is GigabitEthernet
    Address is c89c.1d41.b550
    Internet address is 10.55.172.148/24
    MTU 1500 bytes, BW 1000 Mbps full Duplex
    72780644 packets input, 3567492152 bytes
      28324342 multicast frames, 0 compressed
      0 input errors
      0 frame
      0 overrun
      0 fifo
    7517904 packets output, 2010548688 bytes
      0 underruns, 0 output errors
      0 collisions, 0 fifo
      0 carrier errors

""".splitlines()

PORT_CHANNEL_1 = """
port-channel1 is up
    Hardware is Fibre Channel
    Port WWN is 24:01:00:0d:ec:3c:06:00
    Admin port mode is auto, trunk mode is off
    snmp link state traps are enabled
    Port mode is F
    Port vsan is 50
    Speed is 32 Gbps
    admin fec state is down
    oper fec state is down
    5 minutes input rate 115810464 bits/sec,14476308 bytes/sec, 8468 frames/sec
    5 minutes output rate 195751936 bits/sec,24468992 bytes/sec, 14165 frames/sec
      181200169488 frames input,293149753678128 bytes
        0 discards,0 errors
        0 invalid CRC/FCS,0 unknown class
        0 too long,0 too short
      302772057121 frames output,501873283644288 bytes
        28755 discards,0 errors
      0 input OLS,0  LRR,0 NOS,0 loop inits
      0 output OLS,0 LRR, 0 NOS, 0 loop inits
    Member[1] : fc1/14
    Member[2] : fc1/15
    Member[3] : fc1/32
    Member[4] : fc1/33
    Interface last changed at Sun Jan 26 18:23:15 2014

""".splitlines()

FC1 = """
sup-fc0 is up
    Hardware is Fibre Channel
    Speed is 1 Gbps
    11370221 packets input, 2070083644 bytes
      0 multicast frames, 0 compressed
      0 input errors, 0 frame
      0 overrun, 0 fifo
    11375606 packets output, 2092390516 bytes
      0 underruns, 0 output errors
      0 collisions, 0 fifo
      0 carrier errors

""".splitlines()

FC2 = """
fc1/1 is up
    Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)
    Port WWN is 20:01:00:0d:ec:a2:8b:80
    Admin port mode is F, trunk mode is off
    snmp link state traps are enabled
    Port mode is F, FCID is 0x3c02c0
    Port vsan is 60
    Speed is 8 Gbps
    Rate mode is shared
    Transmit B2B Credit is 40
    Receive B2B Credit is 32
    Receive data field Size is 2112
    Beacon is turned off
    admin fec state is down
    oper fec state is down
    5 minutes input rate 0 bits/sec,0 bytes/sec, 0 frames/sec
    5 minutes output rate 0 bits/sec,0 bytes/sec, 0 frames/sec
      1021993 frames input,33078709404 bytes
        0 discards,0 errors
        0 invalid CRC/FCS,0 unknown class
        0 too long,0 too short
      2688431 frames output,797885608 bytes
        368 discards,0 errors
      38 input OLS,38  LRR,0 NOS,0 loop inits
      89145 output OLS,0 LRR, 44610 NOS, 0 loop inits
      32 receive B2B credit remaining
      40 transmit B2B credit remaining
      40 low priority transmit B2B credit remaining
    Interface last changed at Sun Oct  9 06:02:47 2016

    Last clearing of "show interface" counters 30w 6d
""".splitlines()

FC3 = """
fc1/1 is up
    Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)
    Port WWN is 20:01:00:0d:ec:a2:8b:80
    Admin port mode is F, trunk mode is off
    snmp link state traps are enabled
    Port mode is F, FCID is 0x3c02c0
    Port vsan is 60
    Speed is 8 Gbps
    Rate mode is shared
    Transmit B2B Credit is 40
    Receive B2B Credit is 32
    Receive data field Size is 2112
    Beacon is turned off
    admin fec state is down
    oper fec state is down
    5 minutes input rate 0 bits/sec,0 bytes/sec, 0 frames/sec
    5 minutes output rate 0 bits/sec,0 bytes/sec, 0 frames/sec
      1021993 frames input,33078709404 bytes
        0 discards,0 errors
        0 invalid CRC/FCS,0 unknown class
        0 too long,0 too short
      2688431 frames output,797885608 bytes
        368 discards,0 errors
      38 input OLS,38  LRR,0 NOS,0 loop inits
      89145 output OLS,0 LRR, 44610 NOS, 0 loop inits
      32 receive B2B credit remaining
      40 transmit B2B credit remaining
      40 low priority transmit B2B credit remaining
    Interface last changed at Sun Oct  9 06:02:47 2016

    Last clearing of "show interface" counters 30w 6d
""".splitlines()

GIGABIT2 = """
mgmt0 is up
admin state is up,
  Hardware: GigabitEthernet, address: 00d7.8fc2.8f58 (bia 00d7.8fc2.8f58)
  Internet Address is 10.1.24.171/22
  MTU 1500 bytes, BW 1000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, medium is broadcast
  full-duplex, 1000 Mb/s
  Auto-Negotiation is turned on
  Auto-mdix is turned off
  EtherType is 0x0000
  1 minute input rate 2736 bits/sec, 2 packets/sec
  1 minute output rate 2520 bits/sec, 2 packets/sec
  Rx
    164708450 input packets 99528756 unicast packets 46262699 multicast packets
    18916995 broadcast packets 19628598979 bytes
  Tx
    101301507 output packets 100495283 unicast packets 806196 multicast packets
    28 broadcast packets 17311765741 bytes

""".splitlines()

ETHERNET1 = """
Ethernet1/1 is down (XCVR not inserted)
admin state is up, Dedicated Interface
  Hardware: 1000/10000 Ethernet, address: 00d7.8fc2.8f60 (bia 00d7.8fc2.8f60)
  MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, medium is broadcast
  Port mode is access
  auto-duplex, auto-speed
  Beacon is turned off
  Auto-Negotiation is turned on, FEC mode is Auto
  Input flow-control is off, output flow-control is off
  Auto-mdix is turned off
  Switchport monitor is off
  EtherType is 0x8100
  EEE (efficient-ethernet) : n/a
  Last link flapped never
  Last clearing of "show interface" counters never
  0 interface resets
  30 seconds input rate 0 bits/sec, 0 packets/sec
  30 seconds output rate 0 bits/sec, 0 packets/sec
  Load-Interval #2: 5 minute (300 seconds)
    input rate 0 bps, 0 pps; output rate 0 bps, 0 pps
  RX
    0 unicast packets  0 multicast packets  0 broadcast packets
    0 input packets  0 bytes
    0 jumbo packets  0 storm suppression packets
    0 runts  0 giants  0 CRC  0 no buffer
    0 input error  0 short frame  0 overrun   0 underrun  0 ignored
    0 watchdog  0 bad etype drop  0 bad proto drop  0 if down drop
    0 input with dribble  0 input discard
    0 Rx pause
  TX
    0 unicast packets  0 multicast packets  0 broadcast packets
    0 output packets  0 bytes
    0 jumbo packets
    0 output error  0 collision  0 deferred  0 late collision
    0 lost carrier  0 no carrier  0 babble  0 output discard
    0 Tx pause
""".splitlines()

ETHERNET2 = """
Ethernet1/11 is up
admin state is up, Dedicated Interface
  Hardware: 1000/10000 Ethernet, address: 00d7.8fc2.8f6a (bia 00d7.8fc2.8f6a)
  MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, medium is broadcast
  Port mode is access
  full-duplex, 10 Gb/s, media type is 10G
  Beacon is turned off
  Auto-Negotiation is turned on, FEC mode is Auto
  Input flow-control is off, output flow-control is off
  Auto-mdix is turned off
  Rate mode is dedicated
  Switchport monitor is off
  EtherType is 0x8100
  EEE (efficient-ethernet) : n/a
  Last link flapped 13week(s) 5day(s)
  Last clearing of "show interface" counters never
  12 interface resets
  30 seconds input rate 23045808 bits/sec, 4917 packets/sec
  30 seconds output rate 8595896 bits/sec, 3810 packets/sec
  Load-Interval #2: 5 minute (300 seconds)
    input rate 37.27 Mbps, 6.12 Kpps; output rate 7.57 Mbps, 3.80 Kpps
  RX
    95214252081 unicast packets  1131178 multicast packets  41951 broadcast packets
    95215425210 input packets  92860331246945 bytes
    0 jumbo packets  0 storm suppression packets
    0 runts  0 giants  0 CRC  0 no buffer
    0 input error  0 short frame  0 overrun   0 underrun  0 ignored
    0 watchdog  0 bad etype drop  0 bad proto drop  0 if down drop
    0 input with dribble  0 input discard
    15211 Rx pause
  TX
    99417109059 unicast packets  29497481 multicast packets  56099967 broadcast packets
    99502706507 output packets  100520486401800 bytes
    0 jumbo packets
    0 output error  0 collision  0 deferred  0 late collision
    0 lost carrier  0 no carrier  0 babble  139257868 output discard
    0 Tx pause
""".splitlines()


def test_separate_iface_lines_mgmt0():
    """Test _separate_iface_lines on mgmt0."""
    expected = {'input': ['72780644 packets input, 3567492152 bytes',
                          '28324342 multicast frames, 0 compressed',
                          '0 input errors',
                          '0 frame',
                          '0 overrun',
                          '0 fifo'],
                'normal': ['mgmt0 is up',
                           'Hardware is GigabitEthernet',
                           'Address is c89c.1d41.b550',
                           'Internet address is 10.55.172.148/24',
                           'MTU 1500 bytes, BW 1000 Mbps full Duplex'],
                'output': ['7517904 packets output, 2010548688 bytes',
                           '0 underruns, 0 output errors',
                           '0 collisions, 0 fifo',
                           '0 carrier errors']}
    # pylint: disable=protected-access
    result = cisco_utils._separate_interface_lines(MGMT0)
    assert expected == result


# pylint: disable=invalid-name
def test_separate_iface_lines_port_channel_1():
    """Test _separate_iface_lines on port_channel_1."""
    expected = {'input': ['181200169488 frames input,293149753678128 bytes',
                          '0 discards,0 errors',
                          '0 invalid CRC/FCS,0 unknown class',
                          '0 too long,0 too short',
                          '0 input OLS,0  LRR,0 NOS,0 loop inits'],
                'normal': ['port-channel1 is up',
                           'Hardware is Fibre Channel',
                           'Port WWN is 24:01:00:0d:ec:3c:06:00',
                           'Admin port mode is auto, trunk mode is off',
                           'snmp link state traps are enabled',
                           'Port mode is F',
                           'Port vsan is 50',
                           'Speed is 32 Gbps',
                           'admin fec state is down',
                           'oper fec state is down',
                           '5 minutes input rate 115810464 bits/sec,14476308 bytes/sec, 8468 frames/sec',
                           '5 minutes output rate 195751936 bits/sec,24468992 bytes/sec, 14165 frames/sec',
                           'Member[1] : fc1/14',
                           'Member[2] : fc1/15',
                           'Member[3] : fc1/32',
                           'Member[4] : fc1/33',
                           'Interface last changed at Sun Jan 26 18:23:15 2014'],
                'output': ['302772057121 frames output,501873283644288 bytes',
                           '28755 discards,0 errors',
                           '0 output OLS,0 LRR, 0 NOS, 0 loop inits']}
    # pylint: disable=protected-access
    result = cisco_utils._separate_interface_lines(PORT_CHANNEL_1)
    assert expected == result


def test_separate_iface_lines_fc1():
    """Test _separate_iface_lines on fc1."""
    expected = {'input': ['11370221 packets input, 2070083644 bytes',
                          '0 multicast frames, 0 compressed',
                          '0 input errors, 0 frame',
                          '0 overrun, 0 fifo'],
                'normal': ['sup-fc0 is up',
                           'Hardware is Fibre Channel',
                           'Speed is 1 Gbps'],
                'output': ['11375606 packets output, 2092390516 bytes',
                           '0 underruns, 0 output errors',
                           '0 collisions, 0 fifo',
                           '0 carrier errors']}
    # pylint: disable=protected-access
    result = cisco_utils._separate_interface_lines(FC1)
    assert expected == result


def test_separate_iface_lines_fc2():
    """Test _separate_iface_lines on fc2."""
    expected = {'input': ['1021993 frames input,33078709404 bytes',
                          '0 discards,0 errors',
                          '0 invalid CRC/FCS,0 unknown class',
                          '0 too long,0 too short',
                          '38 input OLS,38  LRR,0 NOS,0 loop inits',
                          '32 receive B2B credit remaining'],
                'normal': ['fc1/1 is up',
                           'Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)',
                           'Port WWN is 20:01:00:0d:ec:a2:8b:80',
                           'Admin port mode is F, trunk mode is off',
                           'snmp link state traps are enabled',
                           'Port mode is F, FCID is 0x3c02c0',
                           'Port vsan is 60',
                           'Speed is 8 Gbps',
                           'Rate mode is shared',
                           'Transmit B2B Credit is 40',
                           'Receive B2B Credit is 32',
                           'Receive data field Size is 2112',
                           'Beacon is turned off',
                           'admin fec state is down',
                           'oper fec state is down',
                           '5 minutes input rate 0 bits/sec,0 bytes/sec, 0 frames/sec',
                           '5 minutes output rate 0 bits/sec,0 bytes/sec, 0 frames/sec',
                           '40 low priority transmit B2B credit remaining',
                           'Interface last changed at Sun Oct  9 06:02:47 2016',
                           'Last clearing of "show interface" counters 30w 6d'],
                'output': ['2688431 frames output,797885608 bytes',
                           '368 discards,0 errors',
                           '89145 output OLS,0 LRR, 44610 NOS, 0 loop inits',
                           '40 transmit B2B credit remaining']}
    # pylint: disable=protected-access
    result = cisco_utils._separate_interface_lines(FC2)
    assert expected == result


def test_separate_iface_lines_fc3():
    """Test _separate_iface_lines on fc3."""
    expected = {'input': ['1021993 frames input,33078709404 bytes',
                          '0 discards,0 errors',
                          '0 invalid CRC/FCS,0 unknown class',
                          '0 too long,0 too short',
                          '38 input OLS,38  LRR,0 NOS,0 loop inits',
                          '32 receive B2B credit remaining'],
                'normal': ['fc1/1 is up',
                           'Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)',
                           'Port WWN is 20:01:00:0d:ec:a2:8b:80',
                           'Admin port mode is F, trunk mode is off',
                           'snmp link state traps are enabled',
                           'Port mode is F, FCID is 0x3c02c0',
                           'Port vsan is 60',
                           'Speed is 8 Gbps',
                           'Rate mode is shared',
                           'Transmit B2B Credit is 40',
                           'Receive B2B Credit is 32',
                           'Receive data field Size is 2112',
                           'Beacon is turned off',
                           'admin fec state is down',
                           'oper fec state is down',
                           '5 minutes input rate 0 bits/sec,0 bytes/sec, 0 frames/sec',
                           '5 minutes output rate 0 bits/sec,0 bytes/sec, 0 frames/sec',
                           '40 low priority transmit B2B credit remaining',
                           'Interface last changed at Sun Oct  9 06:02:47 2016',
                           'Last clearing of "show interface" counters 30w 6d'],
                'output': ['2688431 frames output,797885608 bytes',
                           '368 discards,0 errors',
                           '89145 output OLS,0 LRR, 44610 NOS, 0 loop inits',
                           '40 transmit B2B credit remaining']}
    # pylint: disable=protected-access
    result = cisco_utils._separate_interface_lines(FC3)
    assert expected == result


# pylint: disable=invalid-name
def test_separate_iface_lines_gigabit2():
    """Test _separate_iface_lines on gigabit2."""
    expected = {'input': ['Rx',
                          '164708450 input packets 99528756 unicast packets 46262699 multicast packets',
                          '18916995 broadcast packets 19628598979 bytes'],
                'normal': ['mgmt0 is up',
                           'admin state is up,',
                           'Hardware: GigabitEthernet, address: 00d7.8fc2.8f58 (bia 00d7.8fc2.8f58)',
                           'Internet Address is 10.1.24.171/22',
                           'MTU 1500 bytes, BW 1000000 Kbit, DLY 10 usec',
                           'reliability 255/255, txload 1/255, rxload 1/255',
                           'Encapsulation ARPA, medium is broadcast',
                           'full-duplex, 1000 Mb/s',
                           'Auto-Negotiation is turned on',
                           'Auto-mdix is turned off',
                           'EtherType is 0x0000',
                           '1 minute input rate 2736 bits/sec, 2 packets/sec',
                           '1 minute output rate 2520 bits/sec, 2 packets/sec'],
                'output': ['Tx',
                           '101301507 output packets 100495283 unicast packets 806196 multicast packets',
                           '28 broadcast packets 17311765741 bytes']}
    # pylint: disable=protected-access
    result = cisco_utils._separate_interface_lines(GIGABIT2)
    assert expected == result


# pylint: disable=invalid-name
def test_separate_iface_lines_ethernet1():
    """Test _separate_iface_lines on ethernet1."""
    expected = {'input': ['RX',
                          '0 unicast packets  0 multicast packets  0 broadcast packets',
                          '0 input packets  0 bytes',
                          '0 jumbo packets  0 storm suppression packets',
                          '0 runts  0 giants  0 CRC  0 no buffer',
                          '0 input error  0 short frame  0 overrun   0 underrun  0 ignored',
                          '0 watchdog  0 bad etype drop  0 bad proto drop  0 if down drop',
                          '0 input with dribble  0 input discard',
                          '0 Rx pause'],
                'normal': ['Ethernet1/1 is down (XCVR not inserted)',
                           'admin state is up, Dedicated Interface',
                           'Hardware: 1000/10000 Ethernet, address: 00d7.8fc2.8f60 (bia 00d7.8fc2.8f60)',
                           'MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec',
                           'reliability 255/255, txload 1/255, rxload 1/255',
                           'Encapsulation ARPA, medium is broadcast',
                           'Port mode is access',
                           'auto-duplex, auto-speed',
                           'Beacon is turned off',
                           'Auto-Negotiation is turned on, FEC mode is Auto',
                           'Input flow-control is off, output flow-control is off',
                           'Auto-mdix is turned off',
                           'Switchport monitor is off',
                           'EtherType is 0x8100',
                           'EEE (efficient-ethernet) : n/a',
                           'Last link flapped never',
                           'Last clearing of "show interface" counters never',
                           '0 interface resets',
                           '30 seconds input rate 0 bits/sec, 0 packets/sec',
                           '30 seconds output rate 0 bits/sec, 0 packets/sec',
                           'Load-Interval #2: 5 minute (300 seconds)',
                           'input rate 0 bps, 0 pps; output rate 0 bps, 0 pps'],
                'output': ['TX',
                           '0 unicast packets  0 multicast packets  0 broadcast packets',
                           '0 output packets  0 bytes',
                           '0 jumbo packets',
                           '0 output error  0 collision  0 deferred  0 late collision',
                           '0 lost carrier  0 no carrier  0 babble  0 output discard',
                           '0 Tx pause']}
    # pylint: disable=protected-access
    result = cisco_utils._separate_interface_lines(ETHERNET1)
    assert expected == result


def test_separate_iface_lines_ethernet2():
    """Test _separate_iface_lines on ethernet2."""
    expected = {'input': ['RX',
                          '95214252081 unicast packets  1131178 multicast packets  41951 broadcast packets',
                          '95215425210 input packets  92860331246945 bytes',
                          '0 jumbo packets  0 storm suppression packets',
                          '0 runts  0 giants  0 CRC  0 no buffer',
                          '0 input error  0 short frame  0 overrun   0 underrun  0 ignored',
                          '0 watchdog  0 bad etype drop  0 bad proto drop  0 if down drop',
                          '0 input with dribble  0 input discard',
                          '15211 Rx pause'],
                'normal': ['Ethernet1/11 is up',
                           'admin state is up, Dedicated Interface',
                           'Hardware: 1000/10000 Ethernet, address: 00d7.8fc2.8f6a (bia 00d7.8fc2.8f6a)',
                           'MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec',
                           'reliability 255/255, txload 1/255, rxload 1/255',
                           'Encapsulation ARPA, medium is broadcast',
                           'Port mode is access',
                           'full-duplex, 10 Gb/s, media type is 10G',
                           'Beacon is turned off',
                           'Auto-Negotiation is turned on, FEC mode is Auto',
                           'Input flow-control is off, output flow-control is off',
                           'Auto-mdix is turned off',
                           'Rate mode is dedicated',
                           'Switchport monitor is off',
                           'EtherType is 0x8100',
                           'EEE (efficient-ethernet) : n/a',
                           'Last link flapped 13week(s) 5day(s)',
                           'Last clearing of "show interface" counters never',
                           '12 interface resets',
                           '30 seconds input rate 23045808 bits/sec, 4917 packets/sec',
                           '30 seconds output rate 8595896 bits/sec, 3810 packets/sec',
                           'Load-Interval #2: 5 minute (300 seconds)',
                           'input rate 37.27 Mbps, 6.12 Kpps; output rate 7.57 Mbps, 3.80 Kpps'],
                'output': ['TX',
                           '99417109059 unicast packets  29497481 multicast packets  56099967 broadcast packets',
                           '99502706507 output packets  100520486401800 bytes',
                           '0 jumbo packets',
                           '0 output error  0 collision  0 deferred  0 late collision',
                           '0 lost carrier  0 no carrier  0 babble  139257868 output discard',
                           '0 Tx pause']}
    # pylint: disable=protected-access
    result = cisco_utils._separate_interface_lines(ETHERNET2)
    assert expected == result


def test_no_lines_left_behind():
    """Test that we reference all the lines that we expect to reference within the interfaces."""
    all_ports = [MGMT0, PORT_CHANNEL_1, FC1, FC2, FC3, GIGABIT2, ETHERNET1, ETHERNET2]
    unreferenced_lines = set()

    # Go through each port and check for unreferenced lines.  If there's a line we don't reference
    # and we should be, it'll show up there. we're not actually saving lines, we're recording the
    # line numbers that the values are found in, to set them as a "referenced line", and then seeing
    # what's left if we don't reference anything.
    for port in all_ports:
        # We'll remove empty lines from the unreference set because there's no data we care
        # about in the empty lines
        empty_lines = []
        interface_lines = tuple(enumerate(port))
        # getting line numbers of each line.
        line_nos = set([line_tuple[0] for line_tuple in interface_lines])
        has_it = set()
        interface = cisco_utils.get_interface_dict(port)
        # Go through our interface dicts and our interface lines and check to
        # make sure that all lines are referenced by someone.
        for val in interface.values():
            # We're going to reference these lines by index number.
            for index, interface_line in interface_lines:
                # There are some raw lines that are still around, this is expected, so we'll remove them
                if not interface_line:
                    empty_lines.append(index)
                    continue
                # If our value is in the interface line, we consider it referenced.
                if val.lower() in interface_line.lower():
                    has_it.add(index)
        # Find all our line numbers that haven't been referenced for this port (all line numbers - referenced - empty)
        no_references = line_nos - set([index for index in has_it]) - set(empty_lines)
        for line_no in no_references:
            # port is our original list of lines, so we're adding the original line that is still not referenced
            # to our unreferenced_lines set.
            unreferenced_lines.add(port[line_no])
    # We legitimately don't reference these lines.
    # For a new "interface" set - just add another interface to the list above, and if there are unreferenced
    # once it's added, add the needed processing.
    assert unreferenced_lines == {'  RX', '  Rx', '  TX', '  Tx'}


def test_zoneset_repr():
    """Make sure we instantiate zoneset correctly."""
    test_zoneset = cisco_utils.ZoneSet('Test ZoneSet', 23)
    assert test_zoneset.name == 'Test ZoneSet'
    assert test_zoneset.vsan == 23
    assert repr(test_zoneset) == "<ZoneSet(name='Test ZoneSet', vsan=23)>"


def test_zone_repr():
    """Make sure we instantiate zone correctly."""
    test_zone = cisco_utils.Zone('Test Zone', 23)
    assert test_zone.name == 'Test Zone'
    assert test_zone.vsan == 23
    assert repr(test_zone), "<Zone(name='Test Zone' == vsan=23)>"


def test_alias_and_fcid():
    """Test with alias/fcidwwn."""
    member_line = '  * fcid 0x654321 [pwwn 21:00:00:e0:8b:92:ce:84] [FakeAlias]'
    member = cisco_utils.Member(member_line)
    assert member.fcid == '0x654321'
    assert member.pwwn == '21:00:00:e0:8b:92:ce:84'
    assert member.alias == 'FakeAlias'
    assert member.is_pure is False


def test_alias_no_fcid():
    """Test with alias/wwn."""
    member_line = '    pwwn 21:00:00:e0:8b:92:ce:84 [FakeAlias]'
    member = cisco_utils.Member(member_line)
    assert member.fcid is None
    assert member.pwwn == '21:00:00:e0:8b:92:ce:84'
    assert member.alias == 'FakeAlias'
    assert member.is_pure is False


def test_no_alias_or_fcid():
    """Test with wwn."""
    member_line = '    pwwn 21:00:00:e0:8b:92:ce:84'
    member = cisco_utils.Member(member_line)
    assert member.fcid is None
    assert member.pwwn == '21:00:00:e0:8b:92:ce:84'
    assert member.alias is None
    assert member.is_pure is False


def test_no_alias_fcid():
    """Test with fcid and wwn."""
    member_line = '  * fcid 0x654321 [pwwn 21:00:00:e0:8b:92:ce:84]'
    member = cisco_utils.Member(member_line)
    assert member.fcid == '0x654321'
    assert member.pwwn == '21:00:00:e0:8b:92:ce:84'
    assert member.alias is None
    assert member.is_pure is False


def test_pure():
    """Test with alias/fcid/wwn and is pure."""
    member_line = '  * fcid 0x654321 [pwwn 52:4a:93:77:59:62:b2:12] [FakeAlias]'
    member = cisco_utils.Member(member_line)
    assert member.fcid == '0x654321'
    assert member.pwwn == '52:4a:93:77:59:62:b2:12'
    assert member.alias == 'FakeAlias'
    assert member.is_pure is True


def test_fake_pure():
    """Test with alias/fcid/wwn and is not pure."""
    member_line = '  * fcid 0x654321 [pwwn 77:59:62:b2:12:52:4a:93] [FakeAlias]'
    member = cisco_utils.Member(member_line)
    assert member.fcid == '0x654321'
    assert member.pwwn == '77:59:62:b2:12:52:4a:93'
    assert member.alias == 'FakeAlias'
    assert member.is_pure is False


def test_alias_and_fcid_no_wwn():
    """Test with alias/fcid and no wwn."""
    member_line = '  * fcid 0x654321 [FakeAlias]'
    member = cisco_utils.Member(member_line)
    assert member.fcid == '0x654321'
    assert member.pwwn is None
    assert member.alias == 'FakeAlias'
    assert member.is_pure is False


def test_good_line():
    """Test that we don't screw up a good line."""
    good_line = '0 input errors, 0 frame, 0 overrun, 0 fifo'
    expected = ['0 input errors', '0 frame', '0 overrun', '0 fifo']
    # pylint: disable=protected-access
    result = cisco_utils._prep_line(good_line)
    assert result == expected


def test_bad_line():
    """Test that we fix a bad line."""
    bad_line = '0 input errors, 0 frame, 0 overrun 0 fifo'
    expected = ['0 input errors', '0 frame', '0 overrun', '0 fifo']
    # pylint: disable=protected-access
    result = cisco_utils._prep_line(bad_line)
    assert result == expected


def test_good_and_bad_lines():
    """Test good and bad loads."""
    good_line = '0 input errors, 0 frame, 0 overrun, 0 fifo'
    bad_line = '0 input errors, 0 frame, 0 overrun 0 fifo'
    lines = [good_line, bad_line]
    # pylint: disable=protected-access
    result = cisco_utils._prep_lines(lines)
    expected = ['0 input errors', '0 frame', '0 overrun', '0 fifo', '0 input errors', '0 frame', '0 overrun', '0 fifo']
    assert result == expected
