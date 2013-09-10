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
#* "$Revision:: 26                                                        $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from __future__ import generators
from spark.internal.version import *
from spark.internal.common import paranoid, re_raise, ABSTRACT, DEBUG, SOLVED, NOT_SOLVED
from spark.internal.parse.processing import Imp, StandardExprBindings
from spark.internal.repr.taskexpr import PseudoGoalEvent, TaskExprTFrame

from spark.pylang.implementation import FunImpInt, PredImpInt, ActImpInt
from spark.internal.parse.basicvalues import ConstructibleValue, installConstructor
from spark.internal.parse.usagefuns import *

debug = DEBUG(__name__)#.on()

################################################################
# Common Closure classes


#class ClosurePatExpr(Atomic, PatExpr):
class ClosureImp(Imp):
    __slots__ = ()

    evaluate_class = ABSTRACT          # subclasses redefine this slot

    def call(self, agent, bindings, zexpr):
        captured = [(vi, bindings.getVariableValue(agent, vo)) \
                    for (vo,vi) in zexpr.captured.items()]
        return self.evaluate_class(captured, zexpr)


class ClosureValue(ConstructibleValue):
    __slots__ = (
        "captured_dict",         # dict mapping ext vars to values
        "closed_zexpr",                 #
        )

    make_bindings_class = ABSTRACT           # subclasses redefine this

    def __init__(self, captured, closed_zexpr):
        ConstructibleValue.__init__(self)
        self.closed_zexpr = closed_zexpr
        self.captured_dict = dict(captured)

    def __repr__(self):
        import string
        captured = ["%s=%s"%(k, `v`) \
                    for (k,v) in self.captured_dict.items()]
        return "%s(%s%s)"%(self.__class__.__name__, self.closed_zexpr,
                                    string.join(captured, ','))


    def make_bindings(self, agent, bindings, zexpr):
        "Use closure to create a new bindings"
        newbindings =  self.make_bindings_class(self)
        newbindings.setVariables(self.captured_dict)
        newbindings.setLevel(bindings.level() + 1)
        return newbindings.bformals(agent, bindings, zexpr, True)

    # NOTE - we have to do something better for equality of these
    # Currently (= {fun [] 1} {fun [] 1}) fails!!!

    def constructor_args(self):
        return [tuple(self.captured_dict.items()), self.closed_zexpr]
    constructor_mode = "VV"

    def __call__(self, ignore_decl):
        # Used to install this as the imp of a symbol in an agent
        return self



class ClosureBindings(StandardExprBindings):
    __slots__ = (
        "_closureValue",
        "_level",                       # for debugging
        )
    def __init__(self, closureValue, level=0):
        StandardExprBindings.__init__(self)
        self._closureValue = closureValue
        self._level = level

    def copy(self):
        c = self.__class__(self._closureValue)
        c.setVariables(self._variables)
        c._level = self._level
        return c
    
    def _getSPU(self):                  # UNUSED?
        return self._closureValue.closed_zexpr.getSPU()

    def bformals(self, agent, bindings, zexpr, match):
        """Match/return the given actual parameters to the formal parameters.
        Return self if there was a match, return None otherwise."""
        # default case, match against self._closureValue.closed_zexpr[0]
        fzitem = self._closureValue.closed_zexpr[0]
        if formals(agent, self, fzitem, bindings, zexpr, match):
            return self
        else:
            return None
    def level(self):
        return self._level
    def setLevel(self, level):
        self._level = level
    ################
    # ConstructibleValue methods
    
    def constructor_args(self):
        return [self._closureValue, self._level]
    constructor_mode = "VV"

installConstructor(ClosureBindings)

################################################################
# Task closure

class TaskClosureBindings(ClosureBindings):
    __slots__ = ()
installConstructor(TaskClosureBindings)

class TaskClosureValue(ClosureValue, ActImpInt):
    __slots__ = ()
    make_bindings_class = TaskClosureBindings

    def tframes(self, agent, event, bindings, zexpr):
        b = self.make_bindings(agent, bindings, zexpr)
        #XXX needs a better name. update (kwc): using agent.nextid() now
        if b:
            name = "Closure.%s"%agent.nextid()
            return [TaskExprTFrame(name, event, b, self.closed_zexpr[1])]
        else:
            return []
        
installConstructor(TaskClosureValue)

class TaskClosureImp(ClosureImp):
    """A Pattern that evaluates to a TaskClosureValue"""
    __slots__ = ()
    evaluate_class = TaskClosureValue


