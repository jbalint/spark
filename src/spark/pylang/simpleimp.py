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
#* "$Revision:: 201                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from __future__ import generators
import inspect
import operator

from spark.internal.version import *
from spark.internal.exception import LowError, Failure, ExceptionFailure, LocatedError, MessageFailure, CapturedError
from spark.internal.common import NEWPM, DEBUG
from spark.internal.parse.basicvalues import ConstructibleValue, installConstructor
import threading

from spark.pylang.implementation import Imp, FunImpInt, PredImpInt, PersistablePredImpInt, ActImpInt
from spark.internal.repr.taskexpr import SUCCESS, TFrame
from spark.internal.common import NO_SOLUTIONS, ONE_SOLUTION, SOLVED, NOT_SOLVED
from spark.internal.repr.procedure import ProcedureInt
from spark.internal.parse.usagefuns import *

debug = DEBUG(__name__)#.on()

#from spark.mode import RequiredMode, ALL_EVALUABLE_CALL_MODE
#from spark.set import IBITS, bitmap_indices


def make_callable(x):
    if callable(x):
        return x
    elif inspect.isclass(x):   # Java classes mistakenly fail callable
        return x
    else:
        raise LowError("Cannot coerce %r to something that is callable", x)


class _Basic(ConstructibleValue):
    __slots__ = (
        "_function",
        "_modeString",
        "_sym",
        "_both_indices",
        "_input_indices",
        "_rest_mode",
        "_nrequired",
        "_output_indices",
        "_output_range",
        "_input_agent_p",
        #"_optargs_mode",
        )
    def __init__(self, mode, fun):
        ConstructibleValue.__init__(self)
        # Mode string is of the form [A]?[+?-]+[*]?
        #print "New Basic:", mode, fun
        self._modeString = mode
        if mode.startswith("A"):
            # fun takes the agent as an argument
            self._input_agent_p = True
            io = mode[1:]
        else:
            self._input_agent_p = False
            io = mode
        self._input_indices = []
        self._both_indices = []
        self._output_indices = []
        if io.endswith("*"):
            if not (io[-2:] in ("+*","-*","?*")): raise AssertionError, \
                   "Repeated mode must be one of +, ?, or -: %s" % mode
            self._rest_mode = io[-2]
            io = io[:-2]
        elif len(io) > 1 and io[-2] == "*": # allow *+ stlye rest mode declaration
            if not (io[-2:] in ("*+", "*-", "*?")): raise AssertionError, \
                   "Repeated mode must be one of +, ?, or -: %s" % mode
            self._rest_mode = io[-1]
            io = io[:-2]
        else:
            self._rest_mode = None
        self._nrequired = len(io)
        for i in range(len(io)):
            char = io[i]
            if char == "+":
                # This is an input parameter
                self._input_indices.append(i)
            elif char == "-":
                # This is an output parameter
                self._output_indices.append(i)
            elif char == "?":
                # Acts as both an input and an output
                self._input_indices.append(i)
                self._output_indices.append(i)
                self._both_indices.append(i)
            else:
                raise LowError("The mode string %r is not valid", mode)
        self._function = make_callable(fun)
        self._output_range = range(len(self._output_indices))
        self._sym = None

    def valid_mode_p(self, agent, bindings, zexpr):
