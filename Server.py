from socket import *
from sys import argv
import os
import csv
import threading
import re
import time
import datetime


class Server(object):
    def __init__(self, port):
        self.port = int(port)
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.port))
        self.table = './data/serverTable.csv'

    def registration(self, name, port, status, clientIp):
        """
        write [clientName, clientIp, clientPort, status] into table file; send the new client the copy of the table;
        broadcast the update to all active clients
        """
        with open(self.table, 'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([name, clientIp, port, status])
        print('add client to table')
        # self.send_table_copy(clientIp, int(info[1]))
        self.broadcast_table()
        print('broadcast new table to all active clients!')

    def dereg(self, t1, name, clientAddress):
        """
        send ack of dereg back, update the table, and broadcast new table to all active users
        """
        ack = "ACK DEREG " + t1
        self.socket.sendto(ack.encode(), clientAddress)
        temp = []
        with open(self.table, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for r in reader:
                if r[0] != name:
                    temp.append(r)
                else:
                    temp.append(r[0:3]+['offline'])
        with open(self.table, 'w') as csvfile:
            writer = csv.writer(csvfile)
            for t in temp:
                writer.writerow(t)
        self.broadcast_table()
        print('broadcast new table to all active clients!')

    def send_table_copy(self, clientIp, clientPort):
        with open(self.table, 'r') as csvfile:
            reader = csv.reader(csvfile)
            tableData = ''
            for r in reader:
                tableData += r[0] + ',' + r[1] + ',' + r[2] + ',' + r[3]
                tableData += '\n'
            message = 'table_copy ' + tableData
        self.socket.sendto(message.encode(), (clientIp, clientPort))

    def broadcast_table(self):
        # message = ''  # "table_copt tableData" will be sent to all active users
        with open(self.table, 'r') as csvfile:  # construct tableData from server table file
            reader = csv.reader(csvfile)
            tableData = ''
            for r in reader:
                tableData += r[0] + ',' + r[1] + ',' + r[2] + ',' + r[3]
                tableData += '\n'
        message = 'table_copy ' + tableData  # "table_copy tableData" will be sent to all active users
        with open(self.table, 'r') as csvfile:  # find all online users
            reader = csv.reader(csvfile)
            for r in reader:
                if r[3] == 'online':
                    self.socket.sendto(message.encode(), (r[1], int(r[2])))

    def listening(self):
        print('server listening')
        while True:
            message, clientAddress = self.socket.recvfrom(2048)
            print('receive from client:', clientAddress)
            # messages = message.decode().split(' ')
            message = message.decode()
            if re.match('Registration ([\w]+) ([\d]+) (online|offline)', message):
                m = re.match('Registration ([\w]+) ([\d]+) (online|offline)', message)
                name, port, status = m.groups()
                # if messages[0] == 'Registration':
                # the request message is: "Registration clientName clientPort status"
                clientIp = clientAddress[0]  # we also need to record the client's ip
                self.registration(name, port, status, clientIp)
            elif re.match('Dereg ', message):
                m = re.match('Dereg ([\d.]+) ([\w]+)', message)
                t1, name = m.groups()
                self.dereg(t1, name, clientAddress)
            else:
                print('Error: wrong request!')