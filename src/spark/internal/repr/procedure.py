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
#* "$Revision:: 344                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from __future__ import generators
from spark.internal.version import *
from spark.internal.exception import Unimplemented

from spark.internal.repr.closure import ClosureBindings, ClosureValue, ClosureImp
from spark.internal.repr.taskexpr import TaskExprTFrame, SUCCESS
from spark.internal.repr.common_symbols import PROCEDURE_STARTED, PROCEDURE_FAILED, \
     PROCEDURE_SUCCEEDED, PROCEDURE_STARTED_SYNCHRONOUS

from spark.pylang.defaultimp import MetaFactEvent
from spark.internal.common import ABSTRACT, DEBUG, SOLVED, NOT_SOLVED

from spark.internal.parse.basicvalues import ConstructibleValue, installConstructor, Variable, EMPTY_SPARK_LIST, List
from spark.internal.parse.usagefuns import *
from spark.internal.parse.processing import SPUBindings, matchValueToConstraint
from spark.util.logger import get_sdl

debug = DEBUG(__name__)#.on()

################################################################

class ProcedureInt(object):
    __slots__ = ()
    def append_tframes(self, agent, event, bindings, zexpr, list):
        raise Unimplemented()
    def name(self):
        raise Unimplemented()


class ProcClosureBindings(ClosureBindings): # used by {proc [<args] ...}
    __slots__ = ()

    def rebindVariables(self, agent):
        vdict = self._variables
        for varname in vdict:
            if isinstance(varname, basestring): # constraint
                value = vdict.get(Variable(varname))
                if value is not None:
                    con = vdict[varname]
                    matchValueToConstraint(agent, value, con, False)

installConstructor(ProcClosureBindings)

class ProcedureBindings(ProcClosureBindings): # used by {defprocedure ...}
    __slots__ = ()

    def bformals(self, agent, bindings, zexpr, match):
        # non-standard
        fzitem = self._closureValue.closed_zexpr.keyget0("cue:")[0][0]
        if formals(agent, self, fzitem, bindings, zexpr, match):
            #print "cue matched", fzitem, self._variables
            return self
        else:
            return None

installConstructor(ProcedureBindings)

class ProcClosureValue(ClosureValue, ProcedureInt): # value of {proc [<args] ...}
    __slots__ = (
        "_features",
        )

    IS_SYNCHRONOUS = True               # All synchronous for now

    make_bindings_class = ProcClosureBindings

    def __init__(self, captured, closed_zexpr):
        ClosureValue.__init__(self, captured, closed_zexpr)
        self._features = None

    def isSynchronous(self, agent, bindings):
        return self.IS_SYNCHRONOUS
        
    def getFeatures(self, agent):
        features = self._features
        if features is None:
            fzexpr = self.closed_zexpr.keyget0("features:")
            if fzexpr:
                bindings = SPUBindings(agent, fzexpr.getSPU())
                features = termEvalErr(agent, bindings, fzexpr)
            else:
                features = EMPTY_SPARK_LIST
            self._features = features
        return features
        
    def name(self):
        return str(self.closed_zexpr[0])

    cvcategory = "P"
    def cvname(self):
        return str(self.name())

#     def symbol(self):
#         # DNM - Yes, this is a revolting hack
#         try:
#             #return self.closed_expr.term[2][1][0][1][0].data
#             return self.closed_expr.term[2][1][0][1].symbol()
#         except AttributeError:          # for {proc [...] ...}
#             return None

    def append_tframes(self, agent, event, bindings, zexpr, list):
        b = self.make_bindings(agent, bindings, zexpr)
        if not b:                       # formals do not match
            return
        precondexpr = self.closed_zexpr.keyget0("precondition:")
        debug(" ProcedureValue.append_tframes - precondition %r", precondexpr)
        #from spark.internal.common import mybreak; mybreak()
        taskexpr = self.closed_zexpr.keyget0("body:")
        synchronous = self.isSynchronous(agent, b)
        if precondexpr:  # TODO: and not precondexpr.functor == S_True
            for x in predSolve(agent, b, precondexpr):
                debug(" ProcedureValue.append_tframes solution")
                if x:
                    name = "%s.%d"%(self.name(), agent.nextid())
                    tf = ProcedureTFrame(name, event, b.copy(), taskexpr, self, synchronous)
                    list.append(tf)
        else:
            name = "%s.%d"%(self.name(), agent.nextid())
            tf = ProcedureTFrame(name, event, b, taskexpr, self, synchronous)
            list.append(tf)
            