#         # DNM - THIS IS A DREADFUL HACK NEEDED UNTIL WE DELAY DECL EVALUATION
#         from spark.internal.repr.varbindings import NULL_BINDINGS
#         if bindings == NULL_BINDINGS:
#             return True
        for i in self._input_indices:
            if not (i in self._both_indices or termEvalP(agent, bindings, zexpr[i])):
                return False
        if self._rest_mode == "-":
            i = self._nrequired
            limit = len(zexpr)
            while i < limit:
                if not termEvalP(agent, bindings, zexpr[i]):
                    return False
                i = i + 1
        return True

    def generate_args(self, agent, bindings, zexpr):
        "Returns a list of the input argument values"
        # should check arity as well
        if not self.valid_mode_p(agent, bindings, zexpr):
            raise LowError("Required argument is not bound")
        args = [termEvalOpt(agent, bindings, zexpr[i]) \
                for i in self._input_indices]
        if self._rest_mode in ("+", "?"): # accumulate rest arguments
            i = self._nrequired
            limit = len(zexpr)
            while i < limit:
                args.append(termEvalOpt(agent, bindings, zexpr[i]))
                i = i + 1
        if self._input_agent_p:
            args.insert(0, agent)       # prepend agent
        return args

    def bind_result(self, agent, bindings, zexpr, result):
        if result is None:      # None does not matching anything
            return False
        output_indices = self._output_indices
        has_rest_output = self._rest_mode in ("?", "-")
        l = len(output_indices)
        if l > 1 or has_rest_output:
            # Treat result as a tuple of values
            if not (operator.isSequenceType(result)): raise AssertionError, \
                   "Python function should return a sequence but returned %r instead"%(result,)
            minOut = len(self._output_range)
            actualOut = len(result)
            if has_rest_output:
                if actualOut < minOut:
                    raise LocatedError(zexpr, "Expecting python function to return at least %s elements, not %r"%(minOut, result))
            else:
                if actualOut != minOut:
                    raise LocatedError(zexpr, "Expecting python function to return exactly %s elements, not %r"%(minOut, result))
            for i in self._output_range:
                if not termMatch(agent, bindings, zexpr[output_indices[i]], result[i]):
                    return False
            if has_rest_output:
                limit = len(zexpr)
                i = self._nrequired
                offset = i - len(self._output_indices)
                while i < limit:
                    if termEvalP(agent, bindings, zexpr[i]):
                        pass            # No need to match the argument
                    elif not termMatch(agent, bindings, zexpr[i], result[i-offset]):
                        return False
                    i = i+1
            return True
        elif l == 1:                    # Exactly one output parameter
            # Treat result as a value
            return termMatch(agent, bindings, zexpr[output_indices[0]], result)
        elif result:                    # l == 0, no output parameters
            return True
        else:
            return False

    def setDecl(self, decl):
        symbol = decl and decl.asSymbol()
        if not (self._sym is None or self._sym == symbol): raise AssertionError, \
               "Attempting to rename a named object %r"%self
        self._sym = symbol

    def __call__(self, decl):
        self.setDecl(decl)
        return self

    def constructor_args(self):
        return [self._modeString, self._function]

    cvcategory = "B"
    def cvname(self):
        if self._sym:
            return self._sym.id
        else:
            return ""

    constructor_mode = "VI"

    def function_name(self):
        f = self._function
        from spark.lang.builtin import PythonProxyRaw, Method
        if isinstance(f, PythonProxyRaw):
            return "function "+f._PythonProxyModName + "." + f._PythonProxyVarName
        elif isinstance(f, Method):
            return "method ."+f._methodname
        else:
            return "function ?"


################################################################
# Functions

class BasicFun(_Basic, FunImpInt):
    __slots__ = ()

    def __init__(self, mode, fun):
        _Basic.__init__(self, mode, fun)
        if self._output_indices: #len(self._output_indices) > 0:
            raise LowError("Mode string %r is not valid for a function", mode)

    def call(self, agent, bindings, zexpr):
        args = self.generate_args(agent, bindings, zexpr)
        return self._function(*args)

    def match_inverse(self, agent, bindings, zexpr, obj):
        raise LowError("Trying to match non-invertible function")

installConstructor(BasicFun)

class ReversibleFun(BasicFun):
    __slots__ = (
        "_inverse",
        )

    def __init__(self, mode, fun, inverse):
        BasicFun.__init__(self, mode, fun)
        self._inverse = make_callable(inverse)

    def match_inverse(self, agent, bindings, zexpr, obj):
        inverse = self._inverse
        # If the function requires the agent, so will the inverse
        if self._input_agent_p:
            result = self._inverse(agent, obj)
        else:
            result = self._inverse(obj)
        # A None result indicates no match
        if result == None:
            return False
        # Identify number of inputs parameters to function
        num_fixed_input_args = len(self._input_indices)
        if self._rest_mode is not None \
               or num_fixed_input_args > 1: # may be multiple
            # Result should be a tuple
            length = len(result)
            if length != len(zexpr):
                return False
            i = 0
            while i < length:
                if not termMatch(agent, bindings, zexpr[i], result[i]):
                    return False
                i += 1
            return True
        elif num_fixed_input_args == 1: # exactly one
            # Result should be a value
            return termMatch(agent, bindings, zexpr[0], result)
        else:                           # exactly 0
            # result should be a Boolean
            return result

    def constructor_args(self):
        return BasicFun.constructor_args(self) + [self._inverse]

    constructor_mode = "VII"
