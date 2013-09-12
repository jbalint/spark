# Copyright 2013 Jess Balint

import socket
import select

from threading import Thread

from spark.internal.debug.interpreter import *

serverSocket = None
clientSockets = []

runAgent = None

def start_server_thread(runAgent_):
    global runAgent
    global serverSocket

    runAgent = runAgent_
    print "STARTING TCP SERVER, agent = ", runAgent
    serverSocket = open_listener_socket()
    t = Thread(target=lambda: process_commands())
    t.setDaemon(True)
    t.start()

def process_commands():
    while True:
        next = get_next_socket_command(serverSocket, clientSockets)
        for c in next.split("\n"):
            process_command(runAgent, c)

def open_listener_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 9002))
    s.setblocking(0) # necessary for Jython....
    #https://wiki.python.org/jython/SelectModule
    s.listen(1)
    return s

def get_next_socket_command(serverSocket, clientSockets):
    # can't select on stdin in Jython
    # https://wiki.python.org/jython/SelectModule
    #fds = select.select([serverSocket, sys.stdin] + clientSockets, (), ())
    (readfds, writefds, excfds) = select.select([serverSocket] + clientSockets, (), ())
    for fd in readfds:
        if fd == serverSocket:
            client, addr = serverSocket.accept()
            print '\nConnection from ', addr
            clientSockets.append(client)
            client.setblocking(0) # necessary for Jython....
            next = ''
        else: # read from client socket
            next = fd.recv(4096)
            print "Command from client (", fd.getpeername(), "): ", next
            if not next or next.strip() == "disconnect":
                print "Disconnecting ", fd.getpeername()
                clientSockets.remove(fd)
                fd.close()
    return next