#     def append_tframes(self, agent, event, bindings, zexpr, list):
#         b = self.make_bindings(agent, bindings, zexpr)
#         #print " appending tframes", self.closed_expr.precondexpr
#         agent.push(list)
#         agent.push(event)
#         agent.push(self)
#         try:
#             self.closed_expr.precondexpr.compute(agent, b)
#         finally:
#             agent.pop_check(self)
#             agent.pop_check(event)
#             agent.pop_check(list)
        
#     def compute(self, agent, bindings): # used by append_tframes
#         #print "  found a match", bindings
#         event = agent.get(0)
#         solutions = agent.get(1)
#         name = "%s.%d"%(self.name(), agent.nextid())
#         taskexpr = self.closed_expr.taskexpr
#         tf = ProcedureTFrame(name, event, bindings.copy(), taskexpr, self)
#         solutions.append(tf)

installConstructor(ProcClosureValue)

class ProcedureValue(ProcClosureValue): # value inserted by {defprocedure ...}
    __slots__ = ()

    make_bindings_class = ProcedureBindings

    def isSynchronous(self, agent, bindings):
        cueexpr = self.closed_zexpr.keyget0("cue:")[0]
        return bindings.bImp(agent, cueexpr).synchronous

installConstructor(ProcedureValue)

################################################################
# Support for ProcedureClosures

class ProcClosureImp(ClosureImp):
    """A Pattern that evaluates to a ProcedureValue"""
    __slots__ = ()
    evaluate_class = ProcClosureValue

################################################################
# ProcedureExpr

def tframe_roles(agent, tframe):
    return tframe.roles(agent)

class ProcedureTFrame(TaskExprTFrame):
    __slots__ = (
        "_procedure",                   # ProcedureValue
        #"_started",
        "_cached_roles",
        "_synchronous",
        )

    def cvname(self):
        return self._procedure.name()

    def __init__(self, name, event, bindings, taskexpr, procedure, synchronous):
        self._procedure = procedure
        self._synchronous = synchronous
        TaskExprTFrame.__init__(self, name, event, bindings, taskexpr)
        #self._started = False
        self._cached_roles = None

    def tf_is_sync(self):
        if self._synchronous:
            return TaskExprTFrame.tf_is_sync(self)
        else:
            return None

    def constructor_args(self):
        args = TaskExprTFrame.constructor_args(self)
        return args + [self._procedure, int(self._synchronous)]
    constructor_mode = "VIIVII"

    def features(self, agent):
        return self._procedure.getFeatures(agent)

    def roles(self, agent):
        if self._cached_roles != None:
            return self._cached_roles
        roles_expr = self._procedure.closed_zexpr.keyget0("roles:")
        if roles_expr is None:
            roles = EMPTY_SPARK_LIST
        else:
            bindings = self.getBaseBindings()
            oldroles = quotedEval(agent, self.getBaseBindings(), roles_expr)
            # get variable bindings for the moment
            roles = List([r.functor.structure(bindings.getVariableValue(agent, r[0])) for r in oldroles])
#         roles = ()
#         for roles_expr in self._procedure.closed_expr.roles_exprs:
#             roles = roles + termEvalErr(agent, self.bindings, roles_expr.sub_expr())
        self._cached_roles = roles
        return roles

    def rebind_parameters(self, agent):
        "Redo any bindings needed for intending this tframe"
        # This should remtach any parameters that have been bound (and
        # were not evaluable)
        self.getBaseBindings().rebindVariables(agent)

    def procedure(self):
        return self._procedure

    def tfcont(self, agent):
        return TaskExprTFrame.tfcont(self, agent)                            

    def tf_set_completed(self, agent, result):
        if result is SUCCESS:
            # TODO: should run bindings.bformals to evaluate formals and match actual output params
            # This will allow the MinusPrefix hack to be fixed
            agent.post_event(ProcedureSucceededEvent(self))
        else:
            agent.post_event(ProcedureFailedEvent(self, result))
        TaskExprTFrame.tf_set_completed(self, agent, result)

