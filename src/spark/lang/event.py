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
from spark.pylang.implementation import PredImpInt
from spark.internal.exception import LowError, SignalFailure
from spark.internal.repr.taskexpr import GoalEvent, PseudoGoalEvent, TaskExprTFrame, SUCCESS, TFrame
from spark.pylang.defaultimp import SparkEvent
from spark.internal.repr.procedure import ProcedureTFrame
#from spark.internal.repr.expr import Expr
from spark.internal.common import SOLVED

class EventPosted(PredImpInt):
    __slots__ = ()
    def __init__(self, symbol):
        pass
    def solutions(self, agent, bindings, zexpr):
        if len(zexpr) != 1:
            raise LowError("Expecting one argument to EventPosted")
        allPostedEvents = agent.allPostedEvents
        if allPostedEvents is None:
            return
        val = termEvalOpt(agent, bindings, zexpr[0])
        if val is None:
            for event in allPostedEvents:
                if termMatch(agent, bindings, zexpr[0], event):
                    yield SOLVED
        else:
            if event in allPostedEvents:
                yield True
#     def find_solutions(self, agent, bindings, zexpr):
#         if len(zexpr) != 1:
#             raise LowError("Expecting one argument to EventPosted")
#         allPostedEvents = agent.allPostedEvents
#         if allPostedEvents is None:
#             return
#         val = termEvalOpt(agent, bindings, zexpr[0])
#         if val is None:
#             for event in allPostedEvents:
#                 if termMatch(agent, bindings, zexpr[0], event):
#                     bindings.bfound_solution(agent, zexpr)
#         else:
#             if event in allPostedEvents:
#                 bindings.bfound_solution(agent, zexpr)
    def conclude(self, agent, bindings, expr):
        if len(zexpr) != 1:
            raise LowError("Expecting one argument to EventPosted")
        val = termEvalErr(agent, bindings, zexpr[0])
        if val not in agent.allPostedEvents:
            agent.post_event(val)


class RecordingAllEvents(PredImpInt):
    __slots__ = ()
    def __init__(self, symbol):
        pass
    
    def solution(self, agent, bindings, zexpr):
        if len(zexpr) != 0:
            raise LowError("Expecting no argument to RecordingAllEvents")
        allPostedEvents = agent.allPostedEvents
        if allPostedEvents is not None:
            return SOLVED
        else:
            return NOT_SOLVED

#     def find_solutions(self, agent, bindings, zexpr):
#         if len(zexpr) != 0:
#             raise LowError("Expecting no argument to RecordingAllEvents")
#         allPostedEvents = agent.allPostedEvents
#         if allPostedEvents is not None:
#             bindings.bfound_solution(agent, zexpr)

    def conclude(self, agent, bindings, zexpr):
        if len(zexpr) != 0:
            raise LowError("Expecting no argument to RecordingAllEvents")
        if agent.allPostedEvents is None:
            agent.allPostedEvents = []

    def retractall(self, agent, bindings, zexpr):
        if len(zexpr) != 0:
            raise LowError("Expecting no argument to RecordingAllEvents")
        agent.allPostedEvents = None

def testEventKind(event):
    if not (isinstance(event, SparkEvent)): raise AssertionError
    return event.eventKind

def testEventCompleted(event):
    if not (isinstance(event, GoalEvent)): raise AssertionError
    return event.result

def testSuccessResult(result):
    return result == SUCCESS

def testFailureResult(result):
    return isinstance(result, Failure)

def testEventParent(event):
    "Find the PI that is the parent of a GoalEvent"
    if isinstance(event, GoalEvent):
        tframe = event.e_sync_parent()
        tframe_parent_event = tframe.event()
        while isinstance(tframe_parent_event, PseudoGoalEvent):
            tframe = tf.tf_sync_parent()
            tframe_parent_event = tframe.event()
        return tframe
    else:
        return None

def testEventExpr(event):
    if not (isinstance(event, GoalEvent)): raise AssertionError
    return event.taskexpr()

def listPICurrentSubgoals(agent, tframe):
    # see also procedure_instance_subtasks
    if not (isinstance(tframe, TFrame)): raise AssertionError
    if not isinstance(tframe, TaskExprTFrame):
        return []
    subgoal = tframe.subgoal_event()
    if subgoal is None:
        return ()
    elif isinstance(subgoal, PseudoGoalEvent):
        result = ()
        for childtf in agent.tframe_children(tframe):
            result += listPICurrentSubgoals(agent, childtf)
        return result
    elif isinstance(subgoal, GoalEvent):
        return (subgoal,)
    else:
        raise LowError("Unexpected subgoal type: %r", subgoal)

def getPICurrentStep(agent, tframe):
    # see also procedure_instance_subtasks
    if not (isinstance(tframe, TFrame)): raise AssertionError
    if not isinstance(tframe, TaskExprTFrame):
        return None
    taskexprs = tframe.taskexprs
    if taskexprs:
        return taskexprs[-1]
    else:
        return None
    
def listPICurrentValues(agent, tframe):
    if not isinstance(tframe, TaskExprTFrame):
        return ()
    bindings = tframe.getBaseBindings()
    return bindings.getVariableValues(agent)

def testPIProcedure(pi):
    if isinstance(pi, ProcedureTFrame):
        return pi.procedure()
    else:
        return None

def parentChildExpr(pExpr, cExpr):
    if pExpr == None:
        if not (isinstance(cExpr, Expr)): raise AssertionError
        return (cExpr.parent(), cExpr)
    else:
        if not (isinstance(pExpr, Expr)): raise AssertionError
        if cExpr == None:
            return (pExpr, pExpr._components)
        else:
            return pExpr == cExpr.parent()
        
def listExprVariables(expr):
    if not (isinstance(expr, Expr)): raise AssertionError
    return expr.free_vars().elements()

################################################################

from spark.internal.repr.taskexpr import GoalEvent
from spark.pylang.defaultimp import AddFactEvent
def eventInputArguments(agent, event):
    if isinstance(event, GoalEvent):
        zexpr = event.getZexpr().components[0]
        bindings = event.getBindings()
    elif isinstance(event, AddFactEvent):
        zexpr = event.zexpr()
        bindings = event.bindings()
    else:
        return ("UNKNOWN",)
    result = []
    for i in range(zexpr.nargs()):
        val = zexpr.default(agent, bindings, i, None)
        if val is not None:
            result.append(val)
    return tuple(result)

from spark.internal.repr.taskexpr import INTERRUPT
def interruptProcedureInstance(agent, tframe):
    agent.terminate_children(tframe)
    tframe.tfterminated(agent)
    tframe.tf_set_completed(agent, SignalFailure(tframe, INTERRUPT))
