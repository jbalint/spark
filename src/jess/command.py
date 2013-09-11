import os
from subprocess import *

FNULL = open(os.devnull, 'w')

def run_command_get_output(cmd):
    # naive tokenization of strings
    if isinstance(cmd, str):
        cmd = cmd.split(" ")

    proc = Popen(cmd, stdout=PIPE, stderr=FNULL)
    output = ""
    while True:
        line = proc.stdout.readline()
        if line == '':
            break
        else:
            output += line
    return output.rstrip()
