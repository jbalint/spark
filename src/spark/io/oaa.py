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
#* "$Revision:: 131                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

import types
import threading, os.path
#from weakref import WeakKeyDictionary, WeakValueDictionary
from spark.internal.version import *

from spark.internal.exception import Failure, TestFailure, RuntimeException, InternalException, LowError
#XXX TODO: module_symbols DNE
from spark.pylang.implementation import PredImpInt, ActImpInt
from spark.pylang.defaultimp import Structure, isStructure, SparkEvent, ObjectiveEvent

from spark.internal.common import re_raise, NEWPM, DEBUG, SOLVED
from spark.internal.engine.agent import External
from spark.internal.parse.basicvalues import set_methods, Symbol, isSymbol, BACKQUOTE_SYMBOL, installConstructor, Value, Variable, isVariable, value_str, append_value_str, Structure, isStructure, List
#from spark.internal.repr.patexpr import ListPatExpr, NonAnonVarPatExpr, ConstantPatExpr
from spark.internal.repr.taskexpr import SUCCESS, GoalPostedEvent, GoalSucceededEvent, GoalFailedEvent, DoEvent, AchieveEvent
from spark.internal.parse.processing import StandardExprBindings
from spark.internal.parse.usagefuns import *
from spark.internal.parse.usages import *
from spark.internal.parse.expr import EXPR_CONSTRUCTOR
from spark.util.logger import *
from spark.util.misc import getSparkHomeDirectory

#Testing Script. Begin:
#from spark.internal.debug.chronometer import chronometer, chronometers, print_chronometers, reset_chronometers
#chronometers["oaaPSolve"] = chronometer("oaaPSolve")
#Testing Script. End.

debug = DEBUG(__name__)#.on()
# def debug(format, *args):
#       import time
#       #time.sleep(1)
#       #print "DEBUG", format, args
#       print "DEBUG-", format%args
        
imported = False

javaOaaManager = None #java oaa provider for java-based OAA interactions

try:
    from java.util import ArrayList, HashMap
    from java.io import FileInputStream
    from java.lang import String
except ImportError:
    print "WARNING: Cannot access java.util - OAA interface will not work"
    def ArrayList(n):
        print "WARNING: ATTEMPTING TO CALL java.util.ArrayList WITHIN PYTHON"
        return [None]*n

try:
    from com.sri.oaa2.icl import IclInt, IclFloat, IclStr, IclVar, IclStruct, IclList, IclTerm, IclDataQ, Unifier

    from com.sri.oaa2.lib import OAAEventListener, LibOaa
    from com.sri.oaa2.com import LibCom, LibComTcpProtocol
    EMPTY_ICL_LIST = IclList()
    UNIFIER = Unifier.getInstance()
    # Tell SPARK how to print IclTerms readably
    imported = True
    # Removing "stdout" from the root logger:
    from org.apache.log4j import LogManager
    LogManager.getRootLogger().removeAppender("stdout")
except ImportError:
    print "WARNING: Cannot access OAA or log4j Java packages - OAA interface will not work"

		
if not imported:
    class OAAEventListener: pass
else:
	#setup the java-based OAA manager
	try:
		from com.sri.ai.spark.oaa import OAAManager
		javaOaaManager = OAAManager
	except ImportError:
		javaOaaManager = None


class InvalidICLError(RuntimeException):
    """An ICL term received was not able to be translated to a SPARK value"""

class InvalidTermError(RuntimeException):
    """A SPARK value was not able to be converted to an ICL term"""
    

################################################################
# Common to OAA calling SPARK and SPARK calling OAA

def iclVarName(x):
    return str(x)                # .name and .getName() are protected!

def oaavar(x):
    return Variable("$%s"%(x,))

OAAVar = Variable
# class OAAVar(Value):
#     __slots__ = ("name",)
#     def __init__(self, name):
#         self.name = name
#         if self.name[:1] not in "_ABCDEFGHIJKLMNOPQRSTUVWXYZ":
#             self.name = "__" + self.name
#     def __eq__(self, other):
#         return isinstance(other, OAAVar) and self.name == other.name
#     def _ne_(self, other):
#         return not self._eq_(other)
#     def __hash__(self):
#         return hash(self.name)
#     def inverse_eval(self):
#         return SYM_applyfun.structure(QUOTED_OAAVAR, self.name)
#     def value_str(self):
#         return ","+self.inverse_eval().value_str()
    
