from spark.internal.version import *
from com.sri.ai.spark.executor import Executor, XPSExecutor, ExecutionListener
#from spark.internal.parse.basicvalues import set_methods, Symbol, BACKQUOTE_SYMBOL, installConstructor, Value, Variable, value_str, Structure, List, isVariable, isSymbol, isList, isStructure, isString
from spark.internal.parse.basicvalues import Structure, isString, Symbol, isList, isStructure, List
#from spark.io.xps import XPS, mapToSpark, mapFromSpark
from spark.io.xps import mapToSpark, mapFromSpark, toXPS, fromXPS
from spark.internal.parse.usages import ACTION_DO, TERM_EVAL

# _converter = XPS(None,           # nullValue
#                  True,                  # useDouble
#                  False,                 # useLong
#                  True,                  # useBoolean
#                  mapToSpark,            # toSpark
#                  mapFromSpark           # fromSpark
#                  )
# toXPS = _converter.toXps
# fromXPS = _converter.toSpark

from spark.internal.repr.common_symbols import P_Properties
from spark.internal.repr.taskexpr import DoEvent
from spark.internal.common import NEWPM, DEBUG
from spark.lang.builtin import partial
from spark.io.common import sparkNULL, log_incoming_request, log_outgoing_result, log_outgoing_request, log_incoming_result

debug = DEBUG(__name__).on()

PACKAGE = "spark.io.exec"
FAIL_REQUEST = "fail"
S_ExecuteTask = Symbol(PACKAGE + ".ExecuteTask")
S_taskFailed = Symbol(PACKAGE + ".taskFailed")
S_taskSucceeded = Symbol(PACKAGE + ".taskSucceeded")

def keyget(seq, key):
    for elt in seq:
        functor = elt.functor
        if functor is not None and functor.name == key:
            return elt
    return None

def taskNameToSymOrError(agent, taskname):
    propfacts = agent.factslist0(P_Properties)
    facts = [f for f in propfacts if f[0].id == taskname and keyget(f[1], "uri") != None]
    if len(facts) == 0:
        result = "Task %s has not been defined"%taskname
    elif len(facts) > 1:
        result = "Task %s is not uniquely defined"%taskname
    else:
        result = facts[0][0]
    return result
    
def optMode(agent, symbol, usage):
    "Return the mode corresponding to the given usage of the symbol"
    decl = agent.getDecl(symbol)
    return decl and decl.optMode(usage)

def _if(test, trueval, falseval):
    if test:
        return trueval
    else:
        return falseval

class _SparkExecutor(Executor):
    def __init__(self):
        self.agent = None

    def executeTask(self, listener, taskname, taskargs):
        if self.agent == None:
           self.agent = G._AGENT
        staskargs = fromXPS(taskargs)
        log_incoming_request(listener, "executeTask", (listener, taskname, staskargs))
        symOrError = taskNameToSymOrError(self.agent, taskname)
        if isString(symOrError):
            requestType = FAIL_REQUEST
            term = symOrError
        else:
            mode = optMode(self.agent, symOrError, ACTION_DO)
            if mode:
                requestType = "d"
                inargs = [_if(usage == TERM_EVAL, x, None)
                          for (x, usage) in zip(staskargs, mode)]
                debug("inargs = %r", inargs)
                term = Structure(symOrError, List(inargs))
            else:
                requestType = FAIL_REQUEST
                term = "Cannot find argument modes"
        #debug("initiating task via (%s, %r, %r, %r)", S_ExecuteTask.id, requestType, listener, term)
        self.agent.add_ephemeral(S_ExecuteTask, requestType, listener, term)

    def executingTask(self, parentListener, taskname, taskargs):
        requestId = log_incoming_request(None, "executingTask", (parentListener, taskname, fromXPS(taskargs)))
        listener = _SparkExecutionListener(self.agent, parentListener)
        debug("creating listener %s with parent %s", listener, parentListener)
        log_outgoing_result(requestId, "result", listener)
        return listener

XPSExecutor.setSparkExecutor(_SparkExecutor())

def setLoopback():                      # for testing only
    XPSExecutor.setNonsparkExecutor(XPSExecutor.getSparkExecutor())

def startExecuteTask(agent, listener, taskname, arguments):
    if not isinstance(listener, ExecutionListener):
        listener = None
    newlistener = _SparkExecutionListener(agent, listener)
    debug("creating listener %s with parent %s", newlistener, listener)
    executor = XPSExecutor.getNonsparkExecutor()
    if executor == None:
        raise LowError("XPSExecutor nonsparkExecutor is not set")
    larguments = List(arguments)
    log_outgoing_request(newlistener, "executeTask", (newlistener, taskname, larguments))
    executor.executeTask(newlistener, taskname, toXPS(larguments))
    return newlistener

    
def executingTask(parentListener, taskname, arguments):
    executor = XPSExecutor.getNonsparkExecutor()
    larguments = List(arguments)
    requestId = log_outgoing_request(None, "executingTask", (parentListener, taskname, larguments))
    listener = executor.executingTask(parentListener, taskname, toXPS(larguments))
    log_incoming_result(requestId, "result", listener)
    return listener