class ApplyTask(Imp):
    """A Task expression that 'applies' a TaskClosureValue to parameters."""
    __slots__ = ()

    # This is Parallel, since we can't be sure of the order in which
    # the argument patterns are bound by the TaskClosure's
    # precondition.  This could be fixed by not passing in
    # 'non-parallel' components, instead passing in variables that get
    # matched to each 'non-parallel' component after the precondition
    # has bound it.

    def tenter(self, agent, tframe, zexpr):
        raise Unimplemented("Haven't fixed ApplyTask yet")
        oldbindings = tframe.getBaseBindings()
        closure_value = termEvalErr(agent, oldbindings, zexpr[0])
        closed_zexpr = closure_value.closed_zexpr
        bindings = closure_value.make_bindings(agent, oldbindings, zexpr[1:])
        event = PseudoGoalEvent(tframe, self)
        tframe._subgoal_event = event
        name = "%s.%s"%(tframe.name(), self.label())
        event.addTFrame(TaskExprTFrame(name, event, bindings, closed_zexpr))
        step_fn(agent, tframe, EXECUTING, zexpr)
        return tframe.tfpost_subgoal(agent, event)

    def tsubgoal_complete(self, agent, tframe, zexpr, subevent, result):
        if result is SUCCESS:
            step_fn(agent, tframe, SUCCEEDED, zexpr)
        else:
            step_fn(agent, tframe, FAILED, zexpr)
        return tframe.tfcompleted(agent, result)

################################################################
# FunClosure

class FunClosureBindings(ClosureBindings):
    __slots__ = ()

    def bformals(self, agent, bindings, zexpr, match):
        # Note that the formal parameters of a function closure are
        # listed as usage VARLIST to allow unannotated variables to be
        # treated as input.
        fzitem = self._closureValue.closed_zexpr[0]
        if not match:
            return self
        elif fzitem.varlist(agent, self, bindings, zexpr):
            return self
        else:
            return None

installConstructor(FunClosureBindings)

class FunClosureValue(ClosureValue, FunImpInt):
    __slots__ = ()
    make_bindings_class = FunClosureBindings

    def call(self, agent, bindings, zexpr):
        b = self.make_bindings(agent, bindings, zexpr)
        return termEvalErr(agent, b, self.closed_zexpr[1])

installConstructor(FunClosureValue)

class FunClosureImp(ClosureImp):
    __slots__ = ()
    evaluate_class = FunClosureValue

class ApplyFun(Imp):
    __slots__ = ()

    def call(self, agent, bindings, zexpr):
        funclosurevalue = termEvalErr(agent, bindings, zexpr[0])
        imp = agent.value_imp(funclosurevalue)
        result = imp.call(agent, bindings, zexpr[1:])
        if (result is None): raise AssertionError
        return result

################################################################

class PredClosureBindings(ClosureBindings):
    __slots__ = ()
installConstructor(PredClosureBindings)

class PredClosureValue(ClosureValue, PredImpInt):
    __slots__ = ()
    make_bindings_class = PredClosureBindings
    
    def solutions(self, agent, bindings, zexpr):
        b = self.make_bindings(agent, bindings, zexpr)
        if b:
            for x in predSolve(agent, b, self.closed_zexpr[1]):
                if b.bformals(agent, bindings, zexpr, False):
                    yield x
    def solution(self, agent, bindings, zexpr):
        b = self.make_bindings(agent, bindings, zexpr)
        if b:
            for x in predSolve(agent, b, self.closed_zexpr[1]):
                if b.bformals(agent, bindings, zexpr, False):
                    return SOLVED
        return NOT_SOLVED
    
    def conclude(self, agent, bindings, zexpr): # TODO: verify this
        b = self.make_bindings(agent, bindings, zexpr)
        if not (b): raise AssertionError
        predUpdate(agent, b,  self.closed_zexpr[1])

    def retractall(self, agent, bindings, zexpr): # TODO: verify this
        b = self.make_bindings(agent, bindings, zexpr)
        if not (b): raise AssertionError
        predRetractall(agent, b,  self.closed_zexpr[1])

installConstructor(PredClosureValue)

class PredClosureImp(ClosureImp):
    __slots__ = ()
    evaluate_class = PredClosureValue

class ApplyPred(Imp):
    __slots__ = ()

    def solution(self, agent, bindings, zexpr):
        predclosurevalue = termEvalErr(agent, bindings, zexpr[0])
        imp = agent.value_imp(predclosurevalue)
        return imp.solution(agent, bindings, zexpr[1:])

    def solutions(self, agent, bindings, zexpr):
        predclosurevalue = termEvalErr(agent, bindings, zexpr[0])
        imp = agent.value_imp(predclosurevalue)
        return imp.solutions(agent, bindings, zexpr[1:])

    def conclude(self, agent, bindings, zexpr):
        predclosurevalue = termEvalErr(agent, bindings, zexpr[0])
        imp = agent.value_imp(predclosurevalue)
        return imp.conclude(agent, bindings, zexpr[1:])

    def retractall(self, agent, bindings, zexpr):
        predclosurevalue = termEvalErr(agent, bindings, zexpr[0])
        imp = agent.value_imp(predclosurevalue)
        return imp.retractall(agent, bindings, zexpr[1:])
