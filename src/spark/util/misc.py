#*****************************************************************************#
#* Copyright (c) 2004-2008, SRI International.                               *#
#* All rights reserved.                                                      *#
#*                                                                           *#
#* Redistribution and use in source and binary forms, with or without        *#
#* modification, are permitted provided that the following conditions are    *#
#* met:                                                                      *#
#*   * Redistributions of source code must retain the above copyright        *#
#*     notice, this list of conditions and the following disclaimer.         *#
#*   * Redistributions in binary form must reproduce the above copyright     *#
#*     notice, this list of conditions and the following disclaimer in the   *#
#*     documentation and/or other materials provided with the distribution.  *#
#*   * Neither the name of SRI International nor the names of its            *#
#*     contributors may be used to endorse or promote products derived from  *#
#*     this software without specific prior written permission.              *#
#*                                                                           *#
#* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS       *#
#* "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT         *#
#* LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR     *#
#* A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT      *#
#* OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,     *#
#* SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT          *#
#* LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,     *#
#* DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY     *#
#* THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT       *#
#* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE     *#
#* OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.      *#
#*****************************************************************************#
#* "$Revision:: 470                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

from __future__ import generators
from spark.internal.version import *
from spark.internal.exception import LowError

from spark.internal.engine import agent as agent_mod
from spark.pylang.implementation import Imp, PredImpInt
from spark.internal.parse.usagefuns import *

import random
import time
import string
import md5
import os.path, os
import zipfile, fnmatch

def executeCommand(comm, params):
    parameters = " ".join(params)
    command = comm + " " + parameters
    if isPython:
        os.system(command)
    else:
        from java.lang import Runtime
        runner = Runtime.getRuntime()
        getattr(runner, "exec")(command) # runner.exec is a Python syntax error
    return True

def calculate_md5(str):
    return md5.new(str).digest()

# for genid
#
# Generate random IDs

class IDGenerator(object):
    __slots__ = (
        "_id",
        "_lock",
        )
    def __init__(self):
        self._id = 0
        import threading
        self._lock = threading.Lock()

    def __call__(self):
        self._lock.acquire()
        newid = self._id + 1
        self._id = newid
        self._lock.release()
        return newid
IDGENERATOR = IDGenerator()

def generate_prefix_id(prefix, id):
    if id == None:
        return generateGeneratedId(prefix)
    else:
        return testGeneratedId(prefix, id)    

def random_prefix_id(prefix, id):
    if id == None:
        return generateRandomId(prefix)
    else:
        return testGeneratedId(prefix, id)    

def testGeneratedId(prefix, id):
    if not id.startswith(prefix):
        return None
    for index in range(len(prefix), len(id)):
        if id[index] not in "0123456789":
            return None
    return True

def generateGeneratedId(prefix):
    firstId = prefix + str(IDGENERATOR())
    yield firstId
    raise LowError("You must not find more than one solution to GeneratedId")

def generateRandomId(prefix):
    firstId = prefix + str(random.randint(0,1000000000))
    yield firstId
    raise LowError("You must not find more than one solution to RandomId")
    
# createInstanceOf
#
# Given a type, returns a name to be used as an instance reference.
# Not perfect, but it should work for now.
def createInstanceOf(obj):
    t = int(time.time())
    r = random.randint(0, 100)
    name = "%s%s%02d" % (obj, t, r)
#    print "instance: %s" % (name)
    return name

def getMachineName():
    if isPython:
        from platform import uname
        return uname()[1]
    elif isJython:
        from java.net import InetAddress
        addr = InetAddress.getLocalHost()
        return str(addr.getHostName())
    return False

def getSparkHomeDirectory():
    """Retrieve the root of the SPARK release.
    """
    import spark
    from os.path import dirname, split
    root, subdir = split(dirname(spark.__path__[0]))
    if subdir == "Lib":           # SPARK source mixed with jython Lib
        root = dirname(root)
    elif subdir != "src":
        print "Uncertain of SPARK home directory. Using", root
    return root

def getSetIdleWaitTime(x):
    import spark.internal.engine.agent
    spark.internal.engine.agent

def startFile(filename):
    from java.awt import Desktop
    from java.io import File
    d = Desktop.getDesktop()
    d.open(File(filename))
    return True

def openBrowser(url):
    from java.awt import Desktop
    from java.net import URI
    d = Desktop.getDesktop()
    d.browse(URI(url))
    return True

class IdleWaitTime(Imp, PredImpInt):
    __slots__ = ()

    def solution(self, agent, bindings, zexpr):
        if len(zexpr) != 1:
            raise zexpr.error("Exactly one argument required")
        if termMatch(agent, bindings, zexpr[0], agent_mod.IDLE_WAIT_TIME):
            return SOLVED
        else:
            return NOT_SOLVED

    def conclude(self, agent, bindings, zexpr):
        if len(zexpr) != 1:
            raise zexpr.error("Exactly one argument required")
        agent_mod.IDLE_WAIT_TIME = termEval(agent, bindings, zexpr[0])

def getSvnVersion():
    import re
    filein, fileout = os.popen4("svnversion")
    rev = fileout.read()
    rev = re.sub("\n", "", rev)
    if re.match("[0-9]+", rev) == None:
        print "Subversion revision number could not be obtained"
        return None
    else:
        print "Current Subversion revision: " + rev   
    return rev

def getFileVersion(module):
    import sys, re
    
    #unless found otherwise, assume path is absolute
    filepath = module
    
    #find file in existing paths, if possible
    for path in sys.path:
        sep = "\\"+os.sep
    
        if os.path.isdir(path):
            curPath = os.path.join(path, module)  
            modulePath = re.sub("\.", sep, module)
            modulePath = os.path.join(os.path.abspath(path), \
                                      modulePath+".spark")
            #check absolute path format    
            if os.path.isfile(curPath):
                filepath = curPath
                break
            #check module path format
            elif os.path.isfile(modulePath):
                filepath = modulePath
                break
    
    #read the revision number
    try: 
        FILE = open(filepath, "r")
        raw = FILE.read()
        #stop if file is empty
        if re.match("^(\s)*$", raw):
            print filepath, " is empty."
            return None
        
        lines = re.split(r'[\n|\r]+', raw)
        for line in lines:
            if re.search('\$Revision:', line):
                result = re.search("[0-9]+", line).group(0)
                print module, ": ", result
                return result
        print module, ":  no rev. number"
    except:
        print "could not open file ", filepath
    return None

def getUserHomeDir():
    return os.path.expanduser("~")

def addToZip(zippedHelp, directory, unwanted):
    list = os.listdir(directory)
    for u in unwanted:
        uw = fnmatch.filter(list, u)
        list = filter(lambda x: x not in uw, list)
    for entity in list:
        each = os.path.join(directory,entity)
        if os.path.isfile(each):
            zippedHelp.write(each)
        else:
            addToZip(zippedHelp, each, unwanted)
  
def toZip(zip_file, directory, unwanted):
    zippedHelp = zipfile.ZipFile(zip_file, "w")
    u = unwanted.split(",")
    s = [x.strip() for x in u]
    addToZip(zippedHelp, directory, s)
    zippedHelp.close()

