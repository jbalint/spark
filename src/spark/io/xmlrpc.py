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
#* "$Revision:: 459                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

"""
XML-RPC interface for SPARK.

Allows SPARK to make XML-RPC requests and to prove an XML-RPC server.
"""

from spark.internal.version import *
from spark.internal.common import DEBUG, NEWPM
from spark.io.common import agentServices, postRequest, sparkNULL, log_outgoing_result, log_outgoing_request, log_incoming_result, initiate_request, getDropBox
from spark.internal.parse.basicvalues import Symbol, Structure, Variable, Boolean, List
from spark.internal.parse.basicvalues import isStructure, isList, isNumber, isBoolean, isString, isVariable, isSymbol
from spark.internal.exception import RuntimeException, LowError
import thread
import socket
import types
debug = DEBUG(__name__).on()


from xmlrpclib import ServerProxy, Fault, METHOD_NOT_FOUND, INTERNAL_ERROR, ProtocolError, TRANSPORT_ERROR
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SocketServer import ThreadingMixIn

################################################################
PACKAGE = "spark.io.xmlrpc"
S_XMLRPC = Symbol(PACKAGE + ".XMLRPC")
# S_requestCallback = Symbol(PACKAGE + ".requestCallback")
################################################################


# IMPLEMENTS NON-PERSISTABLE SERVERS

class MyServer(ThreadingMixIn, SimpleXMLRPCServer):
    __slots__ = ["agent",
                 ]
    
    def __init__(self, agent, port):
        self.agent = agent
        SimpleXMLRPCServer.__init__(self, ("127.0.0.1", port))
        
    def _dispatch(self, method, params):
        debug("incoming request method %r args %r", method, params)
        try:
            debug("Decoding parameters %r", params)
            decoded = decodeXMLValue(params)
            debug("Decoded parameters %r", decoded)
            (errnum, rid) = initiate_request(self.agent, S_XMLRPC, 0, method, decoded)
        except AnyException, e:
            errid = NEWPM.displayError()
            raise Fault(INTERNAL_ERROR, "Error [%s] %s"%(errid, e))
        if errnum != 0:
            raise Fault(errnum, encodeXMLValue(rid))
        dropBox = getDropBox(rid)
        dropBox.waitDone()
        (errnum1, result) = dropBox.getErrnumResult()
        if errnum1 != 0:
            raise Fault(errnum1, encodeXMLValue(result))
        else:
            return encodeXMLValue(result)

    def _listMethods(self):
        # TODO: check this is correct
        return [fact[0] for fact in self.agent.factslist0(S_XMLRPCService)]

    def _methodHelp(self, method):
        return "No help for this method"
    def __getattr__(self, name):
        #print "Accessing MyServer attribute", name
        raise AttributeError(name)


_SERVER = None

def startXMLRPCServer(agent, params):
    """Start up an XML-RPC server on the localhost.
    params is a list [portnum].
    Raises an exception if agent already has a server started or if
    it cannot use that port.
    """
    if not isList(params) or len(params) != 1:
        raise LowError("The parameters to startXMLServer must be of the form [$portnum]")
    port = params[0]
    global _SERVER
    if _SERVER:
        raise RuntimeException("Agent already has an XML-RPC server set up")
    try:
        server = MyServer(agent, port)
    except socket.error, e:
        # TODO: handle error properly, check the code and give a proper message
        raise RuntimeException("Error opening socket")
    server.register_introspection_functions()
    _SERVER = server
    thread.start_new_thread(server.serve_forever, ())
    return True

def stopXMLRPCServer(agent):
    """Stops the XML-RPC server running for the given agent.
    Raises an exception if there is no server running.
    """
    global _SERVER
    if _SERVER == None:
        raise RuntimeException("Agent has no XML-RPC server running to stop")
    _SERVER.server_close()
    _SERVER = None
    return True

################################################################