installConstructor(ReversibleFun)

################################################################
# Predicates

class BasicPred(_Basic, PredImpInt):
    """Implements a predicate via a function that returns None or a solution"""
    __slots__ = ()

    def solution(self, agent, bindings, zexpr):
        result = self._function(*self.generate_args(agent, bindings, zexpr))
        debug("BasicPred function returned %r", result)
        if result is not None:
            if self.bind_result(agent, bindings, zexpr, result):
                debug("BasicPred solution %r", result)
                return SOLVED
        return NOT_SOLVED
            
#     def find_solutions(self, agent, bindings, zexpr):
#         result = self._function(*self.generate_args(agent, bindings, zexpr))
#         debug("BasicPred function returned %r", result)
#         if result is not None:
#             if self.bind_result(agent, bindings, zexpr, result):
#                 debug("BasicPred solution %r", result)
#                 bindings.bfound_solution(agent, zexpr)

installConstructor(BasicPred)

class BasicPredSequence(_Basic, PredImpInt):
    """Implements a predicate via a function that returns a sequence of solutions"""
    __slots__ = ()
    
    def solution(self, agent, bindings, zexpr):
        result = self._function(*self.generate_args(agent, bindings, zexpr))
        debug("BasicPredSequence function returned %r", result)
        # Should check for None
        for res in result:
            if self.bind_result(agent, bindings, zexpr, res):
                debug("BasicPredSequence solution %r", res)
                return SOLVED
        return NOT_SOLVED
    
    def solutions(self, agent, bindings, zexpr):
        result = self._function(*self.generate_args(agent, bindings, zexpr))
        debug("BasicPredSequence function returned %r", result)
        # Should check for None
        for res in result:
            if self.bind_result(agent, bindings, zexpr, res):
                debug("BasicPredSequence solution %r", res)
                yield SOLVED
                
#     def find_solutions(self, agent, bindings, zexpr):
#         result = self._function(*self.generate_args(agent, bindings, zexpr))
#         debug("BasicPredSequence function returned %r", result)
#         # Should check for None
#         for res in result:
#             if self.bind_result(agent, bindings, zexpr, res):
#                 debug("BasicPredSequence solution %r", res)
#                 bindings.bfound_solution(agent, zexpr)

installConstructor(BasicPredSequence)

################################################################
class MultiModalPred(PredImpInt):
    """A predicate implementation that is based on other implementations"""
    __slots__ = (
        "_imps",
        "_sym",
        )
    def __init__(self, *imps):
        self._imps = imps
        self._sym = None

    def valid_mode_p(self, agent, bindings, zexpr):
        for imp in self._imps:
            if imp.valid_mode_p(agent, bindings, zexpr):
                return True
        return False
    
    def solution(self, agent, bindings, zexpr):
        for imp in self._imps:
            if imp.valid_mode_p(agent, bindings, zexpr):
                return imp.solution(agent, bindings, zexpr)
        raise LowError("Calling predicate with invalid mode")

    def solutions(self, agent, bindings, zexpr):
        for imp in self._imps:
            if imp.valid_mode_p(agent, bindings, zexpr):
                return imp.solutions(agent, bindings, zexpr)
        raise LowError("Calling predicate with invalid mode")

#     def find_solutions(self, agent, bindings, zexpr):
#         for imp in self._imps:
#             if imp.valid_mode_p(agent, bindings, zexpr):
#                 imp.find_solutions(agent, bindings, zexpr)
#                 return
#         raise LowError("Calling predicate with invalid mode")

    def setDecl(self, decl):
        symbol = decl and decl.asSymbol()
        if not (self._sym is None or self._sym == symbol): raise AssertionError, \
               "Attempting to rename a named object %r"%self
        self._sym = symbol
        for imp in self._imps:
            imp(decl)

    def __call__(self, decl):
        self.setDecl(decl)
        return self


################################################################
# Actions

#@-timing# from spark.internal.timer import TIMER
#@-# T_tfcont = TIMER.newRecord("tfcont")
#@-# T_genargs = TIMER.newRecord("genargs")
#@-# T_callfn = TIMER.newRecord("callfn")
#@-# T_processresult = TIMER.newRecord("processresult")