def string_to_icl(string):
    "Generate an IclTerm from a string"
    return IclTerm.fromString(True, string)
    
def icl_string(icl, string):
    "Convert an IclTerm to a string or vice versa."
    if icl == None:
        if string == None:
            raise LowError("At least one argument needs to be bound")
        else:
            return (IclTerm.fromString(True, string), string)
    else:
        if string == None:
            return (icl, str(icl))
        else:
            if str(icl) == string:
                return (icl, string)
            else:
                return None
            

SYM_generateIclTerm = Symbol("spark.io.oaa.generateIclTerm")
SYM_applyfun = Symbol("applyfun")
QUOTED_GENERATEICLTERM = BACKQUOTE_SYMBOL.structure(SYM_generateIclTerm)
SYM_oaavar = Symbol("spark.io.oaa.oaavar")
QUOTED_OAAVAR = BACKQUOTE_SYMBOL.structure(SYM_oaavar)

def icl_inverse_eval(icl):
    string = icl_string(icl, None)[1]
    return SYM_applyfun.structure(QUOTED_GENERATEICLTERM, string)
def icl_append_value_str(icl, buf):
    buf.append(",")
    return append_value_str(icl_inverse_eval(icl), buf)

if imported:
    set_methods(IclTerm, append_value_str=icl_append_value_str, inverse_eval=icl_inverse_eval)

ATOM_FUNCTOR = "@"
NULLARY_FUNCTOR = "@@"
REF_FUNCTOR = "#"
SPECIAL_FUNCTORS = (ATOM_FUNCTOR, NULLARY_FUNCTOR, REF_FUNCTOR)

# currentid = 0
# objectIdMap = WeakKeyDictionary()
# idObjectMap = WeakValueDictionary()
# def getId(object):
#     "Returns an id that can be used to retrieve the object"
#     id = objectIdMap.get(object, None)
#     if id is None:
#         id = currentid
#         currentid = currentid + 1
#         objectIdMap[object] = id
#         idObjectMap[id] = object
#     return id

# def getObject(id):
#     "Retrieve an object given its id"
#     return idObjectMap.get(id, None)

def getFunctor(icl):
    "Workaround for OAA Java API that doesn't unquote functors"
    functor = icl.getFunctor()
    if functor.startswith("'"):
        return functor[1:-1].replace("''", "'")
    else:
        return functor

def getId(object):
    return id(object)

def getObject(id):
    return None

def icl_value(icl, value):
    "Convert an icl to a spark value and vice versa"
    if icl == None:
        if value == None:
            raise LowError("At least one argument needs to be bound")
        else:
            return (value_to_icl(value), value)
    else:
        v = icl_to_value(icl)
        if value == None:
            return (icl, v)
        else:
            if v == value:
                return (icl, value)
            else:
                return None 

def icl_to_value(icl):
    "Map an ICL object to a value"
    if icl.isVar():
        return Variable(ICL_CONSTRUCTOR.asString(icl))
#         name = iclVarName(icl)
#         if name.startswith('_'):
#             return OAAVar('$' + name[1:])
#         else:
#             return OAAVar('$' + name)
    elif icl.isInt():
        i = icl.toLong()
        try:
            return int(i)
        except:
            return i
    elif icl.isList():
        list = []
        for elt in icl.listIterator():
            list.append(icl_to_value(elt))
        return tuple(list)
    elif icl.isStruct():
        functor = getFunctor(icl)
        args = [icl_to_value(x) for x in icl.iterator()]
        if functor in SPECIAL_FUNCTORS:
            if len(args) == 1:
                arg = args[0]
                if functor is REF_FUNCTOR:
                    if isinstance(arg, types.IntegerType):
                        obj = getObject(arg)
                        if obj is not None:
                            return obj
                        else:
                            err = "Referenced object no longer exists: %r"
                    else:
                        err = "Reference functor must take an integer argument: %r"
                elif isinstance(arg, basestring):
                    if functor == ATOM_FUNCTOR:
                        return Symbol(arg)
                    else:
                        return Symbol(arg).structure()
                else:
                    err = "Special functor must take a string argument: %r"
            else:
                err = "Special functor must take exactly one argument: %r"
        else:
            return Structure(Symbol(functor), args)
    elif icl.isStr():
        return icl.toUnquotedString()
    elif icl.isFloat():
        return icl.toFloat()