def requestXMLRPC(agent, uri, name, parameters):
    import xmlrpclib
    debug("outgoing request %r %r %r", uri, name, parameters)
    try:
        requestId = log_outgoing_request(None, name, parameters)
        proxy = xmlrpclib.ServerProxy(uri, allow_none=True, verbose=True)
        origresult = getattr(proxy, name)(*encodeXMLValues(parameters))
        #print "xml-rpc", result
        result = decodeXMLValue(origresult)
        debug("incoming result %r", result)
        errnum = 0
    except IOError, e:
        debug("error creating proxy: %r", e)
        errnum, result = TRANSPORT_ERROR, "IOError for uri %r: %s"%(uri, e.strerror or e.message)
    except Fault, e:
        debug("incoming fault %r %r", e.faultCode, e.faultString)
        errnum, result =  e.faultCode, e.faultString
    except ProtocolError, e:
        debug("outgoing request protocol error %r %r", e.errcode, e.errmsg)
        errnum, result = e.errcode, e.errmsg
    except socket.timeout, e:
        debug("outgoing request timeout")
        errnum, result = TRANSPORT_ERROR, "timed out"
    except socket.error, e:
        debug("outgoing request socket error")
        from errno import errorcode
        #errno = e[0]
        errmsg = e[1]
        errnum, result = TRANSPORT_ERROR, str(errmsg)
    log_incoming_result(requestId, errnum, result)
    return errnum, result
################################################################

FUNCTOR = "functor"
ARGS = "args"
SYM = "sym"
VAR = "var"

UNCHANGED_TYPES = (types.IntType, types.LongType, types.FloatType, basestring, types.BooleanType)


def encodeXMLValue(sparkValue):
    "Converts a SPARK value to a python value that can be passed by XML"
    if isinstance(sparkValue, UNCHANGED_TYPES):
        return sparkValue
    if sparkValue == sparkNULL():
        return None
    elif isStructure(sparkValue):
        d = mapDict(sparkValue, encodeXMLValue)
        if d != None:
            return d
        else:
            # Use FUNCTOR/ARGS notation
            return {FUNCTOR:sparkValue.functor.name,
                    ARGS:encodeXMLValues(sparkValue)}
    elif isList(sparkValue):
        return encodeXMLValues(sparkValue)
    elif isSymbol(sparkValue):
        return {SYM:sparkValue.name}
    elif isVariable(sparkValue):
        return {VAR:sparkValue.name}
    else:
        raise LowError("Cannot convert python type %r to XML"%sparkValue.__class__)
def encodeXMLValues(seq):
    return [encodeXMLValue(x) for x in seq]

def decodeXMLValue(xmlValue):
    "Converts a python value returned by xmlrpc to a SPARK value"
    if isinstance(xmlValue, UNCHANGED_TYPES):
        return xmlValue
    elif xmlValue == None:
        return sparkNULL()
    elif isinstance(xmlValue, types.DictType):
        functor = xmlValue.get(FUNCTOR)
        if functor is not None:
            args = xmlValue.get(ARGS)
            if args is None:
                raise LowError("Missing %r element for structure"%ARGS)
            return Structure(Symbol(functor), decodeXMLValues(args))
        sym = xmlValue.get(SYM)
        if sym is not None:
            return Symbol(sym)
        var = xmlValue.get(VAR)
        if var is not None:
            return Variable(var)
        # default
        return dictMap(xmlValue, decodeXMLValue)
    elif isinstance(xmlValue, types.ListType):
        return decodeXMLValues(xmlValue)
    elif isinstance(xmlValue, types.TupleType):
        return decodeXMLValues(xmlValue)
    else:
        raise LowError("Cannot convert value of type %r from XML"%xmlValue.__class__)

def decodeXMLValues(seq):
    return List([decodeXMLValue(x) for x in seq])

################################################################
# Routines for accessing fields of a map structure.

# These used to be defined here but have now moved to spark.lang.map
# They should be imported from there not here
from spark.lang.map import isMap, mapChange, mapGetPred, mapGet, mapDict, mapKeys, dictMap, mapCreate

################################################################
