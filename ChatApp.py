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


#prompt = "\n>>> "
datafile = './data'

if argv[1] == '-s':  # 检查参数个数
    #print('server mode!')
    serverPort = argv[2]  # 检查port是否已经占用，以及范围
    if check_port(serverPort):
        if os.path.exists(datafile):
            print('[Warning: old version data files exists.]')
            for f in os.listdir(datafile):
                os.remove(os.path.join(datafile, f))
            print('[Old version data files  removed.]')
        else:
            os.mkdir(datafile)
        #print('server port:', serverPort)
        s = Server(serverPort)
        #print('Server instance made!')
        #x3 = threading.Thread(target=s.listening)
        s.listening()
        #x3.start()


elif argv[1] == '-c':
    #print('client mode!')
    if not os.path.exists(datafile):
        os.mkdir(datafile)
    clientName = argv[2]
    serverIp = argv[3]  # 检查ip地址
    serverPort = argv[4]
    clientPort = argv[5]
    if check_port(clientPort):
        c = Client(clientName, clientPort, serverIp, serverPort)
        c.registration()
        print('>>> [Welcome, you are registered.]', end='\n>>> ')
        # c.listening()
        x1 = threading.Thread(target=c.listening)
        x2 = threading.Thread(target=c.command)
        x1.start()
        x2.start()

else:
    print('Error: enter -s or -c')
