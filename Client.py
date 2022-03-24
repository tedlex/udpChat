from socket import *
from sys import argv
import os
import csv
import threading
import re
import time
import datetime

prompt = '\n>>> '

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
        self.dereg_ack = (0, 'null')
        self.status = 1  # 1. online  0.offline
        self.channel_ack = (0, 'null')

    def registration(self):
        """
        The registration request is: "Registration clientName clientPort status".
        The client Ip will be got when the server is receiving the message.
        """
        message = 'Registration ' + self.name + ' ' + str(self.port) + ' online'
        self.socket.sendto(message.encode(), (self.serverIp, self.serverPort))
        # print('sent the registration request!')

    def dereg(self):
        self.status = 0
        for i in range(5):
            t1 = time.time()
            message = "Dereg " + str(t1) + ' ' + self.name
            self.socket.sendto(message.encode(), (self.serverIp, self.serverPort))
            self.dereg_ack = (1, str(t1))
            time.sleep(0.5)
            if self.dereg_ack == (0, 'null'):
                print('[You are offline. Bye.]', end=prompt)
                return True
        print('[Server not responding.]\n>>> [Exiting.]', end=prompt)
        return False

    def reg(self):
        message = "Reg " + self.name
        self.socket.sendto(message.encode(), (self.serverIp, self.serverPort))
        self.status = 1

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
        print('[Client table updated.]', end=prompt)
        # print(prompt, end='')

    def recv_msg(self, t1, name, msg, clientAddress):
        """
        display the message and send ACK back
        Format of ack is: "ACK MESSAGE "+t1
        """
        ack = "ACK MESSAGE " + t1
        self.socket.sendto(ack.encode(), clientAddress)
        print(name + ': ' + msg, '\n>>> ', end='')
        # print('>>> ', end='')

    def listening(self):
        while True:
            # print('listening 1 >>>', end='')
            message, clientAddress = self.socket.recvfrom(2048)
            #print('[receive from client]:', clientAddress)
            # messages = message.decode().split(' ')
            msg = message.decode()
            # if messages[0] == 'table_copy':  # the request message is: "Registration clientName clientPort status"
            if re.match('table_copy (.+)', msg, flags=re.DOTALL):
                m = re.match('table_copy (.+)', msg, flags=re.DOTALL)
                # print('groups', m.groups())
                self.recv_table(m.groups()[0])
            # elif messages[0] == 'Message':
            elif re.match('Message ([\d.]+) ([\S]+) (.+)', msg, flags=re.DOTALL):
                if self.status == 1:
                    m = re.match('Message ([\d.]+) ([\S]+) (.+)', msg, flags=re.DOTALL)
                    t1, name, mes = m.groups()
                    self.recv_msg(t1, name, mes, clientAddress)
            elif re.match('ACK MESSAGE ([\d.]+)', msg):
                m = re.match('ACK MESSAGE ([\d.]+)', msg)
                t1 = m.groups()[0]
                t2 = time.time()
                if t1 == self.wait_ack[1] and t2 - float(t1) < 0.5:
                    self.wait_ack = (0, 'null')
            elif re.match('ACK DEREG ([\d.]+)', msg):
                m = re.match('ACK DEREG ([\d.]+)', msg)
                t1 = m.groups()[0]
                t2 = time.time()
                if t1 == self.dereg_ack[1] and t2 - float(t1) < 0.5:
                    self.dereg_ack = (0, 'null')
            elif re.match('ACK SAVE MESSAGE (.+)', msg):
                m = re.match('ACK SAVE MESSAGE (.+)', msg)
                print(m.groups()[0] + '\n>>> ', end='')
            elif re.match('ERROR', msg):
                print('>>> [' + msg + ']')
            elif re.match('CHECK ONLINE ([\d.]+)', msg):
                if self.status == 1:
                    m = 'ACK ' + msg
                    self.socket.sendto(m.encode(), clientAddress)
            elif re.match('OFFLINE MESSAGE (.+)', msg, flags=re.DOTALL):
                m = re.match('OFFLINE MESSAGE (.+)', msg, flags=re.DOTALL)
                offMsg = m.groups()[0]
                print(offMsg, end='\n>>> ')
            elif re.match('ACK CHANNEL SENDER T0 ([\d.]+) T1 ([\d.]+)', msg):
                m = re.match('ACK CHANNEL SENDER T0 ([\d.]+) T1 ([\d.]+)', msg)
                t0, t1 = m.groups()
                t2 = time.time()
                if t1 == self.channel_ack[1] and t2 - float(t1) < 0.5:
                    self.channel_ack = (0, 'null')
            elif re.match('FORWARD FROM ([\w]+) TIME ([\d.]+) MSG (.+)', msg, flags=re.DOTALL):
                m = re.match('FORWARD FROM ([\w]+) TIME ([\d.]+) MSG (.+)', msg, flags=re.DOTALL)
                sender, t2, ms = m.groups()
                print('>>> Channel Message ' + sender + ': ' + ms)
                ack = 'ACK FORWARD ' + t2 + ' ' + self.name
                self.socket.sendto(ack.encode(), (self.serverIp, self.serverPort))
            else:
                print('Error: wrong request ' + msg)
            # print('listening 2', prompt, end='')

    def saveMsg(self, t1, name, msg):
        message = "SAVE MESSAGE FROM " + self.name + ' TO ' + name + ' TIME ' + str(t1) + ' MSG ' + msg
        self.socket.sendto(message.encode(), (self.serverIp, self.serverPort))

    def sendMsg(self, name, msg):
        with open(self.table, 'r') as csvfile:  # find the ip and port of that name
            t1 = time.time()
            reader = csv.reader(csvfile)
            for r in reader:
                if r[0] == name:
                    #if r[3] == 'online':
                    m = 'Message ' + str(t1) + ' ' + self.name + ' ' + msg
                    self.socket.sendto(m.encode(), (r[1], int(r[2])))
                    self.wait_ack = (1, str(t1))
                    time.sleep(0.5)
                    if self.wait_ack == (0, 'null'):
                        print('[Message received by %s.]' % name, end=prompt)
                    else:
                        print('[No ACK from %s, message sent to server.]' % name, end=prompt)
                        self.wait_ack = (0, 'null')
                        self.saveMsg(t1, name, msg)
                    #else:  # the receiver is offline in local table
                        #self.saveMsg(t1, name, msg)
                    return True
            print('>>> [Err: No such user name!]')

    def channelMsg(self, msg, t0):
        for i in range(5):
            t1 = time.time()
            m = 'CHANNEL MESSAGE FROM ' + self.name + ' T ' + str(t0) + ' TIME ' + str(t1) + ' MSG ' + msg
            self.socket.sendto(m.encode(), (self.serverIp, self.serverPort))
            self.channel_ack = (1, str(t1))
            time.sleep(0.5)
            if self.channel_ack == (0, 'null'):
                print('[ Message received by server.]', end=prompt)
                return True
        print('[Server not responding.]')
        return False

    def command(self):
        #print('commanding!')
        while True:
            # print('command 1 >>> ', end='')
            cmd = input('')
            print('>>> ', end='')
            # cmds = cmd.split()  # 注意msg里面有空格。需要更改
            if cmd == '':
                pass
            # elif cmd.split()[0] == 'send':
            elif re.match('send ([\S]+) (.+)', cmd, flags=re.DOTALL):
                m = re.match('send ([\S]+) (.+)', cmd, flags=re.DOTALL)
                name, msg = m.groups()
                self.sendMsg(name, msg)
            elif re.match('dereg', cmd):
                self.dereg()
            elif re.match('reg', cmd):
                self.reg()
            elif re.match('send_all (.+)', cmd):
                m = re.match('send_all (.+)', cmd)
                msg = m.groups()[0]
                t0 = time.time()
                self.channelMsg(msg, t0)
            else:
                print('[Err: Canot find the command!]', end=prompt)
            # print('command 2>>> ', end='')

