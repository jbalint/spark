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
from spark.internal.version import *
from spark.internal.common import DEBUG
from spark.pylang.defaultimp import ObjectiveEvent, MetaFactEvent, SparkEvent, Structure, AddFactEvent
from spark.pylang.implementation import ActImpInt, PredImpInt
from spark.internal.repr.varbindings import optBZ
from spark.internal.parse.usagefuns import termEvalEnd, entity
from spark.internal.parse.processing import StandardExprBindings


#from spark.internal.repr.predexpr import PredExpr
from spark.internal.repr.procedure import ProcedureTFrame, ProcedureValue
from spark.internal.repr.taskexpr import TFrame, GoalEvent, PseudoGoalEvent, SUCCESS, TaskExprTFrame, DoEvent#, TaskExpr, DoTaskExpr, AchieveTaskExpr
from spark.internal.parse.basicvalues import Symbol
from spark.internal.repr.common_symbols import P_Properties

#from spark.internal.parse.newparse import Module
from spark.internal.parse.basicvalues import installConstructor
from spark.internal.parse.usagefuns import *
    
debug = DEBUG(__name__)


objective_previous_arg = None
objective_previous_result = None

def objective(event_or_tframe):
    "Returns the top-level, object-level SparkEvent that triggered this event_or_tframe if there is one"
    
    debug("Objective - getting called")
    #note: caching is not thread safe, but we are currently single-threaded
    global objective_previous_arg, objective_previous_result
    if objective_previous_arg is not None and objective_previous_arg == event_or_tframe :
        #print "cache obj"
        debug("Objective - using cache")
        return objective_previous_result

    #clear cache (don't need to clear previous_result)
    objective_previous_arg = None
    
    if isinstance(event_or_tframe, SparkEvent):
        event = event_or_tframe
    elif isinstance(event_or_tframe, TFrame):
        event = event_or_tframe.event()
    else:
        raise Exception("Attempting to get the objective of something other than" \
                        " a tframe or event: %s"%event_or_tframe)
    while isinstance(event, GoalEvent):
        tf = event.e_sync_parent()
        if tf is None:
            #raise Exception(...)
            debug("Objective - goal event had no e_sync_parent %s", event)
            return None
        event = tf.event()
    if isinstance(event, MetaFactEvent):
        debug("Objective - meta-event")
        return None
    elif event is None:
        #raise Exception(...)
        debug("Objective - tframe had no event %s",tf)
        return None
        
    #cache result
    objective_previous_arg = event_or_tframe
    objective_previous_result = event
    debug("Objective - TRUE")
    return objective_previous_result

def task_id(task_event, id = None):
    if task_event == None:
        if id == None:
            raise LowError("At least one argument needs to be bound")
        else:
            from spark.pylang.defaultimp import id_event
            return (id_event(id), id)
    else:    
        if not (isinstance(task_event, SparkEvent)): raise AssertionError
        if id == None:
            return (task_event, task_event.objectId())
        else:
            if task_event.objectId() == id:
                return (task_event, id)
    return None

def tframe_id(tframe, id = None):
    if tframe == None:
        if id == None:
            raise LowError("At least one argument needs to be bound")
        else:
            from spark.internal.repr.taskexpr import id_tframe
            return (id_tframe(id), id)
    else:
        if not (isinstance(tframe, TFrame)): raise AssertionError
        if id == None:
            return (tframe, tframe.objectId())
        else:
            if tframe.objectId() == id:
                return (tframe, id)
    return None
            
def pi_procedure_name(pi):
    if not (isinstance(pi, ProcedureTFrame)): raise AssertionError
    return pi.procedure().name()

task_context_previous_arg = None
task_context_previous_result = None

