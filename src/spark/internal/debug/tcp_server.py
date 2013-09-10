# Copyright 2013 Jess Balint

import socket

def open_listener_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 9002))
    s.setblocking(0) # necessary for Jython....
    #https://wiki.python.org/jython/SelectModule
    s.listen(1)
    return s