#     elif icl.isIclDataQ():
#         return icl
    elif icl.isIclDataQ(): # converting IclDataQ to string
        return str(String(icl.getData()))
    else:
        err = "Unknown ICL type: %r"
    raise InvalidICLError(err%icl)

from java.lang import String
def value_to_icl(x): # DOESN'T HANDLE INFINITE STRUCTURES WELL
    "Map a value to an ICL object"
    if isinstance(x, types.IntType):
        return IclInt(x)
    elif isinstance(x, types.LongType):
        return IclInt(x)
    elif isinstance(x, types.FloatType):
        return IclFloat(x)
    elif isinstance(x, basestring):
        try:
            return IclStr(str(x))
        except: #OAA has a hard-limit on string length
            return IclDataQ(String(str(x)).getBytes())
    elif isinstance(x, types.TupleType):
        al = ArrayList(len(x))
        for elt in x:
            al.add(value_to_icl(elt))
        return IclList(al)
    elif isStructure(x):
        s = x.functor.name
        nargs = len(x)
        if nargs == 0:                  # treat as '@@'("absname")
            args = (s,)
            s = NULLARY_FUNCTOR
        else:
            args = x
        al = ArrayList(nargs)
        for elt in args:
            al.add(value_to_icl(elt))
        return IclStruct(s, al)
    elif isinstance(x, IclTerm):
        return x
    elif isVariable(x) and x.isLocal():
        return ICL_CONSTRUCTOR.createVariable(-1, -1, x.name)
#         name = x.name
#         if name[1] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
#             return IclVar(name[1:])
#         else:
#             return IclVar("_"+name[1:])
    elif isSymbol(x):    # treat as '@'("absname")
        al = ArrayList(1)
        al.add(IclStr(x.name))
        return IclStruct(ATOM_FUNCTOR, al)
    elif x is None:                     # treat as '#'(0)
        al = ArrayList(1)
        al.add(IclInt(0))
        return IclStruct(REF_FUNCTOR, al)
    elif hasattr(x, "coerceToSPARKForOAA"):
        return value_to_icl(x.coerceToSPARKForOAA())
    else:                               # treat as '#'(<id>)
        id = getId(x)
        print "Unusual object type=%s id=%s being passed to OAA: %r" \
              % (type(x), id, x)
        al = ArrayList(1)
        al.add(IclInt(id))
        return IclStruct(REF_FUNCTOR, al)

BACKQUOTE_FULL_NAME_SYMBOL = Symbol('spark.lang.builtin.`#')

def iterator_to_zexpr(iterator):
    from spark.internal.parse.expr import ExprVariable, ExprList, ExprStructure, ExprSimple
    args = []
    for icl in iterator:
        expr = EXPR_CONSTRUCTOR.coerce(ICL_CONSTRUCTOR, icl)
        if isinstance(expr, ExprVariable):
            expr.usage = TERM_MATCH
            #args.append(NonAnonVarPatExpr(None, iclVarName(icl)))
        elif isinstance(expr, ExprSimple):
            expr.usage = TERM_EVAL
        else: # else it needs quoting
            expr = ExprStructure(0, 0, BACKQUOTE_SYMBOL, (expr,))
            expr.impKey = BACKQUOTE_FULL_NAME_SYMBOL
            expr.usage = TERM_EVAL
        args.append(expr)
    allexpr = ExprList(0, 0, args)
    return allexpr


################################################################

CONNECTION_ID = "parent"


APP_DO_EVENT = "oaa_AppDoEvent"

_AGENT_OAA = {}

def _has_oaa(agent):
    return _AGENT_OAA.has_key(agent) and _AGENT_OAA[agent] is not None

def get_oaa_connection(agent):
    """return the LibOaa OAA connection for the specified agent,
    or None if none exists"""
    if _AGENT_OAA.has_key(agent):
        return _AGENT_OAA[agent]
    return None