class BasicImpTFrame(TFrame):
    __slots__ = (
        "_basicact",
        "_bindings",
        "_zexpr",
        )

    def cvname(self):
        return self._basicact.cvname()

    def __init__(self, name, event, basicact, bindings, zexpr):
        TFrame.__init__(self, name, event)
        self._basicact = basicact
        self._bindings = bindings
        self._zexpr = zexpr

    def constructor_args(self):
        return TFrame.constructor_args(self) + [self._basicact, self._bindings, self._zexpr]
    constructor_mode = "VIIIV"

    def tfcont(self, agent):
        #@-timing# T_tfcont.start()
        try:
            #debug("Creating args for %r", self)
            #@-timing# T_genargs.start()
            args = self._basicact.generate_args(agent, self._bindings, self._zexpr)
            #@-timing# T_genargs.stop()
            #debug("Calling %r on %r", self._basicact._function, args)
            #@-timing# T_callfn.start()
            val = self._basicact._function(*args)
            #@-timing# T_callfn.stop()
        except LocatedError, e:
            errid = NEWPM.displayError()
            #@-timing# T_callfn.stop()
            #@-timing# T_processresult.start()
            self.process_exception(agent, e, errid)
            #@-timing# T_processresult.stop()
            #@-timing# T_tfcont.stop()
            return
        except AnyException, e:
            errid = NEWPM.displayError()
            #@-timing# T_callfn.stop()
            #@-timing# T_processresult.start()
            # TODO: work out if this is the right way to handle this case
            new_err = CapturedError(self._zexpr, errid, "executing")
            self.process_exception(agent, new_err, errid)
            #@-timing# T_processresult.stop()
            #@-timing# T_tfcont.stop()
            return
        #@-timing# T_processresult.start()
        self.process_result(agent, val)
        #@-timing# T_processresult.stop()
        #@-timing# T_tfcont.stop()
        
    def process_exception(self, agent, e, errid):
        result = e
        if not isinstance(e, Failure):
           result = ExceptionFailure(self, e, errid)
        
        #print "Setting result=", result
        self.tf_set_completed(agent, result)

    def process_result(self, agent, val):
        if not self._basicact._output_indices: # i.e., length == 0:
            # Note that a function returning None is treated as SUCCESS
            if val is False:
                result = MessageFailure(self, "%s implementing action returned False"%self._basicact.function_name())
            elif isinstance(val, Failure):
                result = val
            else:
                result = SUCCESS
        elif self._basicact.bind_result(agent, self._bindings, self._zexpr, val):
            result = SUCCESS
        elif val == None:
            result = MessageFailure(self, "%s implementing action returned None"
                                    %self._basicact.function_name())
        else:
            try:
                raise Exception("%s implementing action returned a value %r that does not match the output params %r"%(self._basicact.function_name(), val, self._basicact._output_indices))
            except AnyException, e:
                errid = NEWPM.displayError()
                #@-timing# T_callfn.stop()
                #@-timing# T_processresult.start()
                # TODO: work out if this is the right way to handle this case
                new_err = CapturedError(self._zexpr, errid, "executing")
                self.process_exception(agent, new_err, errid)
                return
        #print "Setting result=", result
        self.tf_set_completed(agent, result)
installConstructor(BasicImpTFrame)

class BasicAct(_Basic, ActImpInt):
    __slots__ = ()

    tframe_class = BasicImpTFrame
    def tframes(self, agent, event, bindings, zexpr):
        name = "%s.%d"%(self._sym, agent.nextid())
        return [self.tframe_class(name, event, self, bindings, zexpr)]

installConstructor(BasicAct)

#@-timing# T_ThreadImpTFrameInit = TIMER.newRecord("ThreadImpTFrameInit")