def task_context(task_or_pi):
    "Returns the next task up"
    
    #cache - not thread safe
    global task_context_previous_arg, task_context_previous_result
    if task_context_previous_arg is not None and\
           task_context_previous_arg == task_or_pi:
        #print "cache tc"
        return task_context_previous_result
    # clear cache - don't need to reset previous_result
    task_context_previous_arg = None
    
    if isinstance(task_or_pi, SparkEvent):
        tframe = task_parent(task_or_pi)
    elif isinstance(task_or_pi, TFrame):
        # also handle arbitrary TFrame
        tframe = tframe_procedure_instance(task_or_pi)
    else:
        raise Exception("Attempting to get the task_context of something "\
                        "other than a tframe or event: %s"%task_or_pi)
    if tframe:
        task_context_previous_result = tframe.event()
        task_context_previous_arg = task_or_pi
        return task_context_previous_result
    else:
        return None


def task_parent(task_event):
    "Returns the parent procedure instance (tframe) of task_event"
    # cf. objective
    if isinstance(task_event, MetaFactEvent):
        return None
    tf = task_event.e_sync_parent()
    if tf is None:
        return None
    return tframe_procedure_instance(tf)
    
def tframe_procedure_instance(tframe):
    if not (isinstance(tframe, TaskExprTFrame)): raise AssertionError
    bindings = tframe.getBaseBindings()
    tf = tframe
    tf1 = tf.tf_sync_parent()
    while tf1 is not None \
              and isinstance(tf1, TaskExprTFrame) \
              and tf1.getBaseBindings() is bindings:
        tf = tf1
        tf1 = tf.tf_sync_parent()
    return tf

class GetSelfTaskTFrame(TFrame):
    __slots__ = ("bindings", "zexpr",)

    def __init__(self, name, event, bindings, zexpr):
        TFrame.__init__(self, name, event)
        self.bindings = bindings
        self.zexpr = zexpr

    def constructor_args(self):
        return TFrame.constructor_args(self) + [self.bindings, self.zexpr]
    constructor_mode = "VIIV"
    
    def tfcont(self, agent):
        result = task_context(self.event())
        if result is None:
            sf = MessageFailure(self, "GetSelfTask failed")
        elif not termMatch(agent, self.bindings, self.zexpr[0], result):
            sf = MessageFailure(self, "Result of GetSelfTask did not match output pattern")
        else:
            sf = SUCCESS
        self.tf_set_completed(agent, sf)
installConstructor(GetSelfTaskTFrame)

class GetSelfTask(ActImpInt):
    __slots__ = ()
    def __init__(self, symbol):
        pass
    def tframes(self, agent, event, bindings, zexpr):
        name = "GetSelfTask%d"%agent.nextid()
        return [GetSelfTaskTFrame(name, event, bindings, zexpr)]


getSelfTask = GetSelfTask

class GetSelfProcInstTFrame(TFrame):
    __slots__ = ("bindings", "zexpr",)

    def __init__(self, name, event, bindings, zexpr):
        TFrame.__init__(self, name, event)
        self.bindings = bindings
        self.zexpr = zexpr
    def constructor_args(self):
        return TFrame.constructor_args(self) + [self.bindings, self.zexpr]
    constructor_mode = "VIIV"
    
    def tfcont(self, agent):
        result = task_parent(self.event())
        if result is None:
            sf = MessageFailure(self, "GetSelfProcInst failed")
        elif not termMatch(agent, self.bindings, self.zexpr[0], result):
            sf = MessageFailure(self, "Result of GetSelfProcInst did not match output pattern")
        else:
            sf = SUCCESS
        self.tf_set_completed(agent, sf)
installConstructor(GetSelfProcInstTFrame)

class GetSelfProcInst(ActImpInt):
    __slots__ = ()
    def __init__(self, symbol):
        pass
    def tframes(self, agent, event, bindings, zexpr):
        name = "GetSelfProcInst%d"%agent.nextid()
        return [GetSelfProcInstTFrame(name, event, bindings, zexpr)]


getSelfProcInst = GetSelfProcInst