def _oaa(agent):
    try:
        return _AGENT_OAA[agent]
    except KeyError:
        raise RuntimeException(\
            "The OAA connection has not been started for agent %s"%agent)

def _set_oaa(agent, oaa):
    _AGENT_OAA[agent] = oaa
    if javaOaaManager is not None:
    	javaOaaManager.addOaaConnection(agent, oaa)

def _unset_oaa(agent, oaa):
    del _AGENT_OAA[agent]
    if javaOaaManager is not None:
    	javaOaaManager.removeOaaConnection(agent, oaa)
    	
def oaaStop(agent):
    if _has_oaa(agent):
        oaa = _oaa(agent)
        oaa.oaaDisconnect(IclList())
        _unset_oaa(agent, oaa)
    return True
    
def oaaStart(agent, opt_host, opt_port, opt_agentname):
    if opt_host is None:
        opt_host = ""
    if opt_port is None:
        opt_port = 0
    if opt_agentname is None:
        opt_agentname = "RandomAgent"
    solvablefacts = agent.factslist0(Solvable)
    al = ArrayList(len(solvablefacts)) # may need more if multiple arities
    debug("solvablefacts= %s", solvablefacts)
    #debug("act_arity_imp= %s/%s", act_arity_imp, ACT_ARITY)
    #debug("TEST")
    #debug("pred_imp=%s", current_agent(bindings)._pred_imp)
    for (str, sym) in solvablefacts:
        #from spark.internal.parse.newparse import symbol_get_syminfo
        decl = agent.getDecl(sym)
        minarity = decl.modes[0].sigreq
        if decl.modes[0].sigrep:
            maxarity = minarity + 8
        else:
            maxarity = minarity
        for arity in range(minarity, maxarity+1):
            #debug("Adding %s/%s", str, arity)
            args = ArrayList(arity)
            for i in range(arity):
                args.add(IclVar("_"+`i`))
            al.add(IclStruct(str, args))
    # THREADRUN
    solvables = IclList(al)
    if opt_host == "":
        hosticl = IclVar("Host")
    else:
        hosticl = IclStr(opt_host)
    if opt_port == 0:
        porticl = IclVar("Port")
    else:
        porticl = IclInt(opt_port)
    address = IclStruct("tcp", hosticl, porticl)
    libcom = LibCom(LibComTcpProtocol(),[])
    oaa = LibOaa(libcom)
    if not libcom.comConnect(CONNECTION_ID, address, EMPTY_ICL_LIST):
        raise OAAError("Cannot connect to %s"%address)
    # register callback
    #print "Registering callback"
    oaa.oaaRegisterCallback(APP_DO_EVENT, \
                            OAASolveEventListener(oaa, agent))
    # register solvables
    #print "Registering solvables", solvables
    oaa.oaaRegister(CONNECTION_ID, opt_agentname, solvables, \
                    EMPTY_ICL_LIST)
    # call ready
    #print "Calling oaaReady"
    oaa.oaaReady(True)          # print messages
    # EPILOGUE
    _set_oaa(agent, oaa)
    return [opt_host, opt_port, opt_agentname]


Solvable = Symbol("spark.io.oaa.Solvable")


################################################################
# SPARK calling OAA


def construct_goal(agent, namestring, args):
    al = ArrayList(len(args))
    varindex = 0
    for arg in args:
        if arg is not None:
            #debug("Adding %s", arg)
            al.add(value_to_icl(arg))
        else:
            #debug("Adding var")
            al.add(IclVar("Var_%d"%varindex))
            varindex = varindex + 1
     
    goal = IclStruct(namestring, al)
    oaa = _oaa(agent)
    return goal

class OAAError(LowError):
    pass

