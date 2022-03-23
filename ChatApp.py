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
        print(prompt + '[Client table updated.]\n>>> ', end='')
        # print(prompt, end='')

    def recv_msg(self, t1, name, msg, clientAddress):
        """
        display the message and send ACK back
        Format of ack is: "ACK MESSAGE "+t1
        """
        ack = "ACK MESSAGE " + t1
        self.socket.sendto(ack.encode(), clientAddress)
        print(prompt + name + ': ' + msg, '\n>>> ', end='')
        # print('>>> ', end='')

    def listening(self):
        while True:
            # print('listening 1 >>>', end='')
            message, clientAddress = self.socket.recvfrom(2048)
            print('[receive from client]:', clientAddress)
            #messages = message.decode().split(' ')
            msg = message.decode()
            #if messages[0] == 'table_copy':  # the request message is: "Registration clientName clientPort status"
            if re.match('table_copy (.+)', msg, flags=re.DOTALL):
                m = re.match('table_copy (.+)', msg, flags=re.DOTALL)
                #print('groups', m.groups())
                self.recv_table(m.groups()[0])
            #elif messages[0] == 'Message':
            elif re.match('Message ([\d.]+) ([\S]+) (.+)', msg, flags=re.DOTALL):
                m = re.match('Message ([\d.]+) ([\S]+) (.+)', msg, flags=re.DOTALL)
                t1, name, mes = m.groups()
                self.recv_msg(t1, name, mes, clientAddress)
            elif re.match('ACK MESSAGE ([\d.]+)', msg):
                m = re.match('ACK MESSAGE ([\d.]+)', msg)
                t1 = m.groups()[0]
                t2 = time.time()
                if t1 == self.wait_ack[1] and t2-float(t1) < 0.5:
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
                            print(prompt+'[Message received by %s.]' % name)
                        else:
                            print(prompt + '[No ACK from %s, message sent to server.]' % name)
                            self.wait_ack = (0, 'null')
                            self.offlineMsg(t1, name, msg)
                        return True
            print(prompt + '[Err: No such user name!]')

    def command(self):
        print('commanding!')
        while True:
            # print('command 1 >>> ', end='')
            cmd = input(prompt)
            # cmds = cmd.split()  # 注意msg里面有空格。需要更改
            if cmd == '':
                pass
            # elif cmd.split()[0] == 'send':
            elif re.match('send ([\S]+) (.+)', cmd, flags=re.DOTALL):
                m = re.match('send ([\S]+) (.+)', cmd, flags=re.DOTALL)
                name, msg = m.groups()
                self.sendMsg(name, msg)
            else:
                print(prompt + '[Err: Canot find the command!]')
            # print('command 2>>> ', end='')


class Server(object):
    def __init__(self, port):
        self.port = int(port)
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.port))
        self.table = './data/serverTable.csv'

    def registration(self, info, clientIp):
        """
        write [clientName, clientIp, clientPort, status] into table file; send the new client the copy of the table;
        broadcast the update to all active clients
        """
        with open(self.table, 'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([info[0], clientIp, info[1], info[2]])
        print('add client to table')
        # self.send_table_copy(clientIp, int(info[1]))
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
            messages = message.decode().split(' ')
            if messages[0] == 'Registration':  # the request message is: "Registration clientName clientPort status"
                clientIp = clientAddress[0]  # we also need to record the client's ip
                self.registration(messages[1:], clientIp)
            else:
                print('Error: wrong request!')


def check_port(port):
    s = socket(AF_INET, SOCK_DGRAM)
    try:
        s.bind(('', int(port)))
        s.close()
        return True
    except:
        print('port not binded! maybe in use')
        return False


if not os.path.exists('./data'):
    os.mkdir('./data')

prompt = ">>> "

if argv[1] == '-s':  # 检查参数个数
    print('server mode!')
    serverPort = argv[2]  # 检查port是否已经占用，以及范围
    if check_port(serverPort):
        print('server port:', serverPort)
        s = Server(serverPort)
        print('Server instance made!')
        s.listening()


elif argv[1] == '-c':
    print('client mode!')
    clientName = argv[2]
    serverIp = argv[3]  # 检查ip地址
    serverPort = argv[4]
    clientPort = argv[5]
    if check_port(clientPort):
        c = Client(clientName, clientPort, serverIp, serverPort)
        c.registration()
        print(prompt + '[Welcome, you are registered.]')
        # c.listening()
        x1 = threading.Thread(target=c.listening)
        x2 = threading.Thread(target=c.command)
        x1.start()
        x2.start()

else:
    print('Error: enter -s or -c')