class ThreadImpTFrame(BasicImpTFrame):
    __slots__ = (
        "_thread_event",
        "_thread_result",
        "_thread_exception",
        "_agent_to_do_flag",
        "_errid",
        )

    def __init__(self, name, event, threadact, bindings, zexpr):
        BasicImpTFrame.__init__(self, name, event, threadact, bindings, zexpr)
        self._thread_event = None

    def state_args(self):
        return (0,)

    def set_state(self, agent, ignore):
        self.tf_set_completed(agent, MessageFailure(self, "ThreadImpTFrame cannot be resumed"))
        
    def tfcont(self, agent):
        #debug("ThreadImpTFrame tfcont")
        #@-timing# T_tfcont.start()
        te = self._thread_event
        if te is None:
            #print "Starting thread"
            #@-timing# T_genargs.start()
            args = self._basicact.generate_args(agent, self._bindings, self._zexpr)
            #@-timing# T_genargs.stopstart(T_callfn)
            self._thread_event = threading.Event()
            self._thread_result = None
            self._thread_exception = None
            self._agent_to_do_flag = agent._something_to_do_event
            #debug("ThreadImpTFrame starting thread")
            threading.Thread(target=self.run, args=args).start()
            #THREAD_POOL.startDaemonThread(target=self.run, args=args)
            #@-timing# T_callfn.stop()
        elif te.isSet():
            #@-timing# T_processresult.start()
            #print "Noticed thread finished"
            if self._thread_exception:
                #debug("ThreadImpTFrame processing exception %s", self._thread_exception)
                self.process_exception(agent, self._thread_exception, self._errid)
            else:
                #debug("ThreadImpTFrame processing result %s", self._thread_result)
                self.process_result(agent, self._thread_result)
            #@-timing# T_processresult.stop()
            #debug("ThreadImpTFrame tfcont return not waiting")
        else:
            #print "Waiting for thread"
            #debug("ThreadImpTFrame tfcont return waiting")
            #return None
            pass
        #@-timing# T_tfcont.stop()
                
    def run(self, *args):
        try:
            #print " Starting fun"
            self._thread_result = self._basicact._function(*args)
            #print " Finished fun"
        except AnyException, e:
            #print " Exception in fun"
            errid = NEWPM.displayError()
            self._thread_exception = e
            self._errid = errid
        self._thread_event.set()
        self._agent_to_do_flag.set()
installConstructor(ThreadImpTFrame)

class ThreadAct(BasicAct):
    __slots__ = ()
    tframe_class = ThreadImpTFrame

installConstructor(ThreadAct)

################################################################
# What follows should be removed once things that depend upon it are fixed
################################################################
    
class SimpleProcedureInstance(TFrame):
    __slots__ = (
        "_procedure",
        "_bindings",                # should be able to get from event
        "_zexpr",                   # should be able to get from event
        "_features",
        )
    def __init__(self, name, procedure, event, bindings, zexpr):
        TFrame.__init__(self, name, event)
        self._procedure = procedure 
        self._bindings = bindings
        self._zexpr = zexpr
        self._features = ()

    def constructor_args(self):
        [name, event] = TFrame.constructor_args(self)
        return [name, self._procedure, event, self._bindings, self._zexpr]
    constructor_mode = "VIIIV"

    def tfcont(self, agent):
        result = self._procedure.execute(agent,self._event,self._bindings,self._zexpr)
        if not (result is SUCCESS or isinstance(result, Failure)):
            raise LowError(\
                """execute method of procedure returned something that was
                neither SUCCESS of a Failure instance
                procedure: %s
                return value: %s""", self._procedure, result)
        self.tf_set_completed(agent, result)

    def features(self, agent):
        return self._features

installConstructor(SimpleProcedureInstance)

class SimpleProcedure(ProcedureInt):
    __slots__ = (
        "_name",
        )
    def __init__(self, name):
        self._name = name
    def name(self):
        return self._name
    def append_tframes(self, agent, event, bindings, zexpr, list):
        if self.applicable(agent, event, bindings, zexpr):
            name = "%s.%d"%(self._name, agent.nextid())
            list.append(SimpleProcedureInstance(name, self, event, bindings, zexpr))

    def applicable(self, agent, event, bindings, zexpr):
        return True                     # default precondition

    def execute(self, agent, event, bindings, zexpr):
        raise LowError("execute method not defined for %r", self)

    def __str__(self):
        return self.__class__.__name__ + "." + self._name

    def __repr__(self):
        return self.__class__.__name__ + "." + self._name



################################################################

# class ThreadProcedureInstance(TFrame):
#     __slots__ = (
#         "_procedure",
#         "_bindings",                # should be able to get from event
#         "_zexpr",                   # should be able to get from event
#         "_thread_event",
#         "_thread_result",
#         "_thread_exception",
#         )
#     def __init__(self, name, procedure, event, bindings, zexpr):
#         TFrame.__init__(self, name, event)
#         self._procedure = procedure
#         self._bindings = bindings
#         self._zexpr = zexpr
#         self._thread_event = None
#         self._thread_result = None
#         self._thread_exception = None