installConstructor(ProcedureTFrame)

# class ProcedureClosureImp(ClosureImp):
#     """A Pattern that evaluates to a ProcedureValue"""
#     __slots__ = ()
#     evaluate_class = ProcedureValue


class ProcedureEvent(MetaFactEvent):
    __slots__ = ()
    def base_tframe(self):      # make synchronous
        return self._fact[0]

class ProcedureStartedEvent(ProcedureEvent):
    __slots__ = ()
    def __init__(self, *args):
        ProcedureEvent.__init__(self, *args)
        from spark.lang.meta_aux import getProcedureName
        get_sdl().logger.debug("Procedure Started: %s", getProcedureName(args[0]))
        
    numargs = 1
    event_type = PROCEDURE_STARTED
    constructor_mode = "I"
installConstructor(ProcedureStartedEvent)

class ProcedureSucceededEvent(ProcedureEvent):
    __slots__ = ()
    def __init__(self, *args):
        ProcedureEvent.__init__(self, *args)
        from spark.lang.meta_aux import getProcedureName
        get_sdl().logger.debug("Procedure Succeeded: %s", getProcedureName(args[0]))

    numargs = 1
    event_type = PROCEDURE_SUCCEEDED
    constructor_mode = "I"
installConstructor(ProcedureSucceededEvent)

class ProcedureFailedEvent(ProcedureEvent):  
    __slots__ = ()
    def __init__(self, *args):
        ProcedureEvent.__init__(self, *args)
        from spark.lang.meta_aux import getProcedureName
        reason = str(args[1].getFailureValue())            
        get_sdl().logger.debug("procedure failed [%s]...\n\treason: %s", getProcedureName(args[0]), reason)
        
    numargs = 2
    event_type = PROCEDURE_FAILED
    constructor_mode = "IV"
installConstructor(ProcedureFailedEvent)

################################################################
################################################################

class AdviceClosureBindings(ClosureBindings):
    __slots__ = ()
    def bformals(self, agent, bindings, zexpr, match):
        # non-standard
        if not match:
            return self
        expr = self._closureValue.closed_zexpr
        fzitem = (expr[2], expr[4])
        if expr[2].varlist(agent, self, bindings, zexpr[0]) \
               and expr[4].varlist(agent, self, bindings, zexpr[1]):
            return self
        else:
            return None

installConstructor(AdviceClosureBindings)

from spark.pylang.implementation import PredImpInt
class AdviceClosureValue(ClosureValue, PredImpInt):
    __slots__ = ()
    make_bindings_class = AdviceClosureBindings
    
    def solutions(self, agent, bindings, zexpr):
        b = self.make_bindings(agent, bindings, zexpr)
        closed_zexpr = self.closed_zexpr
        if b:
            for x in predSolve(agent, b, closed_zexpr[3]):
                for y in predSolve(agent, b, closed_zexpr[5]):
                    #if b.bformals(agent, bindings, zexpr, False): # no need to check
                    yield y
    def solution(self, agent, bindings, zexpr):
        b = self.make_bindings(agent, bindings, zexpr)
        closed_zexpr = self.closed_zexpr
        if b:
            for x in predSolve(agent, b, closed_zexpr[3]):
                if predSolve1(agent, b, closed_zexpr[5]):
                    #if b.bformals(agent, bindings, zexpr, False):
                        return SOLVED
        return NOT_SOLVED
    

installConstructor(AdviceClosureValue)

class AdviceClosureImp(ClosureImp):
    __slots__ = ()
    evaluate_class = AdviceClosureValue
