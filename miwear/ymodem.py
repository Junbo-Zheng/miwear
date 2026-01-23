#!/usr/bin/env python3
# -*- coding:UTF-8 -*-
#
# Copyright (C) 2026 Junbo Zheng. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
import binascii
import datetime
import io
import os
import sys
import termios
from time import sleep

import serial

SOH = b"\x01"  # Start of 128-byte data packet
STX = b"\x02"  # Start of 1024-byte data packet
STC = b"\x03"  # Start of a customsize data packet
EOT = b"\x04"  # End of transmission
ACK = b"\x06"  # Acknowledge
NAK = b"\x15"  # Negative acknowledge
CAN = b"\x18"  # Two of these in succession aborts transfer
CRC = b"\x43"  # "C" == 0x43, request 16-bit CRC

PACKET_SIZE = 128
PACKET_1K_SIZE = 1024
EAGAIN = 1
EINVAL = 2
EEOT = 3
RETRIESMAX = 200


def format_time(seconds):
    hours = seconds / 3600
    seconds %= 3600
    minutes = seconds / 60
    seconds %= 60

    time = "%02dh%02dm%02ds" % (int(hours), int(minutes), int(seconds))
    return time


def ymodem_stdread(size):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    new_settings = termios.tcgetattr(fd)
    new_settings[3] &= ~(termios.ICANON | termios.ECHO)
    termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
    data = sys.stdin.buffer.read(size)
    termios.tcflush(sys.stdin, termios.TCIFLUSH)
    sys.stdin.flush()
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return data


def ymodem_stdwrite(data):
    fd = sys.stdout.fileno()
    old_settings = termios.tcgetattr(fd)
    new_settings = termios.tcgetattr(fd)
    new_settings[3] &= ~(termios.ICANON | termios.ECHO)
    termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
    data = sys.stdout.buffer.write(data)
    termios.tcflush(sys.stdout, termios.TCIFLUSH)
    sys.stdout.flush()
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return data


def ymodem_stdclear():
    sys.stdin.flush()
    sys.stdout.flush()


def ymodem_stdprogress(data):
    sys.stderr.write(data)
    sys.stderr.flush()


def ymodem_ser_read(size):
    data = fd_serial.read(size)
    return data


def ymodem_ser_write(data):
    fd_serial.write(data)
    fd_serial.flush()


def ymodem_ser_clear():
    fd_serial.reset_input_buffer()
    fd_serial.reset_output_buffer()