#     def tfcont(self, agent):
#         te = self._thread_event
#         try:
#             if te is None:                  # thread not started
#                 data = self._procedure.prologue(agent,self._event,self._bindings,self._zexpr)
#                 te = threading.Event()
#                 self._thread_event = te
#                 #print "STARTING te.isSet() =", te.isSet()
#                 thread = threading.Thread(target=self._threadrun, \
#                                           args=(agent, data), name="Thread")
#                 thread.start()            
#             elif te.isSet():                # thread complete
#                 #print "FINISHED te.isSet() =", te.isSet()
#                 if self._thread_exception:
#                     raise self._thread_exception # DNM - maybe re-raise
#                 result = self._procedure.epilogue(agent, self._event, self._bindings, self._zexpr, self._thread_result)
#                 if not (result is SUCCESS or isinstance(result, Failure)): raise AssertionError
#                 self.tf_set_completed(agent, result)
#             else:
#                 #print "WAITING te.isSet() =", te.isSet(), self._procedure
#                 return NOCHANGE
#         except Failure, failure:
#             self.tf_set_completed(agent, failure)
#         except AnyException, e:
#             pm.setprint()
#             self.tf_set_completed(agent, ExceptionFailure(self, e))
#         return None

#     def _threadrun(self, agent, data):
#         try:
#             self._thread_result = self._procedure.threadrun(data)
#         except AnyException, e:
#             self._thread_exception = ExceptionFailure(self, e)
#             pm.setprint()
#         #print "THREAD COMPLETED"
#         self._thread_event.set()
#         agent._something_to_do_event.set()

# class ThreadProcedure(object, ProcedureInt):
#     __slots__ = (
#         "_name",
#         )
#     def __init__(self, name):
#         self._name = name
#     def name(self):
#         return self._name
#     def append_tframes(self, agent, event, bindings, zexpr, list):
#         if self.applicable(agent, event, bindings, zexpr):
#             name = "%s.%d"%(self._name, agent.nextid())
#             list.append(ThreadProcedureInstance(name, self, event, bindings, zexpr))

#     def applicable(self, agent, event, bindings, zexpr):
#         return True                     # default precondition

#     def prologue(self, agent, event, bindings, zexpr):
#         return None

#     def threadrun(self, prologue_data):
#         raise LowError("threadrun method not implemented for %r", self)

#     def epilogue(self, agent, event, bindings, zexpr, threadrun_result):
#         return threadrun_result

class ProcedureActImp(ActImpInt):
    """An action that is implemented by executing a fixed procedure"""

    def __init__(self, procedure):
        if not (isinstance(procedure, ProcedureInt)): raise AssertionError
        self._procedure = procedure

    def __call__(self, symbol):
        self._symbol = symbol
        return self

    def tframes(self, agent, event, bindings, zexpr):
        tframes = []
        self._procedure.append_tframes(agent, event, bindings, zexpr, tframes)
        return tframes

################################################################
    
class CounterImp(Imp, PersistablePredImpInt):
    #NOTE: single agent implementation (SINGLEAGENT). easy to make multiagent
    __slots__ = ('counter')

    def __init__(self, decl):
        Imp.__init__(self, decl)
        self.counter = 0

    #PERSIST
    def persist_arity_or_facts(self, ignore_agent):
        return [[self.counter]]

    def resume_conclude(self, agent, bindings, zexpr):
        self.counter = termEvalErr(agent, bindings, zexpr[0])
        
    def solution(self, agent, bindings, zexpr):
        if len(zexpr) != 1:
            raise zexpr.error("Invalid arity -- counters have arity of 1")
        if self.counter is not None and \
               termMatch(agent, bindings, zexpr[0], self.counter):
            return SOLVED
        else:
            return NOT_SOLVED

#     def find_solutions(self, agent, bindings, zexpr):
#         if len(zexpr) != 1:
#             raise zexpr.error("Invalid arity -- counters have arity of 1")
#         if self.counter is not None and \
#                termMatch(agent, bindings, zexpr[0], self.counter):
#             bindings.bfound_solution(agent, zexpr)

    def conclude(self, agent, bindings, zexpr):
        """Conclude this predicate and return whether the database has
        been changed."""
        if len(zexpr) != 1:
            raise zexpr.error("Invalid arity -- counters have arity of 1")
        self.counter = termEvalErr(agent, bindings, zexpr[0])

    def retractall(self, agent, bindings, zexpr):
        """Retract anything matching this predicate and return whether
        the datadase has been changed."""
        raise zexpr.error("Cannot retractall on a counter implementation")

