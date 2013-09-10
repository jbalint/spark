"""
Module containing functions for translating between ordinary Java
representations of JSON-like objects and SPARK objects.
Java/Jython <-> SPARK/Jython
null/None <-> SPARK NULL value
String/basestring <-> String/basestring
Integer/int <-> Integer/int
Double/float <-> Float/float
List<Object> <-> List/tuple
Map<String,Object> <-> Structure or Symbol or Variable

"""
from com.sri.ai.spark.runtime import XPS
from spark.lang.map import dictMap, mapDict
from java.util.concurrent import ExecutionException, CancellationException
from java.lang import InterruptedException
from com.sri.ai.spark.executor import Solver, XPSSolver
from java.util.concurrent import Future

from spark.internal.parse.basicvalues import Symbol
from spark.io.common import initiate_request, getDropBox, NO_ERROR, ERR_EXECUTION, ERR_CANCELLED, ERR_SERVER_NOT_AVAILABLE, sparkNULL, log_outgoing_request, log_incoming_result


# The following do not handle Symbols, Variables, mixed Structures, or Others

def mapToSpark(**keyargs):
    "Given a set of keyword parameters representing a map, return the SPARK map object"
    return dictMap(keyargs)

def mapFromSpark(obj):
    "Given a SPARK map, return the correponding Python dict (or None if not a map)"
    try:
        return mapDict(obj)
    except:
        return None

_converter = XPS(sparkNULL(),           # nullValue
                 True,                  # useDouble
                 False,                 # useLong
                 True,                  # useBoolean
                 mapToSpark,            # toSpark
                 mapFromSpark           # fromSpark
                 )

toXPS = _converter.toXps
fromXPS = _converter.toSpark



S_XPS = Symbol("spark.io.xps.XPS")

def startXPSServer(agent):
    XPSSolver.setSparkSolver(SPARKSolver(agent))

def stopXPSServer(agent):
    XPSSolver.setSparkSolver(None)

def requestXPS(name, parameters):
    remote = XPSSolver.getNonsparkSolver()
    requestId = log_outgoing_request(None, name, parameters)
    if remote is None:
        errnum = ERR_SERVER_NOT_AVAILABLE
        result = "Remote XPS server is not available"
        log_incoming_result(requestId, errnum, result)
        return errnum, result
    f = remote.solveList(name, toXPS(parameters))
    try:
        objresult = f.get()
        result = fromXPS(objresult)
        errnum = NO_ERROR
    except ExecutionException, e:
        errnum = ERR_EXECUTION
        result = e.getMessage()
    except CancellationException, e:
        errnum = ERR_CANCELLED
        result = e.getMessage()
    log_incoming_result(requestId, errnum, result)
    return errnum, result
        
    
class SPARKSolver(Solver):
    __slots__ = (
        "agent",
        )

    def __init__(self, agent):
        self.agent = agent

    def solve(self, method, args):
        return self.do(method, fromXPS(args))

    def solveList(self, method, args):
        return self.do(method, fromXPS(args))

    def do(self, method, args):
        (errnum, rid) = initiate_request(self.agent, S_XPS, None, method, args)
        if errnum != 0:
            return FailedFuture(rid)
        return ResultFuture(getDropBox(rid))

class FailedFuture(Future):
    __slots__ = ("reason",
                 )
    def __init__(self, reason):
        self.reason = reason

    def cancel(self, ignore):
        return False

    def get(self, *args):
        raise ExecutionException(str(self.reason), None)

    def isDone(self):
        return True

    def isCancelled(self):
        return False


class ResultFuture(Future):
    __slots__ = ("dropBox",
                 )

    def __init__(self, dropBox):
        self.dropBox = dropBox

    def cancel(self, ignore):
        return False

    def get(self, *args):
        dropBox = self.dropBox
        if args == ():
            done = dropBox.waitDone(None) # wait forever
        else:
            timeout, unit = args
            secs = unit.toSeconds(1000000000) * 1e-9 * timeout
            done = dropBox.waitDone(secs)
        if not done:
            raise TimeoutException()
        errnum, result = dropBox.getErrnumResult()
        if errnum == 0:
            return toXPS(result)
        else:
            raise ExecutionException(result, None)

    def isDone(self):
        return self.dropBox.isDone()

    def isCancelled(self):
        return False
    
        
