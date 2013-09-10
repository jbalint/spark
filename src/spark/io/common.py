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
#* "$Revision:: 422                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.version import *
from spark.internal.parse.basicvalues import Symbol, Structure, EMPTY_SPARK_LIST, isList, isString, List, isStructure, value_str
from spark.internal.common import DEBUG
import thread
import time

# The following enables this file to work with older versions of SPARK
try:
    from spark.lang.builtin import sparkNULL
except:
    def sparkNULL():
        return Symbol("utilities.rdf.NULL")

debug = DEBUG(__name__)#.on()
commsDebug = DEBUG("****").on()
PACKAGE = "spark.io.common"
S_ProvideService = Symbol(PACKAGE + ".ProvideService")
S_Request = Symbol(PACKAGE + ".Request")
S_standardCallback = Symbol(PACKAGE + ".standardCallback")

#S_NULL = Symbol(PACKAGE + ".NULL")


def agentServices(agent, mechanism, name=None):
    debug("Calling agentServices(%r, %r, %r)", agent, mechanism, name)
    def _appropriate(fact):
        m = fact[3]
        return m == EMPTY_SPARK_LIST \
               or m == mechanism \
               or (isList(mechanism) and m in mechanism)
    if name is None:
        rawfacts = agent.factslist0(S_ProvideService)
    else:
        rawfacts = agent.factslist1(S_ProvideService, name)
    facts = [fact for fact in  rawfacts if _appropriate(fact)]
    debug("agentServices(agent, %r, %r)->%r", mechanism, name, facts)
    return facts
    
def postRequest(agent, requestType, requestId, partial, callback):
    debug("posting (Request %r %r %r %r)", requestType, requestId, partial, callback)
    agent.add_ephemeral(S_Request, requestType, requestId, partial, callback)

################################################################
# DropBox holds results of execution

ID_MAP = {}                             # dict mapping id to DropBox
NEXT_ID = 0
LOCK = thread.allocate_lock()

def allocateId():
    LOCK.acquire()
    global NEXT_ID
    request_id = NEXT_ID
    NEXT_ID = request_id + 1
    LOCK.release()
    return request_id

def allocateDropBox(info=None):
    request_id = allocateId()
    dropBox = _DropBox(request_id, info)
    ID_MAP[request_id] = dropBox
    return request_id

def getDropBox(request_id):
    return ID_MAP.get(request_id)

class _DropBox(object):
    __slots__ = ("_request_id",
                 "_info",
                 "_lock",
                 "_errnum",
                 "_result",
                 )
    def __init__(self, request_id, info):
        debug("creating dropbox %s", request_id)
        self._request_id = request_id
        self._info = info
        self._lock = thread.allocate_lock()
        self._lock.acquire()
        self._errnum = None
        self._result = None

    def isDone(self):
        return not self._lock.locked()

    def waitDone(self, secondsTimeout=None):
        """Wait at most the given number of seconds (or forever if None) for a
        result. Return whether there is a result."""
        debug("entering dropbox.waitDone(%r)", secondsTimeout)
        lock = self._lock
        if not lock.locked():
            debug("dropbox lock has been released")
            return True
        if secondsTimeout is None:
            debug("acquiring dropbox lock")
            lock.acquire()
            lock.release()
            debug("dropbox lock acquired")
            return True
        if secondsTimeout <= 0:
            return False
        now = time.time()
        end = now + secondsTimeout
        interval = 0.1
        while True:
            if not lock.locked():
                debug("dropbox lock has been released")
                return True
            if now >= end:
                debug("dropbox.waitFor timeout")
                return False
            sleepTime = min(1.0, interval, (end - now))
            debug("dropbox.waitDone sleeping for %s seconds", sleepTime)
            time.sleep(sleepTime)
            interval *= 2
            now = time.time()

    def getInfo(self):
        return self._info

    def peekErrnum(self):
        return self._errnum

    def peekResult(self):
        return self._result

    def getErrnumResult(self):
        "Get (errnum,result) pair or None if not done. If done also remove from ID_MAP"
        if self._lock.locked():
            return None
        else:
            try:
                del ID_MAP[self._request_id]
            except KeyError:
                pass
            return self._errnum, self._result

    def setErrnumResult(self, errnum, result):
        if not self._lock.locked():
            raise Exception("Errnum and result are already set")
        self._errnum = errnum
        self._result = result
        self._lock.release()

################################################################
# Initiate a request

NO_ERROR = 0
ERR_METHOD_NOT_FOUND = -1
ERR_TRANSLATION = -2
ERR_SERVER_NOT_AVAILABLE = -3
ERR_EXECUTION = -4
ERR_CANCELLED = -5
ERR_SERVER_ERROR = -6

def initiate_request(agent, service_sym, info, method, args):
    """Initiate an asynchronous request
        service_sym is the 'mechanism' symbol
        info is arbitrary information to associate with the request
        method is the service name
        args specifies the service arguments
        returns (0, request_id) if initiation went well
        returns (errnum, error_message_string) otherwise
        """
    
    facts = agentServices(agent, service_sym, method)
    if len(facts) == 0:
        errnum = ERR_METHOD_NOT_FOUND
        result = "Method %r hasn't been defined for %s"%(method, service_sym.id)
    elif len(facts) > 1:
        errnum = ERR_METHOD_NOT_FOUND
        result = "Method %r is not uniquely defined for %s"%(method, service_sym.id)
    else:
        _method, sym, requestType, _mechanism = facts[0]
        if requestType not in ("d", "d1", "db", "d0", "s"):
            errnum = ERR_SERVER_ERROR
            result = "Method maps to an invalid request type: %s"%(requestType,)
        else:
            requestId = allocateDropBox(info)
            log_incoming_request(requestId, method, args)
            postRequest(agent, requestType, requestId,
                        Structure(sym, args), S_standardCallback)
            return 0, requestId
    requestId = log_incoming_request(None, method, args)
    log_outgoing_result(requestId, errnum, result)
    return (errnum, result)

def standardCallback(agent, requestType, request_id, errnum, result):
    "Standard callback posts result in dropbox"
    log_outgoing_result(request_id, errnum, result)
    getDropBox(request_id).setErrnumResult(errnum, result)

################################################################
# functions to log incoming and outgoing requests
def log_incoming_request(requestId, method, args):
    if requestId is None:
        requestId = allocateId()
    commsDebug("Incoming request %s %s %s", (requestId), value_str(method), value_str(args))
    return requestId

def log_outgoing_result(requestId, errnum, result):
    commsDebug("Outgoing result %s %s %s", (requestId), value_str(errnum), value_str(result))

def log_outgoing_request(requestId, method, args):
    if requestId is None:
        requestId = allocateId()
    commsDebug("Outgoing request %s %s %s", (requestId), value_str(method), value_str(args))
    return requestId

def log_incoming_result(requestId, errnum, result):
    commsDebug("Incoming result %s %s %s", (requestId), value_str(errnum), value_str(result))

    

    
################################################################
