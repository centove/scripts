#!/usr/bin/env python
# RDP protocol is based on a protocol called X.224, this will test the very basic
# X.224 protocol operations. Gives a slightly better indication of rdp working or
# not vs just checking that it's listening on port 3389
# References:
# TPKT:  http://www.itu.int/rec/T-REC-T.123/
# X.224: http://www.itu.int/rec/T-REC-X.224/en

import os
import sys
import socket
import struct
import select
import time
import argparse

ICMP_ECHO_REQUEST = 8
# Raw socket stuff
def checksum(source_string):
    sum = 0
    countTo = (len(source_string)/2)*2
    count = 0
    while (count < countTo):
        thisVal = ord(source_string[count + 1]) * 256 + ord(source_string[count])
        sum += thisVal
        sum = sum & 0xffffffff
        count += 2
    if countTo < len(source_string):
        sum += ord(source_string[len(source_string) - 1])
        sum = sum & 0xffffffff
    sum = (sum >> 16) + (sum & 0xffff)
    sum += (sum >> 16)
    answer = ~sum
    answer = answer & 0xffff
    # swap and return
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def receive_one_ping(my_socket, ID, timeout):
    """
    receive the ping from the socket.
    """
    timeLeft = timeout
    while True:
        startedSelect = time.time()
        whatReady = select.select([my_socket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []: # Timeout
            return
 
        timeReceived = time.time()
        recPacket, addr = my_socket.recvfrom(1024)
        icmpHeader = recPacket[20:28]
        type, code, checksum, packetID, sequence = struct.unpack(
            "bbHHh", icmpHeader
        )
        if packetID == ID:
            bytesInDouble = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0]
            return timeReceived - timeSent
 
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return

def send_one_ping(my_socket, dest_addr, ID):
    """
    Send one ping to the given >dest_addr<.
    """
    dest_addr  =  socket.gethostbyname(dest_addr)
 
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    my_checksum = 0
 
    # Make a dummy heder with a 0 checksum.
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
    bytesInDouble = struct.calcsize("d")
    data = (192 - bytesInDouble) * "Q"
    data = struct.pack("d", time.time()) + data
 
    # Calculate the checksum on the data and the dummy header.
    my_checksum = checksum(header + data)
 
    # Now that we have the right checksum, we put that in. It's just easier
    # to make up a new header than to stuff it into the dummy.
    header = struct.pack(
        "bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), ID, 1
    )
    packet = header + data
    my_socket.sendto(packet, (dest_addr, 1)) # Don't know about the 1

def do_rdp_conn(hostname,port,setup_payload,teardown_payload):
    try:
        s = socket.socket()
        t1 = time.time()

        # connect
        s.connect((hostname,port))
        sent_bytes = s.send(setup_payload)
        if sent_bytes != len(setup_payload):
            print('Could not send RDP setup payload')
            sys.exit(2)
        setup_received = s.recv(1024)
        t2 = time.time()

        # disconnect
        sent_bytes = s.send(teardown_payload)
        if sent_bytes != len(teardown_payload):
            print('x224 CRITICAL: Could not send RDP teardown payload')
            sys.exit(2)
        s.close()

        elapsed = t2 - t1

        l_setup_received = len(setup_received)
        l_expected_short = 11
        l_expected_long  = 19
        if l_setup_received <> l_expected_short and l_setup_received <> l_expected_long:
            print('x224 CRITICAL: RDP response of unexpected length (%d)' % l_setup_received)
            sys.exit(2)
    except socket.error, e:
        if e[0] == -2:
            print("x224 UNKNOWN: Could not resolve hostname '%s': %s" % (hostname,e))
            sys.exit(3)
        print('x224 CRITICAL: Could not set up connection on port %d: %s' % (port,e))
        sys.exit(2)
    except Exception, e:
        print('x224 CRITICAL: Problem communicating with RDP server: %s' % e)
        sys.exit(2)
    return (elapsed,setup_received)

def check_host(hostname, port):
    print ("checking %s @ %d") % (hostname, port)
    # try and ping the host first
    icmp = socket.getprotobyname("icmp")
    try:
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
    except socket.error, (errno, msg):
        if errno == 1:
            # Operation not permitted - need root for raw sockets
            msg = msg + (" - Note ICMP messages can only be sent from processes running as root.")
            raise socket.error(msg)
        raise
    # got the socket
    my_ID = os.getpid() & 0xFFFF
    send_one_ping(my_socket, hostname, my_ID)
    delay = receive_one_ping(my_socket, my_ID, 2)
    my_socket.close()
    print ("Host is alive, testing RDP connection...")
    
    socket.setdefaulttimeout(5)
    setup_x224_cookie = "Cookie: msthash=\r\n"
    setup_x224_rdp_neg_data = struct.pack('<BBHI', 1, 0, 8, 3)
    setup_x224_header = struct.pack('!BBHHB', len(setup_x224_cookie) + 6 + 8, 224, 0, 0, 0)
    setup_x224 = setup_x224_header + setup_x224_cookie + setup_x224_rdp_neg_data
    tpkt_total_len = len(setup_x224) + 4
    setup_tpkt_header = struct.pack('!BBH', 3, 0, tpkt_total_len)
    setup_payload = setup_tpkt_header + setup_x224
    teardown_payload = struct.pack('!BBHBBBBBBB', 3, 0, 11, 6, 128, 0, 0, 0, 0, 0)
    elapsed, rec = do_rdp_conn(hostname, port, setup_payload, teardown_payload)

    rec_tpkt_header={}
    rec_x224_header={}
    rec_nego_resp  ={}

    # Older Windows hosts will return with a short answer
    if len(rec) == 11:
        rec_tpkt_header['version'],         \
            rec_tpkt_header['reserved'],    \
            rec_tpkt_header['length'],      \
                                            \
            rec_x224_header['length'],      \
            rec_x224_header['code'],        \
            rec_x224_header['dst_ref'],     \
            rec_x224_header['src_ref'],     \
            rec_x224_header['class'],       \
            = struct.unpack('!BBHBBHHB',rec)
    else:
        # Newer Windows hosts will return with a longer answer
        rec_tpkt_header['version'],         \
            rec_tpkt_header['reserved'],    \
            rec_tpkt_header['length'],      \
                                            \
            rec_x224_header['length'],      \
            rec_x224_header['code'],        \
            rec_x224_header['dst_ref'],     \
            rec_x224_header['src_ref'],     \
            rec_x224_header['class'],       \
                                            \
            rec_nego_resp['type'],          \
            rec_nego_resp['flags'],         \
            rec_nego_resp['length'],        \
            rec_nego_resp['selected_proto'] \
            = struct.unpack('!BBHBBHHBBBHI',rec)

    if rec_tpkt_header['version'] <> 3:
        print('x224 CRITICAL: Unexpected version-value(%d) in TPKT response' % rec_tpkt_header['version'])
        sys.exit(2)

    # 13 = binary 00001101; corresponding to 11010000 shifted four times
    # dst_ref=0 and class=0 was asked for in the connection setup
    if (rec_x224_header['code'] >> 4) <> 13 or \
            rec_x224_header['dst_ref'] <> 0 or \
            rec_x224_header['class'] <> 0:
        print('x224 CRITICAL: Unexpected element(s) in X.224 response')
    print('x224 OK. Connection setup time: %f sec.' % (elapsed))
    
def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-p', '--port', default=3389, type=int, help="port [default 3389]")
    parser.add_argument('hostname', help="hostname/ip to check")
    
    args = parser.parse_args()
    check_host (args.hostname, args.port)
    
    
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