def deconstruct_answers(namestring, args, iclanswers):
    nargs = len(args)
    if not isinstance(iclanswers, IclList):
        raise OAAError("oaasolve returned something that is not a list" \
                        " but rather %s: %s" \
                        % (type(iclanswers),iclanswers))
    answers = []
    answer = list(args)[:]          # copy of the args
    for iclanswer in iclanswers.listIterator():
        debug("got answer: %s", iclanswer)
        if not isinstance(iclanswer, IclStruct):
            raise OAAError("oaasolve solutions list contains something"\
                            " that is not a structure but rather %s: %s"\
                            % (type(iclanswer), iclanswer))
        if getFunctor(iclanswer) != namestring:
            raise OAAError("oaasolve solutions list contains something"\
                            " that does not have functor %s but rather %s: %s"\
                            % (namestring, getFunctor(iclanswer), iclanswer))
        if iclanswer.size() != nargs:
            raise OAAError("oaasolve solutions list contains something"\
                            " that has not %d but %d arguments: %s"\
                            % (nargs, iclanswer.size(), iclanswer))
        for i in range(nargs):
            #print "DEBUG: processing arg", i
            if args[i] is None:
                answer[i] = icl_to_value(iclanswer.getTerm(i))
        answers.append(answer[:])   # add a copy
    return answers

def oaaSolve(agent, namestring, *args):
    return oaaPSolve(agent, namestring, (), *args)

def oaaPSolve(agent, namestring, params, *args):
        ans = None
        #Testing Script. Begin:
#        global chronometers
#        chronometers["oaaPSolve"].start()
        #Testing Script. End.                
        oaa = _oaa(agent)
        goal = construct_goal(agent, namestring, args)
        iclanswers = IclList()
        debug("calling oaaSolve on %s", goal)
        completed_without_exception = False
        functor = goal.functor
        #-------
        #print "Goal: %s, params: %s"%(goal, params)
        try:
            #debug("Calling oaaSolve(%s, %s, %s)", goal, value_to_icl(params), iclanswers)
            logInfo("oaasolve[%s]"%functor)
            result = oaa.oaaSolve(goal, value_to_icl(params), iclanswers)
            #print "RESULT is %s"%result
            #debug("Call to oaaSolve returned %s with answers %s", result, iclanswers)
            completed_without_exception = True
        finally:
            if not completed_without_exception: #record exception on its way up
                print "DEBUG: oaaSolve raised an exception"
                errid = NEWPM.displayError()
        if completed_without_exception:
            logInfo("oaasolve complete[%s]"%functor)
        if result:
            debug("oaaSolve returned success: %s", iclanswers)
            answers = deconstruct_answers(namestring, args, iclanswers)
            logInfo("oaasolve answers deconstructed[%s]"%functor)
            debug("deconstructed: %s", answers)
            if answers:
                ans = answers[0]
        else:
            debug("oaaSolve return failure: %s", iclanswers)
            raise OAAError("The call to oaaSolve [goal %s] failed and returned %s"\
                            %(functor, iclanswers))
        #Testing Script. Begin:
#        chronometers["oaaPSolve"].stop()
        #Testing Script. End.
        return ans


################################################################
# Very low level calls to oaa

def rawoaasolve(agent, sparkgoal, sparkparams, sparkpattern=None):
    oaa = _oaa(agent)
    iclgoal = value_to_icl(sparkgoal)
    iclparams = value_to_icl(sparkparams)
    iclanswers = IclList()
    debug("calling oaaSolve on %s", iclgoal)
    functor = iclgoal.functor
    logInfo("rawoaasolve[%s]"%functor)
    result = oaa.oaaSolve(iclgoal, iclparams, iclanswers)
    logInfo("rawoaasolve complete[%s]"%functor)

    if result:
        debug("oaaSolve returned success: %s", iclanswers)
        if not iclanswers.isList():
            raise LowError("The call to oaaSolve returned a non-IclList answer: %s"%iclanswers)
        if sparkpattern is None:
            ans = icl_to_value(iclanswers)
        else:
            bindings = HashMap()
            iclpattern = value_to_icl(sparkpattern)
            anslist = []
            for iclans in iclanswers.iterator():
                bindings.clear()
                if UNIFIER.matchTerms(iclans, iclgoal, bindings):
                   anslist.append(icl_to_value(UNIFIER.deref(iclpattern, bindings)))
                else:
                    raise LowError("The call to oaaSolve returned an answer that doesn't unify with the query:\nans=%s\query=%s"%(iclans, iclgoal))
            ans = List(anslist)
        logInfo("rawoaasolve answers deconstructed[%s]"%functor)
        return ans
    else:
        debug("oaaSolve return failure: %s", iclanswers)
        logError("rawoaasolve return failure with answers [%s]"%iclanswers)
        raise OAAError("The call to oaaSolve [goal %s] failed and returned %s"\
                        %(functor, iclanswers))


        