################################################################
# taskid_statement

def taskid_statement(taskid):
    return "<statement for %s>"%taskid

def taskid_successors(taskid):
    raise Unimplemented()

#
################################################################


def procedure_instance_subtasks(agent, pi_tframe):
    "Return a tuple of the current subtasks of procedure instance pi_tframe"
    result = []
    pis_aux(agent, pi_tframe, result)
    return tuple(result)

def pis_aux(agent, tframe, tframes):
    """Accumulate into tframes subgoals of all tframe descendants of tframe
    (including tframe) that have no children with the same bindings."""
    has_child_in_pi = False
    for tf in agent.tframe_children(tframe):
        # non-TaskExprTFrames don't have 'bindings' slor
        if isinstance(tf, TaskExprTFrame) and tf.getBaseBindings() is tframe.getBaseBindings():
            has_child_in_pi = True
            pis_aux(agent, tf, tframes)
            
    if not has_child_in_pi and isinstance(tframe, TaskExprTFrame):
        subtask = tframe.subgoal_event()
        # TODO: should this verify isinstance(subtask, GoalEvent)
        if subtask is not None:
            #print "FOUND SUBGOAL: ", subtask._tframe
            tframes.append(subtask)


########################################
# taskexpr_first_taskexprs
# taskexpr_next_taskexprs
# implemented as python functions that
# can be passed into a SimpleFun
########################################

# def _find_basic_tasks(taskexpr):
#     print "enter _find_basic_tasks(%r)"%taskexpr.label()
#     result = _find_basic_tasks1(taskexpr)
#     print "exit _find_basic_tasks(%r)=%r"%(taskexpr.label(), result)
#     return result
def _find_basic_tasks(taskexpr):
    """recursive routine that descends the taskexpr hierarchy to find the
    basic tasks"""

    #reached bottom without finding anything
    if taskexpr is None:
        return []
        
    #found a basic task
    if isinstance(taskexpr, DoTaskExpr) or isinstance(taskexpr, AchieveTaskExpr):
        return [taskexpr]

    #most likely the predicate part of a select, examine the next expr
    if not isinstance(taskexpr, TaskExpr):
        return _find_basic_tasks(taskexpr.next)

    #descend the children of the expr by looking at the startpoints()
    #startpoints is a list of expressions that come first in the hierarchy
    startpoints = taskexpr.startpoints()
    if startpoints == []:
        # look at next
        return find_next_taskexpr(taskexpr)

    #build solution set based on child exprs
    solns = []
    for child in startpoints:
        solns.extend(_find_basic_tasks(child))

    return solns

def _find_task(parenttaskexpr, tasklabel):
    """recursive routine that descends the taskexpr hierarchy to find 
    a task with the specified task label"""
    if parenttaskexpr is None:
        return None
        
    #found a basic task, check for label match
    if isinstance(parenttaskexpr, DoTaskExpr) or isinstance(parenttaskexpr, AchieveTaskExpr):
        if tasklabel == parenttaskexpr.label():
            return parenttaskexpr

    #most likely the predicate part of a select, examine the next expr
    if isinstance(parenttaskexpr, PredExpr):
        return _find_task(parenttaskexpr.next, tasklabel)

    #descend the task tree by looking at the startpoints()
    startpoints = parenttaskexpr.startpoints()
    if startpoints is None:
        return None

    #see if expr is in the subtree
    for child in startpoints:
        found = _find_task(child, tasklabel)
        if found is not None:
            return found

    if parenttaskexpr.next is not None:
        return _find_task(parenttaskexpr.next, tasklabel)
    else:
        return None
        
def find_first_taskexpr(taskexpr):
    """solve the function for taskexpr_first_taskexprs, which
    returns the first task expression of the taskexpr"""
    #process arguments
    if (taskexpr is None): raise AssertionError
    if not (isinstance(taskexpr, TaskExpr)): raise AssertionError
        
    return _find_basic_tasks(taskexpr)

