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
        self.last_channel_t0 = 0
        self.ack_channel_recv = (0, [])

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
        #print('add client to table')
        # self.send_table_copy(clientIp, int(info[1]))
        self.broadcast_table()
        #print('broadcast new table to all active clients!')

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
            msg = 'OFFLINE MESSAGE You Have Messages.'
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
        print('检查是否在线：', message)
        self.check_online_ack = (1, str(t1))
        print('开始sleep')
        time.sleep(0.5)
        print('结束sleep')
        if self.check_online_ack == (0, 'null'):
            print(name, '在线')
            return True
        else:
            print(name, '不在线')
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

    def channelMsg(self, name, t0, t1, msg, clientAddress):
        """
        send ack to the sender
        check if the msg has been forwarded by checking self.last_channel_t0. If not,
        forward msg to online clients except for sender (wait ack)
        and write into offline files (duplicate)
        """
        ack = 'ACK CHANNEL SENDER T0 ' + str(t0) + ' T1 ' + str(t1)
        self.socket.sendto(ack.encode(), clientAddress)
        if float(t0) > self.last_channel_t0:  # it's a new channel msg
            #print('转发并写入', name, msg)
            self.last_channel_t0 = float(t0)
            online_list = []
            offline_list = []
            check_list = []  # online in server table but no ack back
            with open(self.table, 'r') as csvfile:
                reader = csv.reader(csvfile)
                for r in reader:
                    if r[3] == 'online':
                        online_list.append((r[0], r[1], r[2]))
                    else:
                        offline_list.append((r[0], r[1], r[2]))
            #print('online list', online_list)
            #print('offline list', offline_list)
            # forward to all online clients
            t2 = time.time()
            m = "FORWARD FROM " + name + ' TIME ' + str(t2) + ' MSG ' + msg
            self.ack_channel_recv = (str(t2), [])
            #print('ack_channel_recv', self.ack_channel_recv)
            for c in online_list:
                self.socket.sendto(m.encode(), (c[1], int(c[2])))
            #print('sleep 1 开始')
            time.sleep(0.5)
            #print('sleep 1 结束')
            for c in online_list:
                if c[0] not in self.ack_channel_recv[1]:
                    check_list.append((c[0], c[1], c[2]))
            #print('未收到ack名单：check list', check_list)
            # write into offline files
            for c in check_list:
                if not self.check_online(c[0]):
                    self.write_status(c[0], 'offline')
                    offline_list.append((c[0], c[1], c[2]))
            self.broadcast_table()
            for c in offline_list:
                f = self.offlineMsg + '_' + c[0] + '.csv'
                with open(f, 'a') as csvfile:
                    writter = csv.writer(csvfile)
                    writter.writerow(['Channel Message ' + name, t0, msg])

    def listening(self):
        print('server listening')
        while True:
            message, clientAddress = self.socket.recvfrom(2048)
            #print('receive from client:', clientAddress)
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
                #print('收到 ACK CHECK ONLINE, t2 =', t2, 't2-t1 =', t2-float(t1))
                if t1 == self.check_online_ack[1] and t2 - float(t1) < 0.5:
                    self.check_online_ack = (0, 'null')
            elif re.match('CHANNEL MESSAGE FROM ([\w]+) T ([\d.]+) TIME ([\d.]+) MSG (.+)', message, flags=re.DOTALL):
                m = re.match('CHANNEL MESSAGE FROM ([\w]+) T ([\d.]+) TIME ([\d.]+) MSG (.+)', message, flags=re.DOTALL)
                name, t0, t1, msg = m.groups()
                xx = threading.Thread(target=self.channelMsg, args=(name, t0, t1, msg, clientAddress))
                #self.channelMsg(name, t0, t1, msg, clientAddress)
                xx.start()
            elif re.match('ACK FORWARD ([\d.]+) ([\w]+)', message):
                m = re.match('ACK FORWARD ([\d.]+) ([\w]+)', message)
                t2, receiver = m.groups()
                t3 = time.time()
                #print('收到', message, '此时 t3=',t3, 't3-t2=', t3-float(t2))
                if t2 == self.ack_channel_recv[0] and t3 - float(t2) < 0.5:
                    self.ack_channel_recv[1].append(receiver)
            else:
                print('Error: wrong request ' + message)