################################################################
# OAA calling SPARK



class OAASolveEventListener(OAAEventListener):
    def __init__(self, oaa, agent):
        self._oaa = oaa
        self._agent = agent
        
    def doOAAEvent(self, goal, params, _answers):
        debug("doOAAEvent(%r, %r, %r)", goal, params, _answers)
        try:
            goalname = getFunctor(goal)
            logInfo("doOAAEvent[%s]"%goalname)
            if goalname == "ev_solved":
                print "skipping the ev_solved: %s"%goal
                return True
            ext = ExternalSolve(self._oaa, goal, params)
            debug("doOAAEvent calling oaadelaySolution")
            self._oaa.oaaDelaySolution(ext.get_id())
            debug("doOAAEvent adding external %r", ext.get_id())
            self._agent.add_external(ext)
            return True
        except AnyException:
            #print "Rejected OAA request"
            errid = NEWPM.displayError()
            return False


_ID = [0]

def _getid():
    _ID[0] = _ID[0] + 1
    return _ID[0]

class ESEvent(ObjectiveEvent):
    __slots__ = ()
        
    # SparkEvent methods for handling actions
    def bindings(self):
        return self.base._bindings
    def zexpr(self):
        return self.base._zexpr
    def goalsym(self):
        return self.base._goalsym
    def kind_string(self):
        return "Do"

    def find_tframes(self, agent):
        return self.base._imp.tframes(agent, self, self.base._bindings, self.base._zexpr)

    def getParams(self):
        "Get the OAA parameters supplied with the goal"
        return self.base.getParams()

installConstructor(ESEvent)

class ExternalSolve(External):
    __slots__ = (
        "_oaa",
        "_iclgoal",
        "_params",
        "_id",
        "_zexpr",
        "_bindings",
        "_answerlist",
        "_goalsym",
        "_imp",
        )

    def __init__(self, oaa, iclgoal, params, restartGoalSymbol=None):
        External.__init__(self)
        self._oaa = oaa                 # use oaa = 0 for restarted
        self._iclgoal = iclgoal
        self._params = params
        self._id = "solver#%d"%_getid()
        # Construct arguments
        self._zexpr = iterator_to_zexpr(iclgoal.iterator())
        self._bindings = StandardExprBindings()
        self._goalsym = restartGoalSymbol

    def constructor_args(self):
        return [0, self._iclgoal, self._params, self._goalsym]

    constructor_mode = "VVVV"

    def getParams(self):
        return icl_to_value(self._params)
    
    def perform(self, agent):
        goal = self._iclgoal
        oaa = self._oaa
        debug("ExternalSolve solving %r", goal)
        # Work out what predicate/action to use
        if not goal.isStruct():
            raise InvalidICLError("Goal must be struct %s"%goal)
        goalname = getFunctor(goal)
        logInfo("ExternalSolve solving %s"%goalname)
        facts = agent.factslist1(Solvable, goalname)
        if len(facts) == 0:
            return InvalidICLError("Goal not solvable %s"%goal)
        elif len(facts) > 1:
            return InvalidICLError("Multiple definitions for goal %s"%goal)
        goalsym = facts[0][1]
        self._goalsym = goalsym
        try:
            self._imp = agent.getImp(goalsym)
            decl = agent.getDecl(goalsym)
        except KeyError:
            raise InvalidICLError("No implementation for goal symbol %s"%goalsym)
        self._answerlist = ArrayList(0)
        if decl.optMode(PRED_SOLVE):
            # Find predicate solutions
            #print "ExternalSolve finding solutions"
            for x in self._imp.solutions(agent, self._bindings, self._zexpr):
                if x:
                    self.add_solution(agent)