# ################################################################
# # ThreadPool
# #
# # source of threads that can be reused
# #

# import Queue

# class ThreadPool(object):
#     __slots__ = (
#         "idleWorkerThreadsQueue",
#         )

#     def __init__(self, maxsize=0):
#         self.idleWorkerThreadsQueue = Queue.Queue(maxsize)

#     def startDaemonThread(self, target=None, name=None, args={}, kwargs={}):
#         "Take an idle WorkerThread from the pool and run target function on the given args. Create a new _WorkerThread if necessary."
#         queue = self.idleWorkerThreadsQueue
#         try:
#             workerThread = queue.get(False)
#             #print "Taking", workerThread, "from", queue
#         except Queue.Empty:
#             workerThread = _WorkerThread()
#             #print "Creating new", workerThread
#             workerThread.setDaemon(True)
#             workerThread.start()
#         workerThread.invokeRun(queue, target, name, args, kwargs)

#     def killIdleWorkerThreads(self, leave=0):
#         queue = self.idleWorkerThreadsQueue
#         while queue.qsize() > leave:
#             try:
#                 workerThread = queue.get(False)
#             except Queue.Empty:
#                 return
#             workerThread.killIdleWorkerThread()
        

# THREAD_POOL = ThreadPool(0) # Allow an unlimited number of idle threads

# class _WorkerThread(threading.Thread):
#     __slots__ = (
#         "workLock",                    # Lock to say work is available
#         "oldname",                      # original name of thread
#         "idleWorkerThreadsQueue",     # queue to put self on when idle
#         "target",                       # runnable object
#         "name",                         # name to use
#         "args",                         # args to use
#         "kwargs",                       # keyword args to use
#         )

#     def __init__(self):
#         threading.Thread.__init__(self)
#         self.workLock = threading.Lock()
#         self.workLock.acquire()         # invokeRun will release this Lock
#         self.oldname = self.getName()
#         self._reset()

#     def _reset(self):
#         self.setName(self.oldname)
#         self.idleWorkerThreadsQueue = None
#         self.target = None
#         self.name = None
#         self.args = None
#         self.kwargs = None

#     def run(self):
#         terminate = False
#         while not terminate:
#             terminate = self.performRun()

#     def performRun(self):
#         "Acquire lock, and perform the target function. Return Ture if thread should exit."
#         self.workLock.acquire()         # wait until something to do
#         # Check if we should die
#         idleWorkerThreadsQueue = self.idleWorkerThreadsQueue
#         if idleWorkerThreadsQueue is None:
#             #print "Killing", self
#             return True
#         # call the target function
#         #print "Using", self, "to run", self.target
#         if self.name is not None:
#             self.setName(self.name)
#         try:
#             self.target(*self.args, **self.kwargs)
#         except:
#             print "Exception in WorkerThread", self.getName()
#             errid = NEWPM.displayError()
#         # reset self and go back on the idle queue
#         self._reset()
#         #print "Putting", self, "back on", idleWorkerThreadsQueue
#         try:
#             idleWorkerThreadsQueue.put_nowait(self)
#         except Queue.Full:
#             #print "Idle _WorkerThread Queue is full, kill _WorkerThread instead"
#             return True
#         return False

#     def invokeRun(self, queue, target, name, args, kwargs):
#         if self.workLock.acquire(False): raise AssertionError, \
#            "Trying to call _WorkerThread.invokeRun with workLock unlocked"
#         if queue is None: raise AssertionError, \
#            "Must supply a Queue to return _WorkerThread to when done"
#         if target is None: raise AssertionError, \
#            "Must supply a target function to execute"
#         self.idleWorkerThreadsQueue = queue
#         self.target = target
#         self.name = name
#         self.args = args
#         self.kwargs = kwargs
#         self.workLock.release()

#     def killIdleWorkerThread(self):
#         "Kill off this _WorkerThread"
#         if self.target is not None: raise AssertionError, \
#            "Cannot kill a _WorkerThread that is current executing something"
#         self.idleWorkerThreadsQueue = None
#         self.workLock.release()
            
# ONE_WORKER_THREAD = _WorkerThread()