def calc_crc16(data, crc=0):
    crctable = [
        0x0000,
        0x1021,
        0x2042,
        0x3063,
        0x4084,
        0x50A5,
        0x60C6,
        0x70E7,
        0x8108,
        0x9129,
        0xA14A,
        0xB16B,
        0xC18C,
        0xD1AD,
        0xE1CE,
        0xF1EF,
        0x1231,
        0x0210,
        0x3273,
        0x2252,
        0x52B5,
        0x4294,
        0x72F7,
        0x62D6,
        0x9339,
        0x8318,
        0xB37B,
        0xA35A,
        0xD3BD,
        0xC39C,
        0xF3FF,
        0xE3DE,
        0x2462,
        0x3443,
        0x0420,
        0x1401,
        0x64E6,
        0x74C7,
        0x44A4,
        0x5485,
        0xA56A,
        0xB54B,
        0x8528,
        0x9509,
        0xE5EE,
        0xF5CF,
        0xC5AC,
        0xD58D,
        0x3653,
        0x2672,
        0x1611,
        0x0630,
        0x76D7,
        0x66F6,
        0x5695,
        0x46B4,
        0xB75B,
        0xA77A,
        0x9719,
        0x8738,
        0xF7DF,
        0xE7FE,
        0xD79D,
        0xC7BC,
        0x48C4,
        0x58E5,
        0x6886,
        0x78A7,
        0x0840,
        0x1861,
        0x2802,
        0x3823,
        0xC9CC,
        0xD9ED,
        0xE98E,
        0xF9AF,
        0x8948,
        0x9969,
        0xA90A,
        0xB92B,
        0x5AF5,
        0x4AD4,
        0x7AB7,
        0x6A96,
        0x1A71,
        0x0A50,
        0x3A33,
        0x2A12,
        0xDBFD,
        0xCBDC,
        0xFBBF,
        0xEB9E,
        0x9B79,
        0x8B58,
        0xBB3B,
        0xAB1A,
        0x6CA6,
        0x7C87,
        0x4CE4,
        0x5CC5,
        0x2C22,
        0x3C03,
        0x0C60,
        0x1C41,
        0xEDAE,
        0xFD8F,
        0xCDEC,
        0xDDCD,
        0xAD2A,
        0xBD0B,
        0x8D68,
        0x9D49,
        0x7E97,
        0x6EB6,
        0x5ED5,
        0x4EF4,
        0x3E13,
        0x2E32,
        0x1E51,
        0x0E70,
        0xFF9F,
        0xEFBE,
        0xDFDD,
        0xCFFC,
        0xBF1B,
        0xAF3A,
        0x9F59,
        0x8F78,
        0x9188,
        0x81A9,
        0xB1CA,
        0xA1EB,
        0xD10C,
        0xC12D,
        0xF14E,
        0xE16F,
        0x1080,
        0x00A1,
        0x30C2,
        0x20E3,
        0x5004,
        0x4025,
        0x7046,
        0x6067,
        0x83B9,
        0x9398,
        0xA3FB,
        0xB3DA,
        0xC33D,
        0xD31C,
        0xE37F,
        0xF35E,
        0x02B1,
        0x1290,
        0x22F3,
        0x32D2,
        0x4235,
        0x5214,
        0x6277,
        0x7256,
        0xB5EA,
        0xA5CB,
        0x95A8,
        0x8589,
        0xF56E,
        0xE54F,
        0xD52C,
        0xC50D,
        0x34E2,
        0x24C3,
        0x14A0,
        0x0481,
        0x7466,
        0x6447,
        0x5424,
        0x4405,
        0xA7DB,
        0xB7FA,
        0x8799,
        0x97B8,
        0xE75F,
        0xF77E,
        0xC71D,
        0xD73C,
        0x26D3,
        0x36F2,
        0x0691,
        0x16B0,
        0x6657,
        0x7676,
        0x4615,
        0x5634,
        0xD94C,
        0xC96D,
        0xF90E,
        0xE92F,
        0x99C8,
        0x89E9,
        0xB98A,
        0xA9AB,
        0x5844,
        0x4865,
        0x7806,
        0x6827,
        0x18C0,
        0x08E1,
        0x3882,
        0x28A3,
        0xCB7D,
        0xDB5C,
        0xEB3F,
        0xFB1E,
        0x8BF9,
        0x9BD8,
        0xABBB,
        0xBB9A,
        0x4A75,
        0x5A54,
        0x6A37,
        0x7A16,
        0x0AF1,
        0x1AD0,
        0x2AB3,
        0x3A92,
        0xFD2E,
        0xED0F,
        0xDD6C,
        0xCD4D,
        0xBDAA,
        0xAD8B,
        0x9DE8,
        0x8DC9,
        0x7C26,
        0x6C07,
        0x5C64,
        0x4C45,
        0x3CA2,
        0x2C83,
        0x1CE0,
        0x0CC1,
        0xEF1F,
        0xFF3E,
        0xCF5D,
        0xDF7C,
        0xAF9B,
        0xBFBA,
        0x8FD9,
        0x9FF8,
        0x6E17,
        0x7E36,
        0x4E55,
        0x5E74,
        0x2E93,
        0x3EB2,
        0x0ED1,
        0x1EF0,
    ]

    crc = 0x0
    for char in bytearray(data):
        crctbl_idx = ((crc >> 8) ^ char) & 0xFF
        crc = ((crc << 8) ^ crctable[crctbl_idx]) & 0xFFFF
    return crc & 0xFFFF


