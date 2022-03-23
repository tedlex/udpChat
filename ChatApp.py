from socket import *
from sys import argv
import os
import csv
import threading
import re
import time
import datetime
from Server import Server
from Client import Client


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
