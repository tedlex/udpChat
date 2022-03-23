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
        self.offlineMsg = './data/offline'
        self.check_online_ack = (0, 'null')

    def registration(self, name, port, status, clientIp):
        """
        check if the name is already in use. If yes, send error back.
        If not, write [clientName, clientIp, clientPort, status] into table file, and
        broadcast the update to all active clients
        """
        if os.path.exists(self.table):
            with open(self.table, 'r') as csvfile:
                reader = csv.reader(csvfile)
                for r in reader:
                    if r[0] == name:
                        err = 'ERROR: name %s already in use.' % name
                        self.socket.sendto(err.encode(), (clientIp, int(port)))
                        return False
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

    def reg(self, name, clientAddress):
        self.write_status(name, 'online')
        self.broadcast_table()
        f = self.offlineMsg + '_' + name + '.csv'
        if os.path.exists(f):
            msg = 'OFFLINE MESSAGE >>> You Have Messages.'
            with open(f, 'r') as csvfile:
                reader = csv.reader(csvfile)
                for r in reader:
                    msg += '\n>>> %s: <%s> %s' % (r[0],
                                                  datetime.datetime.fromtimestamp(float(r[1])).strftime('%Y-%m-%d %H:%M:%S'),
                                                  r[2])
            self.socket.sendto(msg.encode(), clientAddress)
            os.remove(f)



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

    def get_info(self, name):
        with open(self.table, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for r in reader:
                if r[0] == name:
                    return r[1], r[2], r[3]

    def write_status(self, name, new_status):
        temp = []
        with open(self.table, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for r in reader:
                if r[0] != name:
                    temp.append(r)
                else:
                    temp.append(r[0:3] + [new_status])
        with open(self.table, 'w') as csvfile:
            writer = csv.writer(csvfile)
            for t in temp:
                writer.writerow(t)

    def check_online(self, name):
        ip, port, status = self.get_info(name)
        t1 = time.time()
        message = "CHECK ONLINE " + str(t1)
        self.socket.sendto(message.encode(), (ip, int(port)))
        self.check_online_ack = (1, str(t1))
        time.sleep(0.5)
        if self.check_online_ack == (0, 'null'):
            return True
        else:
            self.check_online_ack = (0, 'null')
            return False

    def saveMsg(self, sender, receiver, t, msg, clientAddress):
        """
        check if the receiver is indeed offline. If yes, save the msg and send ack. If not,
        send sender the error info and the table.
        """
        if self.check_online(receiver):  # the receiver is online
            err = "ACK SAVE MESSAGE [Client %s exists!]" % receiver
            self.socket.sendto(err.encode(), clientAddress)
            _, _, table_status = self.get_info(receiver)
            if table_status == 'offline':
                self.write_status(receiver, 'online')
                self.broadcast_table()
        else:  # the receiver is offline
            f = self.offlineMsg + '_' + receiver + '.csv'
            with open(f, 'a') as csvfile:
                writter = csv.writer(csvfile)
                writter.writerow([sender, t, msg])
            ack = "ACK SAVE MESSAGE [Messages received by the server and saved.]"
            self.socket.sendto(ack.encode(), clientAddress)
            _, _, table_status = self.get_info(receiver)
            if table_status == 'online':
                self.write_status(receiver, 'offline')
                self.broadcast_table()

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
            elif re.match('Reg ([\w]+)', message):
                m = re.match('Reg ([\w]+)', message)
                name = m.groups()[0]
                self.reg(name, clientAddress)
            elif re.match('SAVE MESSAGE FROM ([\w]+) TO ([\w]+) TIME ([\d.]+) MSG (.+)', message, flags=re.DOTALL):
                m = re.match('SAVE MESSAGE FROM ([\w]+) TO ([\w]+) TIME ([\d.]+) MSG (.+)', message, flags=re.DOTALL)
                sender, receiver, t, msg = m.groups()
                self.saveMsg(sender, receiver, t, msg, clientAddress)
            elif re.match('ACK CHECK ONLINE ([\d.]+)', message):
                m = re.match('ACK CHECK ONLINE ([\d.]+)', message)
                t1 = m.groups()[0]
                t2 = time.time()
                if t1 == self.check_online_ack[1] and t2 - float(t1) < 0.5:
                    self.check_online_ack = (0, 'null')
            else:
                print('Error: wrong request!')