class ymodem:
    def __init__(
        self,
        read=ymodem_stdread,
        write=ymodem_stdwrite,
        progress=ymodem_stdprogress,
        clear=ymodem_stdclear,
        timeout=100,
        maxretry=RETRIESMAX,
        debug="",
        customsize=0,
    ):
        self.read = read
        self.write = write
        self.clear = clear
        self.timeout = timeout
        self.maxretry = maxretry
        self.progress = progress
        self.customsize = customsize
        self.retries = 0

        if debug != "":
            self.debugfd = open(debug, "w+")
        else:
            self.debugfd = 0

    def debug(self, data):
        if isinstance(self.debugfd, io.RawIOBase):
            self.debugfd.write(data)
            self.debugfd.flush()

    def init_pkt(self):
        self.head = SOH
        self.seq0 = b"\x00"
        self.seq1 = b"\xff"
        self.data = b""
        self.crch = b""
        self.crcl = b""

    def send_pkt(self):
        crc16 = calc_crc16(self.data)
        self.crch = bytes([(crc16 >> 8) & 0xFF])
        self.crcl = bytes([crc16 & 0xFF])
        pkt = self.head + self.seq0 + self.seq1 + self.data + self.crch + self.crcl

        self.write(pkt)

    def add_seq(self):
        seq0 = bytearray(self.seq0)
        if seq0[0] == 0xFF:
            seq0[0] = 0x00
        else:
            seq0[0] += 1

        seq1 = bytearray(self.seq1)
        if seq1[0] == 0x00:
            seq1[0] = 0xFF
        else:
            seq1[0] -= 1

        self.seq0 = bytes(seq0)
        self.seq1 = bytes(seq1)

    def get_pkt_size(self):
        if self.head == SOH:
            return PACKET_SIZE
        elif self.head == STX:
            return PACKET_1K_SIZE
        elif self.head == STC:
            return self.customsize

        return PACKET_SIZE

    def recv_cmd(self, cmd):
        chunk = self.read(1)
        if chunk == NAK:
            return -EAGAIN
        if chunk != cmd:
            self.debug("should be " + binascii.hexlify(cmd).decode("utf-8"))
            self.debug("but receive " + binascii.hexlify(chunk).decode("utf-8") + "\n")
            return -EINVAL

        return 0

    def send_handshake(self):
        self.write(CRC)
        while self.retries < self.maxretry:
            chunk = self.read(1)
            if chunk == CRC:
                return True
            else:
                self.retries += 1
                self.clear()

        self.progress("too many retries\n")
        return False

    def send(self, filelist):
        need_sendfile_num = len(filelist)
        cnt = 0
        now = datetime.datetime.now()
        base = float(int(now.timestamp() * 1000)) / 1000
        totolbytes = 0

        if not self.send_handshake():
            return -EINVAL

        while need_sendfile_num != 0:
            now = datetime.datetime.now()
            start = float(int(now.timestamp() * 1000)) / 1000
            self.init_pkt()
            self.head = SOH
            filename = os.path.basename(filelist[cnt])
            self.data = filename.encode("utf-8")
            self.data = self.data + bytes([0x00] * 1)
            filesize = os.path.getsize(filelist[cnt])
            sendfilesize = 0
            self.data = self.data + str(filesize).encode("utf-8")
            self.data = self.data.ljust(self.get_pkt_size(), b"\x00")
            self.send_pkt()

            ret = self.recv_cmd(ACK)
            if ret == -EAGAIN:
                continue
            elif ret == -EINVAL:
                if self.send_handshake():
                    continue
                return ret

            ret = self.recv_cmd(CRC)
            if ret == -EAGAIN:
                continue
            elif ret == -EINVAL:
                if self.send_handshake():
                    continue
                return ret

            self.progress(f"File: {filename}, Size: {filesize}\n")
            self.add_seq()
            readfd = open(filelist[cnt], "rb")
            while sendfilesize < filesize:
                if sendfilesize + 128 >= filesize:
                    self.head = SOH
                elif self.customsize != 0:
                    self.head = STC
                else:
                    self.head = STX

                self.data = readfd.read(self.get_pkt_size())
                sendbytes = len(self.data)
                self.data = self.data.ljust(self.get_pkt_size(), b"\x00")

                retry = 0
                while retry < 10:
                    self.send_pkt()
                    ret = self.recv_cmd(ACK)
                    if ret < 0:
                        retry += 1
                    else:
                        break

                if retry >= 10:
                    return ret

                self.add_seq()
                sendfilesize += sendbytes
                totolbytes += sendbytes
                self.progress("\r")
                self.progress(
                    "Progress: %6.2f%%" % (float(sendfilesize) / filesize * 100)
                )
                self.progress(" | %d / %d bytes" % (sendfilesize, filesize))
                now = datetime.datetime.now()
                usedtime = float(int(now.timestamp() * 1000) / 1000) - start
                realspeed = sendfilesize / 1024 / usedtime if usedtime > 0 else 0
                left = (
                    (filesize - sendfilesize) / 1024 / (realspeed)
                    if realspeed > 0
                    else 0
                )
                self.progress(" | Speed: %.1f kB/s" % realspeed)
                self.progress(" | ETA: %s" % format_time(left))

            retries = 0
            while True:
                if retries == 2:
                    return -EINVAL
                retries += 1

                self.write(EOT)
                ret = self.recv_cmd(ACK)
                if ret == -EAGAIN:
                    continue
                elif ret < 0:
                    return ret
                ret = self.recv_cmd(CRC)
                if ret == -EAGAIN:
                    continue
                elif ret < 0:
                    return ret
                break

            need_sendfile_num = need_sendfile_num - 1
            readfd.close()
            now = datetime.datetime.now()
            time = float(int(now.timestamp() * 1000) / 1000)
            time = time - start
            self.progress("\n")
            self.progress(
                "File completed: time used: %.1fs, speed: %.1f kB/s\n"
                % (time, float(sendfilesize) / 1024 / time if time > 0 else 0)
            )
            if need_sendfile_num != 0:
                cnt += 1
                continue

            retries = 0
            while True:
                if retries == 2:
                    return -EINVAL
                retries += 1
                self.head = SOH
                self.seq0 = b"\x00"
                self.seq1 = b"\xff"
                self.data = bytes([0x00] * self.get_pkt_size())
                self.send_pkt()

                ret = self.recv_cmd(ACK)
                if ret == -EAGAIN:
                    continue
                elif ret < 0:
                    return ret
                break

        now = datetime.datetime.now()
        time = float(int(now.timestamp() * 1000) / 1000)
        totaltime = time - base
        arvgspeed = float(totolbytes) / 1024 / totaltime if totaltime > 0 else 0
        self.progress(
            "All files completed: total time: %.2fs, average speed: %.2f kB/s"
            % (totaltime, arvgspeed)
        )

    def recv_packet(self):
        chunk = self.read(1)
        if chunk == SOH:
            self.packetsize = PACKET_SIZE
        elif chunk == STX:
            self.packetsize = PACKET_1K_SIZE
        elif chunk == STC:
            self.packetsize = self.customsize
        elif chunk == NAK:
            return -EAGAIN
        elif chunk == EOT:
            return -EEOT
        else:
            self.debug("recv EBADMSG" + str(chunk) + "\n")
            return -EINVAL

        seq0 = self.read(1)
        seq1 = self.read(1)

        self.data = self.read(self.packetsize)

        crch = self.read(1)
        crcl = self.read(1)

        if seq0 != self.seq0:
            self.debug("recv bad seq0" + binascii.hexlify(seq0).decode("utf-8") + "\n")
            return -EINVAL
        if seq1 != self.seq1:
            self.debug("recv bad seq1" + binascii.hexlify(seq1).decode("utf-8") + "\n")
            return -EINVAL

        crc16 = calc_crc16(self.data)

        crch_b = (crc16 >> 8).to_bytes(1, byteorder="little")
        if crch != crch_b:
            self.debug(
                "recv bad crch_b" + binascii.hexlify(crch_b).decode("utf-8") + "\n"
            )
            self.debug("recv bad crch" + binascii.hexlify(crch).decode("utf-8") + "\n")
            return -EINVAL

        crcl_b = (crc16 & 0xFF).to_bytes(1, byteorder="little")
        if crcl != crcl_b:
            self.debug(
                "recv bad crcl_b" + binascii.hexlify(crcl_b).decode("utf-8") + "\n"
            )
            self.debug("recv bad crcl" + binascii.hexlify(crcl).decode("utf-8") + "\n")
            return -EINVAL

        self.add_seq()
        return 0

    def recv(self):
        now = datetime.datetime.now()
        base = float(int(now.timestamp() * 1000)) / 1000
        totolbytes = 0
        self.write(CRC)
        while True:
            now = datetime.datetime.now()
            start = float(int(now.timestamp() * 1000)) / 1000
            self.init_pkt()
            ret = self.recv_packet()

            if ret == -EEOT:
                self.write(ACK)
                self.write(CRC)
                continue

            elif ret < 0:
                if self.retries > self.maxretry:
                    return -1

                # self.progress("recv ret %d\n" % ret)
                self.debug("recv first packet\n")
                self.retries += 1
                continue

            filename = bytes.decode(self.data.split(b"\x00")[0], "utf-8")
            if not filename:
                self.debug("recv a none file\n")
                break

            size_str = bytes.decode(self.data.split(b"\x00")[1], "utf-8")
            filesize = int(size_str)
            self.progress(f"File: {filename}, Size: {filesize}\n")

            self.write(ACK)
            self.write(CRC)
            fd = open(filename, "wb+")
            writensize = 0
            while writensize < filesize:
                ret = self.recv_packet()
                if ret < 0:
                    self.debug("recv a bad data packet\n")
                    if self.retries > self.maxretry:
                        return -1
                    self.retries += 1
                    continue

                size = 0
                if self.packetsize > filesize - writensize:
                    self.debug("last data packet\n")
                    size = filesize - writensize
                else:
                    size = self.packetsize

                data = self.data[0:size]
                fd.write(data)
                writensize += len(data)

                self.progress(
                    "\rProgress: %6.2f%%" % (float(writensize) / filesize * 100)
                )
                self.progress(" | %d / %d bytes" % (writensize, filesize))
                now = datetime.datetime.now()
                usedtime = float(int(now.timestamp() * 1000) / 1000) - start
                realspeed = writensize / 1024 / usedtime if usedtime > 0 else 0
                left = (
                    (filesize - writensize) / 1024 / (realspeed) if realspeed > 0 else 0
                )
                self.progress(" | Speed: %.1f kB/s" % realspeed)
                self.progress(" | ETA: %s" % format_time(left))

                self.write(ACK)

            now = datetime.datetime.now()
            time = float(now.timestamp() * 1000) / 1000
            time = time - start
            self.progress("\n")
            self.progress(
                "File completed: time used: %.1fs, speed: %.1f kB/s\n"
                % (time, float(filesize) / 1024 / time if time > 0 else 0)
            )
            totolbytes += filesize

            fd.close()

        now = datetime.datetime.now()
        time = float(int(now.timestamp() * 1000) / 1000)
        totaltime = time - base
        arvgspeed = float(totolbytes) / 1024 / totaltime if totaltime > 0 else 0
        self.progress(
            "All files completed: total time: %.2fs, average speed: %.2f kB/s"
            % (totaltime, arvgspeed)
        )