#             agent.push(self)
#             try:
#                 self._imp.find_solutions(agent, self._bindings, self._zexpr)
#             finally:
#                 agent.pop_check(self)
            #print "ExternalSolve found all solutions"
            # Do return value call in a different thread
            threading.Thread(target=self.return_solutions, name="ReturnSolutions").start()
        elif decl.optMode(ACTION_DO):
            # Add a tframe 
            event = ESEvent(self)
            agent.post_event(GoalPostedEvent(event))
            agent.post_event(event)
        else:
            OAAError("Implementation object is neither a predicate nor action")

    def return_solutions(self):
        answer = IclList(self._answerlist)
        debug("ExternalSolve returning solutions %r", answer)
        try:
            self._oaa.oaaReturnDelayedSolutions(self._id, answer)
            debug("ExternalSolve called oaaReturnDelayedSolutions, %s, %s",\
                  self._id, answer)
        except AnyException:
            print "Exception while returning solutions to oaa", self._id
            NEWPM.displayError()
        debug("ExternalSolve return_solutions finishing")

    def get_id(self):
        return self._id

    def add_solution(self, agent):
        #print "ExternalSolve found a solution"
        zexpr = self._zexpr
        bindings = self._bindings
        goal = self._iclgoal
        nargs = len(zexpr)
        answerargs = ArrayList(nargs)
        for zitem in zexpr:
            result = termEvalEnd(agent, bindings, zitem)
            answerargs.add(value_to_icl(result)) # TODO: not optimized
        #results = termEvalEnd(agent, bindings, zexpr)
        #for i in range(nargs):
#             if termEvalP(agent, bindings, zexpr[i]):
#                 answerargs.add(goal.getTerm(i))
#             else:
#                 answerargs.add(value_to_icl(results[i]))
        self._answerlist.add(IclStruct(getFunctor(goal), answerargs))

    # Solver target methods
    def tfhandlecfin(self, agent, subevent, result):
        if result is SUCCESS:
            agent.post_event(GoalSucceededEvent(subevent))
        else:
            agent.post_event(GoalFailedEvent(subevent, result))
        if self._oaa == 0:
            # Do nothing for a resumed solvable
            return
        if result is SUCCESS:
            self.add_solution(agent)
        threading.Thread(target=self.return_solutions, name="ReturnSolutions").start()

installConstructor(ExternalSolve)

################################################################
        
def oaa_construct(sym, *args):
    if not isSymbol(sym):
        raise LowError("oaastruct requires a symbol for its first argument, not %s", value_str(sym))
    return Structure(sym, args)

def oaa_deconstruct(struct):
    functor = struct.functor
    return List((functor,)+tuple(struct))

def dataq_to_string(dataq, string):
    from java.lang import String
    if dataq == None:
        if string == None:
            raise LowError("At least one argument needs to be bound")
        else:
            return (IclDataQ(String(string).getBytes()), string)
    else:
        s = str(String(dataq.getData()))
        if string == None:
            return (dataq, s)
        else:
            if s == string:
                return (dataq, string)
            else:
                return None
        
################################################################


from spark.internal.parse.constructor import Constructor, ConstructorValueException