# def find_next_taskexpr(taskexpr):
#     print "enter find_next_taskexpr(%r)"%taskexpr.label()
#     result = find_next_taskexpr1(taskexpr)
#     print "exit find_next_taskexpr(%r)=%r"%(taskexpr.label(), result)
#     return result
    
def find_next_taskexpr(taskexpr):
    """solve the function for taskexpr_next_taskexprs, which
    returns the next expression after the taskexpr"""
    #process arguments
    if (taskexpr is None): raise AssertionError
    if not (isinstance(taskexpr, TaskExpr)): raise AssertionError
        
    if taskexpr.next is None:
        #need to go to parent expr and move on to its next
        parent = taskexpr.parent()
        if (parent is None) \
               or not isinstance(parent, TaskExpr): # top parent is procedure
            return []
        else:
            return find_next_taskexpr(parent)#_find_basic_tasks(parent.next)
    else:
        return _find_basic_tasks(taskexpr.next)

def get_pi_body(proc_instance):
    return proc_instance.procedure().closure_value.closed_zexpr.keyget0("body:")


############################################################
# ProcInstTaskExprTaskId $pi $taskexpr $taskid)
############################################################

#  # DNM - CHANGE TO objectId
def taskIdForSubTask(procinstid, tasklabel):
    if not (isinstance(procinstid, basestring)): raise AssertionError
    if not (isinstance(tasklabel, basestring)): raise AssertionError
    return "%s|%s"%(procinstid, tasklabel)

#  class PITIdPred(PredImpInt):
#      __slots__ = ("_symbol",)
    
#      def __init__(self, symbol):
#          self._symbol = symbol

#      def find_solutions(self, agent, bindings, zexpr):
#          pi = termEvalOpt(agent, bindings, zexpr[0])
#          taskexpr = termEvalOpt(agent, bindings, zexpr[1])
#          if pi is not None and taskexpr is not None:
#              taskid = taskIdForSubTask(pi.name(),expr.label())
#              if termMatch(agent, bindings, zexpr[2], taskid):
#                  bindings.bfound_solution(agent, zexpr)
#          else:
#              taskid = termEvalErr(agent, bindings, zexpr[2])
#              split = taskid.split('|')
#              if (len(split) != 2): raise AssertionError
#              proc_inst_id = split[0]
#              proc_instance = id_tframe(proc_inst_id)
#              if termMatch(agent, bindings, zexpr[0], proc_instance):
#                  taskexpr_label = split[1]
#                  procexpr = get_pi_body(proc_instance)
#                  taskexpr = _find_task(procexpr, taskexpr_label)
#                  if termMatch(agent, bindings, zexpr[1], taskexpr):
#                      bindings.bfound_solution(agent, zexpr)

            
################################################################
def procedure_module(procedure):
    if isinstance(procedure, ProcedureValue):
        return procedure.closed_zexpr.getSPU()
    return False

def task_module(doevent):
    if isinstance(doevent, DoEvent):
        return doevent.goalsym().modname
    return False

def get_procedure_from_tframe(tframe):
    if isinstance(tframe, ProcedureTFrame):
        return tframe._procedure
    return False

def module_name(module):
    from spark.internal.parse.processing import SPU
    if isinstance(module, SPU):
        return module.get_modpath().name
    return False

def procedure_packagename(procedure):
    if isinstance(procedure, ProcedureValue):
        return procedure.closed_zexpr.getSPU()._currentPackageName
    return False

################################################################
def failValue(failure):
    "Tests whether a failure is a FailFailure and returns the value specified"
    from spark.internal.exception import FailFailure
    return isinstance(failure, FailFailure) and failure.getFailureValue()

################################################################
#def getTaskParent(tframe):
#    if isinstance(tframe._parent, TaskExprTFrame):
#        name = tframe._parent.cvname()
#        if name [0] == "|":
#            name = name[1:-1]
#        return name
#    return False