def main():
    global fd_serial

    B = "\033[1;34m"
    V = "\033[1;35m"
    L = "\033[1;36m"
    A = "\033[1;33m"
    E = "\033[1;32m"
    N = "\033[0m"

    print(f"\n{B}{'*' * 70}{N}")
    print(f"{E}IMPORTANT:{N} Before running this script, please:")
    print(
        f"{A}1.{N} Execute '{L}rb{N}' (for receiving) or '{L}sb <file>{N}' (for sending) in nsh"
    )
    print(f"{A}2.{N} Immediately exit the terminal after executing the command")
    print(f"{A}3.{N} Let ymodem.py take over the terminal for file transfer")
    print(f"{B}{'*' * 70}{N}\n")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filelist", help="if filelist is valid, that is sb, else is rb", nargs="*"
    )

    parser.add_argument(
        "-k",
        "--kblocksize",
        help="This opthin can set a customsize block size to transfer",
        type=int,
        default=0,
    )

    parser.add_argument(
        "-p", "--port", type=str, default="/dev/ttyACM1", help="device port"
    )

    parser.add_argument(
        "-b",
        "--baudrate",
        type=int,
        default=921600,
    )

    parser.add_argument(
        "-r",
        "--recvfrom",
        type=str,
        nargs="*",
        help="""
            recvfile from board path
            like this:
                ./ymodem.py -r <file1 [file2 [file 3]...]> -p /dev/ttyUBS0
            """,
    )

    parser.add_argument(
        "-s",
        "--sendto",
        type=str,
        nargs=1,
        help="""
            send file to board path
            like this:
                ./ymodem.py -s <path on board> -t /dev/ttyUBS0 <file1 [file2 [file3] ...]>
            """,
    )

    parser.add_argument(
        "--maxretry",
        type=int,
        default=RETRIESMAX,
        help="This opthin set max retry for transmission",
    )

    parser.add_argument(
        "--debug", help="This opthin is save debug log on host", default=""
    )

    args = parser.parse_args()
    print(f"{V}ymodem transfer init, a moment please...{N}")

    if args.port:
        fd_serial = serial.Serial(args.port, baudrate=args.baudrate)
        fd_serial.reset_input_buffer()

        cmd = ("setlogmask -r\r\n").encode()
        fd_serial.write(cmd)
        sleep(0.5)
        fd_serial.reset_input_buffer()

        if args.recvfrom:
            recvfile = ""
            for i in args.recvfrom:
                recvfile += i + " "

            fd_serial.write(("sb %s\r\n" % (recvfile)).encode())
            # tmp = fd_serial.read(len(("sb %s\r\n" % (recvfile)).encode()))
        else:
            if args.sendto:
                cmd = ("rb -f %s\r\n" % (args.sendto[0])).encode()
            else:
                cmd = ("rb\r\n").encode()

            fd_serial.write(cmd)
            sleep(0.5)
            # length = fd_serial.read(len(cmd))
            fd_serial.reset_input_buffer()

        tool = ymodem(
            debug=args.debug,
            customsize=args.kblocksize * 1024,
            read=ymodem_ser_read,
            write=ymodem_ser_write,
            clear=ymodem_ser_clear,
            maxretry=args.maxretry,
        )
    else:
        tool = ymodem(
            debug=args.debug, customsize=args.kblocksize * 1024, maxretry=args.maxretry
        )

    if len(args.filelist) == 0:
        tool.progress("ymodem start receiving\n")
        tool.recv()
        tool.progress("\n")
    else:
        tool.progress("ymodem start sending\n")
        tool.send(args.filelist)
        tool.progress("\n")

    if args.port:
        cmd = ("setlogmask -d\r\n").encode()
        fd_serial.write(cmd)
        sleep(0.3)
        fd_serial.reset_input_buffer()
        fd_serial.write("\n".encode())
        fd_serial.close()


if __name__ == "__main__":
    main()