def callTaskFailed(listener, reason):
    log_outgoing_result(listener, "failure", reason)
    listener.taskFailed(reason)

def callTaskSucceeded(listener, bindings):
    larguments = List(bindings)
    log_outgoing_result(listener, "success", larguments)
    listener.taskSucceeded(toXPS(larguments))


###############

# Record of internal tasks.  These are ones returned from calling the
# PAL/CPOF bridge's executingTask methods

# On executing a CPOF task, we must (1) call the executingTask method for
# every ancestor intermediate task that we haven't already done it
# for and (2) call the listener's method for 

################

class _SparkExecutionListener(ExecutionListener):
    def __init__(self, agent, parent):
        self.agent = agent
        self._parent = parent
        print "Creating "

    def getParent(self):
        return self._parent

    def taskFailed(self, reason):
        log_incoming_result(self, "failure", reason)
        self.agent.add_ephemeral(S_taskFailed, self, reason)

    def taskSucceeded(self, boundParameters):
        result = fromXPS(boundParameters)
        log_incoming_result(self, "success", result)
        self.agent.add_ephemeral(S_taskSucceeded, self, result)


    def __str__(self):
        return "<Listener %s>"%id(self)

################################################################
# Common utilities

from spark.internal.common import SUCCESS
from spark.internal.parse.usagefuns import termMatch
from spark.pylang.implementation import Imp

class NewtryColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        return tframe.tfpost_child(agent, 0)

    def tchild_complete(self, agent, tframe, zexpr, index, result):
        if index == 0:
            if result is SUCCESS:
                return tframe.tfpost_child(agent, 1)
            elif termMatch(agent, tframe.getBaseBindings(), zexpr[2], result):
                return tframe.tfpost_child(agent, 3)
            else:
                raise zexpr.error("Pattern does not match value %s", result)
        else:
            return tframe.tfcompleted(agent, result)

def access(obj, *accessors):
    value = obj
    for accessor in accessors:
        if isList(accessor):
            if len(accessor) == 1:
                value = value[accessor[0]]
            else:
                raise LowError("Invalid accessor: %r", accessor)
        elif isStructure(accessor):
            methodname = accessor.functor.name
            method = getattr(value, methodname, None)
            if method == None:
                raise LowError("Object has no method called %s", methodname)
            value = method(*accessor)
        elif isSymbol(accessor):
            value = getattr(value, accessor.name, None)
        elif isInteger(accessor):
            value = value[accessor]
        else:
            raise LowError("Invalid accessor: %r", accessor)
        if value == None:
            return None
    return value

def mergePartial(p1, p2):
    if len(p1) != len(p2):
        return None
    def merge(x, y):
        if x == None:
            return y
        else:
            return x
    newargs = [merge(e1, e2) for (e1, e2) in zip(p1, p2)]
    if isList(p1):
        return List(newargs)
    elif isStructure(p1):
        return Structure(p1.functor, newargs)
    
        
################################################################

def isLearnedProcedure(agent, tframe):
    "This is a learned procedure that is triggered directly by a learned task, not via doActionSpec"
    event = tframe.event()
    if not isinstance(event, DoEvent):
        return False
    eventSym = event.goalsym()
    # TODO: should factor out the following "look for property"
    propfacts = agent.factslist1(P_Properties, eventSym)
    if propfacts:
        for prop in propfacts[0][1]:
            if isStructure(prop) and prop.functor.id == "uri":
                return True
    return False

def tframeInitialArguments(agent, tframe):
    args = tframe.event().getArgs(agent)
    #debug("initial args: %r %r", tframe, args)
    return args

def tframeFinalArguments(agent, tframe):
    args = tframe.event().getTaskResultArgs(agent)
    #debug("final args: %r %r", tframe, args)
    return args

    

from spark.lang.builtinObjectProperty import getObjectProperty
from spark.lang.meta_aux import procInstSymbol
from spark.internal.repr.taskexpr import GoalEvent

def ancestorListener(agent, tframe):  # returns (ancestor, listener) or None
    event = tframe.event()
    while isinstance(event, GoalEvent):
        tf = event.e_sync_parent()
        listener = getObjectProperty(agent, tf, "listener")
        if listener != None:
            #debug("Found ancestor listener %r", listener)
            return (tf, listener)
        event = tf.event()
    else:
        #debug("No ancestor listener is recorded")
        return None
    
def reportable(agent, tframe):          # returns listener or None
    """If this procedure is a learned one, return the listener for
    reporting its success or failure.
    If an ancestor is being reported, ask the bridge for a new listener.
    If not, use the listener recorded for the objective."""
    if not isLearnedProcedure(agent, tframe):
        debug("no need to report non-learned or top-level procedure %r for event %s", tframe, tframe.event())
        return None
    debug("must report learned procedure %r for event %s", tframe, tframe.event())
    (tf, listener) = ancestorListener(agent, tframe) or (None,None)
    if tf == None:
        return None
    executor = XPSExecutor.getNonsparkExecutor()
    taskname = tframe.event().goalsym().id
    taskargs = tframeInitialArguments(agent, tframe)
    newListener = executingTask(listener, taskname, taskargs)
    debug("obtained listener for %r: %r", tframe, newListener)
    return newListener
