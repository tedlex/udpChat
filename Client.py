from socket import *
from sys import argv
import os
import csv
import threading
import re
import time
import datetime

class Client(object):
    def __init__(self, name, port, serverIp, serverPort):
        """
        wait_ack: if it is (1, 'timestamp'), it means we are waiting for the ack for the message we sent at this time
        """
        self.name = name
        self.port = int(port)
        self.serverIp = serverIp
        self.serverPort = int(serverPort)
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.port))
        self.table = './data/localTable_' + self.name + '.csv'
        self.wait_ack = (0, 'null')

    def registration(self):
        """
        The registration request is: "Registration clientName clientPort status".
        The client Ip will be got when the server is receiving the message.
        """
        message = 'Registration ' + self.name + ' ' + str(self.port) + ' online'
        self.socket.sendto(message.encode(), (self.serverIp, self.serverPort))
        print('sent the registration request!')

    def recv_table(self, tableData):
        """
        tableData: "name1,ip1,port1,status1\nname2,,,\n,,,\n"
        """
        # print('receive table copy!')
        rows = tableData.split('\n')
        with open(self.table, 'w') as csvfile:
            writer = csv.writer(csvfile)
            for row in rows[:-1]:  # there is a blank item at last
                writer.writerow(row.split(','))
        print('>>> [Client table updated.]\n>>> ', end='')
        # print(prompt, end='')

    def recv_msg(self, t1, name, msg, clientAddress):
        """
        display the message and send ACK back
        Format of ack is: "ACK MESSAGE "+t1
        """
        ack = "ACK MESSAGE " + t1
        self.socket.sendto(ack.encode(), clientAddress)
        print('>>> ' + name + ': ' + msg, '\n>>> ', end='')
        # print('>>> ', end='')

    def listening(self):
        while True:
            # print('listening 1 >>>', end='')
            message, clientAddress = self.socket.recvfrom(2048)
            print('[receive from client]:', clientAddress)
            # messages = message.decode().split(' ')
            msg = message.decode()
            # if messages[0] == 'table_copy':  # the request message is: "Registration clientName clientPort status"
            if re.match('table_copy (.+)', msg, flags=re.DOTALL):
                m = re.match('table_copy (.+)', msg, flags=re.DOTALL)
                # print('groups', m.groups())
                self.recv_table(m.groups()[0])
            # elif messages[0] == 'Message':
            elif re.match('Message ([\d.]+) ([\S]+) (.+)', msg, flags=re.DOTALL):
                m = re.match('Message ([\d.]+) ([\S]+) (.+)', msg, flags=re.DOTALL)
                t1, name, mes = m.groups()
                self.recv_msg(t1, name, mes, clientAddress)
            elif re.match('ACK MESSAGE ([\d.]+)', msg):
                m = re.match('ACK MESSAGE ([\d.]+)', msg)
                t1 = m.groups()[0]
                t2 = time.time()
                if t1 == self.wait_ack[1] and t2 - float(t1) < 0.5:
                    self.wait_ack = (0, 'null')
            else:
                print('Error: wrong request!')
            # print('listening 2', prompt, end='')

    def offlineMsg(self, t1, name, msg):
        pass

    def sendMsg(self, name, msg):
        with open(self.table, 'r') as csvfile:  # find the ip and port of that name
            reader = csv.reader(csvfile)
            for r in reader:
                if r[0] == name:
                    if r[3] == 'online':
                        t1 = time.time()
                        m = 'Message ' + str(t1) + ' ' + self.name + ' ' + msg
                        self.socket.sendto(m.encode(), (r[1], int(r[2])))
                        self.wait_ack = (1, str(t1))
                        time.sleep(0.5)
                        if self.wait_ack == (0, 'null'):
                            print('>>> [Message received by %s.]' % name)
                        else:
                            print('>>> [No ACK from %s, message sent to server.]' % name)
                            self.wait_ack = (0, 'null')
                            self.offlineMsg(t1, name, msg)
                        return True
            print('>>> [Err: No such user name!]')

    def command(self):
        print('commanding!')
        while True:
            # print('command 1 >>> ', end='')
            cmd = input('>>> ')
            # cmds = cmd.split()  # 注意msg里面有空格。需要更改
            if cmd == '':
                pass
            # elif cmd.split()[0] == 'send':
            elif re.match('send ([\S]+) (.+)', cmd, flags=re.DOTALL):
                m = re.match('send ([\S]+) (.+)', cmd, flags=re.DOTALL)
                name, msg = m.groups()
                self.sendMsg(name, msg)
            else:
                print('>>> [Err: Canot find the command!]')
            # print('command 2>>> ', end='')