class IclConstructor(Constructor):
    def createSymbol(self, start, end, string):
        al = ArrayList(1)
        al.add(IclStr(string))
        return IclStruct(ATOM_FUNCTOR, al)
    def createVariable(self, start, end, string):
        name = str(string)
        if name.startswith("$$"):
            raise ConstructorValueException("Cannot create an ICL variable equivalent to a captured variable")
        minusDollar = name[1:]
        stripped = minusDollar.lstrip("_") # look for first character after $_*
        if stripped == "" or stripped[0] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            return IclVar("_"+minusDollar)
        else:
            return IclVar(minusDollar)
    def createStructure(self, start, end, functor_name, args):
        nargs = len(args)
        if nargs == 0:                  # treat as '@@'("absname")
            args = (IclString(functor_name),)
            functor_name = NULLARY_FUNCTOR
            nargs = 1
        al = ArrayList(nargs)
        for elt in args:
            al.add(elt)
        return IclStruct(functor_name, al)
    def createList(self, start, end, elements):
        al = ArrayList(len(elements))
        for elt in elements:
            al.add(elt)
        return IclList(al)
    def createString(self, start, end, string):
        return IclStr(string)
    def createInteger(self, start, end, integer):
        return IclInt(integer)
    def createBigInteger(self, start, end, integer):
        raise ConstructorValueException("Cannot handle big integers")
    def createFloat(self, start, end, float):
        return IclFloat(float)
    def start(self, obj):
        return -1
    def end(self, obj):
        return -1
    def asFloat(self, obj):
        try:
            return obj.toFloat()
        except:
            raise ConstructorValueException("Not a Float: %r"%obj)

    def asInteger(self, obj):
        try:
            i = obj.toInt()
            return int(i)
        except:
            raise ConstructorValueException("Not a valid integer: %r"%obj)

    def asBigInteger(self, obj):
        raise ConstructorValueException("Cannot handle big integers")

    def category(self, object):
        if object.isStr():
            return self.STRING
        elif object.isInt():
            return self.INTEGER
        elif object.isFloat():
            return self.FLOAT
        elif object.isStruct():
            functor = getFunctor(object)
            if functor == ATOM_FUNCTOR:
                return self.SYMBOL
            else:
                return self.STRUCTURE
        elif object.isList():
            return self.LIST
        elif object.isVar():
            return self.VARIABLE
        elif object.isIclDataQ():
            return self.STRING
        else:
            raise ConstructorValueException("Not a valid object")

    def functor(self, object):
        if object.isStruct():
            functor = getFunctor(object)
            if functor == ATOM_FUNCTOR:
                return None
            elif functor == NULLARY_FUNCTOR:
                functor = object.getTerm(0).toString()
            return functor
        elif object.isList():
            return None
        else:
            raise ConstructorValueException("Not a compound object")

    def asString(self, obj):
        if obj.isStr():
            return obj.toUnquotedString()
        elif obj.isVar():
            name = iclVarName(obj)
            stripped = name.lstrip("_")
            if stripped == "" or stripped[0] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                return '$' + name[1:]
            else:
                return '$' + name
        elif obj.isStruct():
            functor = getFunctor(obj)
            args = [icl_to_value(x) for x in obj.iterator()]
            if functor == ATOM_FUNCTOR and obj.getNumChildren() == 1:
                return obj.getTerm(0).toUnquotedString()
        elif obj.isIclDataQ():
            return dataq_to_string(obj, None)[1]
        else:
            raise ConstructorValueException("Not a String, Variable, or Symbol")
            
    def components(self, obj):
        if obj.isList():
            return [x for x in obj.iterator()]
        elif obj.isStruct():
            functor = getFunctor(obj)
            if functor == ATOM_FUNCTOR:
                return None
            elif functor == NULLARY_FUNCTOR:
                return ()
            else:
                return [x for x in obj.iterator()]
        else:
            raise ConstructorValueException("Not a compound object")

ICL_CONSTRUCTOR = IclConstructor()

def get_oaa(agent):
    oaa = get_oaa_connection(agent)
    if not oaa:
        raise OAAError("oaa object is null, you may not be connected to the facilitator.")
    return oaa

def get_online_agents(agent):
    oaa = get_oaa(agent)
    OAAAGENTS = []
    tTerm = IclTerm.fromString(True, "agent_data(Id,Type,ready,Sv,Name,Info)")
    answers = IclList()
    oaa.oaaSolve(tTerm, IclList(IclTerm.fromString(True, "block(true)")),answers)    
    for i in range(answers.size()):
        OAAAGENTS.append(answers.getTerm(i).getTerm(4).toIdentifyingString()) # Name is term #4.
    return OAAAGENTS
    
def can_solve(agent, goal):
    oaa = get_oaa(agent)
    return oaa.oaaCanSolve(goal)

    
def oaa_set_trigger(agent,type,triggerterm,actionterm,params):
    oaa = get_oaa(agent)
    return oaa.oaaAddTrigger(value_to_icl(type), value_to_icl(triggerterm), value_to_icl(actionterm), value_to_icl(params))


def get_agent_address(agent):
    oaa = get_oaa(agent)    
    address = oaa.oaaPrimaryAddress()
    return address
    
def oaa_add_data(agent, clause, params):
    oaa = get_oaa(agent)
    return oaa.oaaAddData(clause, params)    
    
    
def oaa_replace_data(agent, clause1, clause2, params):
    oaa = get_oaa(agent)
    return oaa.oaaReplaceData(clause1, clause2, params)
    
def oaa_remove_data(agent, clause, params):
    oaa = get_oaa(agent)
    return oaa.oaaRemoveData(clause, params)