def getProcedureName(tframe):
    if isinstance(tframe, ProcedureTFrame):
        name = tframe.cvname()
        if name [0] == "|":
            name = name[1:-1]
        return name
    return False

def getTaskName(task):
    if not isinstance(task, DoEvent):
        return False
    return str(task._symbol)

def getTaskParentName(tframe):
    parentname = ""
    if isinstance(tframe, DoEvent):
        parentname = tframe._tframe.name()
    elif isinstance(tframe, TaskExprTFrame):
        tframe_parent_event = tframe.event()
        if isinstance(tframe_parent_event, GoalEvent):
            parentname = tframe_parent_event._tframe.name()
    return parentname

def getTaskParentID(tframe):
    parentname = ""
    if isinstance(tframe, DoEvent):
        parentname = tframe._tframe.objectId()
    elif isinstance(tframe, TaskExprTFrame):
        tframe_parent_event = tframe.event()
        if isinstance(tframe_parent_event, GoalEvent):
            parentname = tframe_parent_event._tframe.objectId()
    return parentname

def getInputGoalParameters(agent, event):
    return getGoalParameters(agent, event, False)

def getOutputGoalParameters(agent, event):
    return getGoalParameters(agent, event, True)

def getGoalParameters(agent, doevent, type):
    #type=False for input parameters. type=True for output parameters
    if isinstance(doevent, GoalEvent):
        solutions = solve(agent, "spark.lang.builtin.ArgNames",[doevent._symbol, None])
        keys = solutions[0][1]
        invalues = doevent.getArgs(agent)
        args = []
        if type:
            allvalues = doevent.getTaskResultArgs(agent)
            for i in range(len(keys)):
                if (invalues[i] is None) and (allvalues[i] is not None):
                    args.append(("$" + keys[i], allvalues[i]))
        else:
            for i in range(len(keys)):
                if invalues[i] is not None:
                    args.append(("$" + keys[i], invalues[i]))
        return tuple(args)
    return False

def getPredicateParameters(agent, fact):
    #type=False for input parameters. type=True for output parameters
    if isinstance(fact, AddFactEvent):
        solutions = solve(agent, "spark.lang.builtin.ArgNames",[fact._symbol, None])
        keys = solutions[0][1]
        #print "Binding type is %s and keys are %s."%(fact.bindings()[0], keys)
        args = []
        binding = fact.getArgs(agent)
        for i,key in enumerate(keys):
            args.append(("$" + key, binding[i]))
        return tuple(args)
    return False

def getProcedureFeatures(agent, tframe):
    if isinstance(tframe, ProcedureTFrame):
        return tframe.features(agent)
    return False

# A way to access the knowledgebase.
# Given a predicate name and its parameters, it returns a list of solutions.
def solve(agent, predString, argList):
    imp = agent.getImp(Symbol(predString))
    b, z = optBZ(argList)
    solutions = []
    for solved in imp.solutions(agent, b, z):
        if solved:
            solutions.append([termEvalEnd(agent, b, zi) for zi in z])
    return tuple(solutions)

def getIntentions(agent):
    intentions = agent.get_intentions()
    intentions_list = []
    for intent in intentions:
        if isinstance(intent, ProcedureTFrame):
            intentions_list.append(intent.cvname())
        else:
            intentions_list.append(intent.name())
    return tuple(intentions_list)
    
def isIntended(agent, intention):
    return intention in getIntentions(agent)

_NULL_BINDINGS = StandardExprBindings()

def procInstSymbol(agent, tframe):
    if not isinstance(tframe, ProcedureTFrame):
        return None
    procedure = tframe.procedure()
    if not isinstance(procedure, ProcedureValue): # maybe just ProcClosureValue 
        return None
    zexpr = procedure.closed_zexpr
    name = entity(agent, _NULL_BINDINGS, zexpr[0])
    return name
