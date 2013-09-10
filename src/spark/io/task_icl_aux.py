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

import re

from spark.internal.version import *
from spark.internal.common import NEWPM

from spark.internal.repr.taskexpr import DoEvent, GoalSucceededEvent, GoalFailedEvent
import types
from spark.internal.parse.basicvalues import Symbol, isSymbol, BACKQUOTE_SYMBOL, value_str, Structure, isStructure
from spark.internal.repr.taskexpr import TFrame, id_tframe, TaskExprTFrame, GoalEvent, SUCCESS, PseudoGoalEvent, find_do_tframes
#from spark.internal.repr.varbindings import DictBindings

#from spark.internal.engine.agent import Sentinel

from spark.lang.meta_aux import tframe_procedure_instance, procedure_instance_subtasks

from spark.pylang.simpleimp import BasicImpTFrame
from spark.pylang.defaultimp import ObjectiveEvent
# java-based imports for intention structure -> oaa icl
try:
    from java.util import ArrayList
except ImportError:
    print "SPARK is not running under Jython.  ICL-based meta predicates will not function"
    #raise ImportError("SPARK is not running under Jython.  ICL-based meta predicates will not function")
try:
    from com.sri.oaa2.icl import IclStr, IclList, IclTerm, IclStruct
except ImportError:
    print "Cannot import OAA Java packages.  ICL-based meta predicates will not function"
    #raise ImportError("Cannot import OAA Java packages.  ICL-based meta predicates will not function")



# mode = None - use standard mode, and use constant for evaluables
class Meth(object):
    __slots__ = (
        #"evaluate_if_possible",
        "use_parent_bindings",
        )
    
    def __init__(self, use_parent_bindings):
        #self.evaluate_if_possible = evaluate_if_possible
        self.use_parent_bindings = use_parent_bindings

    def recurse_components(self, agent, bindings, patexpr, mode):
        return [self.recurse(agent, bindings, c, mode) \
                for c in patexpr]

    def recurse(self, agent, bindings, patexpr, mode):
        if not isinstance(patexpr, Pat):
            return self.unhandleable(agent, bindings, patexpr)
        # If the patexpr has a value, find it
        if mode is None:       # Use standard mode for this expression
            if patexpr.evalpx(agent, bindings):
                value = termEvalErr(agent, bindings, patexpr)
            else:
                value = None
        else:                   # Use special mode for this expression
            if patexpr.evaluable_given(mode):
                if patexpr.evalpx(agent, bindings):
                    value = termEvalErr(agent, bindings, patexpr)
                else:
                    value = termEvalEnd(agent, bindings, patexpr)
            else:
                value = None
        if isinstance(patexpr, NonAnonVarPatExpr):
            acc = patexpr.accessor
            if value is not None:
                return self.ground(acc.name, value)
            elif isinstance(acc,FirstBivarAccessor) \
                     and self.use_parent_bindings:
                newb = bindings.pat_bindings
                try:
                    newe = bindings.pat_zexpr[acc.bivar_index]
                except AttributeError:
                    return self.nonground(acc.name)
                return self.recurse(agent, newb, newe, None)
            else:
                return self.nonground(acc.name)
        elif value is not None:
            return self.constant(value)            
        elif isinstance(patexpr, ListPatExpr):
            elements = self.recurse_components(agent, bindings, patexpr, mode)
            return self.list(tuple(elements))
        elif isinstance(patexpr, CompoundPatExpr):
            args = self.recurse_components(agent, bindings, patexpr, mode)
            return self.struct(patexpr.funsym, tuple(args))
        elif isinstance(patexpr, AnonVarPatExpr):
            return self.anon(patexpr.name)
        elif isinstance(patexpr, ConstantPatExpr):
            return self.constant(patexpr.get_value())
        elif not isinstance(patexpr, PatExpr): # a funny zexpr thing
            return self.anon('$_')
        else:
            return self.unhandleable(self, agent, bindings, patexpr)

    # Redefine the following to get different behavior
    def struct(self, functor_sym, args):
        return Structure(functor_sym, args)
    def list(self, elements):
        return tuple(elements)
    def constant(self, value): # constant or (value if evaluate_if_possible)
        return BACKQUOTE_SYMBOL.structure(value)
    def ground(self, name, value):      # bound variable 
        return Symbol(name)
    def nonground(self, name):          # variable not bound to ground value
        return Symbol(name)
    def anon(self, name="$_"):
        return Symbol(name)
    def unhandleable(self, agent, bindings, patexpr):
        raise Exception("Cannot handle %s"%patexpr)

def makeIclStruct(functor_name, args):
    from spark.io.oaa import ArrayList, IclStruct
    al = ArrayList(len(args))
    for elt in args:
        al.add(elt)
    return IclStruct(functor_name, al)

def makeIclList(elements):
    from spark.io.oaa import ArrayList, IclList
    al = ArrayList(len(elements))
    for elt in elements:
        al.add(elt)
    return IclList(al)
    
def makeIclStr(string):
    from spark.io.oaa import IclStr
    return IclStr(string)

class ICLConverter(Meth):
    __slots__ = ()
    
    def __init__(self, agent):
        Meth.__init__(self, True)
        
    def struct(self, functor_sym, args):
        return makeIclStruct(functor_sym.name, args)

    def list(self, elements):
        return makeIclList(elements)

    def constant(self, value):
        return self.value_to_icl(value)

    def ground(self, name, value):
        return self.value_to_icl(value)

    def nonground(self, name):
        from spark.io.oaa import IclVar
        return IclVar(re.sub("[$]", "_", name))

    def anon(self, name):
        return IclVar("_")

    def value_to_icl(self, value):
        from spark.io.oaa import InvalidTermError, value_to_icl
        try:
            return value_to_icl(value)
        except InvalidTermError:
            errid = NEWPM.displayError()
            result = "<NO ICL EQUIVALENT:%s>"%value_str(value)
            return value_to_icl(result)

def do_task_icl(agent, bindings, patexprs, kind, action_symbol, mode):
    from spark.io.oaa import IclVar
    # assume OAA name of task is the symbol absname
    oaa_action_name = action_symbol.name
    con = ICLConverter(agent)
    targs = []
    for patexpr in patexprs:
        if patexpr is None:
            icl = IclVar("_")
        elif isinstance(patexpr, Pat):
            icl = con.recurse(agent, bindings, patexpr, mode)
        else:
            icl = con.value_to_icl(patexpr)
        targs.append(icl)
    return makeIclStruct("task", \
                         [makeIclStr(kind), \
                          makeIclStr(oaa_action_name), \
                          makeIclList(targs), \
                          makeIclList(())])

def task_icl_mode(agent, task, mode):
    try:
        kind = task.kind_string()
        namesym = task.goalsym()
        bindings = task.getBindings()
        patexprs = task.getZexpr()
        if not (isinstance(kind, basestring)): raise AssertionError
        if not (isSymbol(namesym)): raise AssertionError
    except AnyException:
        errid = NEWPM.displayError()
        return makeIclStr("<cannot handle task %s>"%task)
    try:
        return do_task_icl(agent, bindings, patexprs, kind, namesym, mode)
    except AnyException:
        errid = NEWPM.displayError()
        return "<err: %s>"%task

def task_icl_0(agent, task):
    return task_icl_mode(agent, task, NO_VARS_BOUND)

task_icl_previous_arg = None
task_icl_previous_result = None

def task_icl(agent, task):
    global task_icl_previous_arg, task_icl_previous_result
    if task_icl_previous_arg is not None and \
           task_icl_previous_arg[0] == agent and \
           task_icl_previous_arg[1] == task:
        #print "cache ticl"
        return task_icl_previous_result
    
    #clear cache
    task_icl_previous_arg = None
    
    task_icl_previous_result = task_icl_mode(agent, task, None)
    # set cache - important to wait until after task_icl_mode
    # completes
    task_icl_previous_arg = (agent, task)
    return task_icl_previous_result

def task_icl_done(agent, task):
    return task_icl_mode(agent, task, ALL_VARS_BOUND)
    



################################################
# intention structure -> icl routines
################################################
            
def _sbi_list_arraylist(list):
    """convert a python list to an arraylist.  subroutine for
    _sub_build_intentions_icl"""
    al  = ArrayList()
    for el in list:
        al.add(el)
    return al

# subroutine for _sub_build_intention_icl
# pi rep omits the subtasks slot so that it can be set later
# task is the event for the pi. pi_name is the string name/id
# of the procedure instance.
def _sbi_pi_arraylist_rep(agent, task, pi_name):
    """generate icl representation for a tframe, return ArrayList"""

    task_id = IclStruct('task_id', IclStr(task.name())) # DNM - CHANGE TO objectId
    task_icl_rep = task_icl(agent, task)
    procedure_name = IclStruct('procedure', IclStr(pi_name))
    return [task_id, task_icl_rep, procedure_name]

def _sbi_task_icl_rep(agent, task, pi_name):
    """generate icl representation for a task with no tframe,
    return IclList.  subroutine for _sub_build_intention_icl"""
    
    #assert(task._tframe is None)
    event_icl_list = _sbi_pi_arraylist_rep(agent, task, pi_name)
    #return intention with no subtasks
    return IclStruct('intention', event_icl_list[0], \
                     event_icl_list[1], event_icl_list[2], \
                     IclList(ArrayList()))
    
def _sub_build_intention_icl(agent, tframe):
    """builds the IclList representation of a single
    intention/taskexprtframe.  subroutine of
    build_intention_icl"""

    ##################################################
    # locals:
    # intention_rep: holds the list representation
    #    of the the intention as it is being constructed.
    #    it has all of the IclStruct params except the subtasks
    # subtask_list: holds a list of IclLists that represent subtasks
    # subtasks: list of the subevents of the current tframe
    # tframe_children: list of child tframes according to the agent
    ##################################################
    
    ##################################################
    # setup the intention representation, if necessary
    ##################################################

    intention_rep = None
    #print "current tframe", tframe.name(), tframe.__class__.__name__
    if isinstance(tframe, TaskExprTFrame) and not isinstance(tframe.event(), PseudoGoalEvent):
        name = tframe_procedure_instance(tframe).name()
        intention_rep = _sbi_pi_arraylist_rep(agent, tframe.event(), name)
        #note: at this point, we still need to fill in the children slot

    ##################################################
    # build list of sub-tasks
    ##################################################
    
    subtask_list = []
    # - traverse goals w/o pi's first
    subtasks = procedure_instance_subtasks(agent, tframe)
    for task in subtasks:
        #print "examining task: ", task.name(), task.__class__.__name__, task._tframe
        
        # look for tasks that don't have a tframe yet and
        # add their descriptions
        if isinstance(task, GoalEvent) and (task._tframe is None or isinstance(task._tframe, BasicImpTFrame)):
            # currently signify no proc with an empty stringx
            # appends an IclList
            subtask_list.append(_sbi_task_icl_rep(agent, task, ""))

    # - traverse tframe children 
    tframe_children = agent.tframe_children(tframe)
    for child in tframe_children:
        #print "examining frame: ", child.name()
        subtree = _sub_build_intention_icl(agent, child)
        if subtree is not None:
            subtask_list.extend(subtree)

    ##################################################
    # compute return value
    ##################################################

    # if we have a taskexpr tframe (intention_rep not None),
    # put the subtask list into the children slot
    if intention_rep is not None:
        subtask_arraylist = _sbi_list_arraylist(subtask_list)
        return [IclStruct('intention', intention_rep[0], \
                          intention_rep[1], intention_rep[2],
                          IclList(subtask_arraylist))]
    # we don't have a taskexpr tframe, but still include the task children in the
    # icl representation
    else:
        return subtask_list

def build_intention_icl(agent):
    """builds an IclList representation of the agent's current intention
    structure.  this representation only includes task tframes and their
    associated goals/tasks"""

    intentions = ArrayList()
    intention_structure = agent._intention_structure
    for root in intention_structure.get_root_tframes():
        tree = _sub_build_intention_icl(agent, root)
        for iclstruct in tree:
            if not (isinstance(iclstruct, IclStruct)): raise AssertionError
            intentions.add(iclstruct)
    return IclList(intentions)

################################################################

# Construct event

def createObjective(agent):
    "Create an event"

def postObjective(agent, objective):
    agent.post_event(objective)
    return True

def objective_result(objective):
    return objective.result()

class COEvent(ObjectiveEvent):
    __slots__ = (
        "_result",
        "_expr",
        "_bindings",
        "_symbol",
        )
    
    name_base = "COEvent"
    
    def __init__(self, task_icl):
        from spark.io.oaa import icl_to_value, iterator_to_zexpr
        ObjectiveEvent.__init__(self, None)
        if not (isinstance(task_icl, IclStruct)): raise AssertionError
        if (task_icl.iclFunctor() != "task"): raise AssertionError
        if (task_icl.size() != 4): raise AssertionError
        [ikind_string, iact_name, itask_args, imods] = [x for x in task_icl.iterator()]
        if (icl_to_value(ikind_string) != "Do"): raise AssertionError
        if not (isinstance(iact_name, IclStr)): raise AssertionError
        act_name = icl_to_value(iact_name)
        self._symbol = Symbol(act_name)
        if not (isinstance(itask_args, IclList)): raise AssertionError
        self._expr = iterator_to_zexpr(itask_args.listIterator())
#         from spark.symbol import Symbol, isSymbol
#         self._symbol = Symbol("spark.common.print")
#         expr = ListPatExpr(None,
#                             ConstantPatExpr(None, "MESSAGE %s"),
#                             ListPatExpr(None, ConstantPatExpr(None, 2)))
        self._expr.process(())
        self._result = None
        self._bindings = DictBindings(())

    def __repr__(self):
        return "<CObjective:[do: %s]>"%self.goalsym().id

    def e_sync_parent(self):
        # This is an asynchronous event
        return None

    def e_solver_target(self):
        # Although this event is async, we want to notify base on a result
        return self

    def tfhandlecfin(self, agent, event, result):
        self._result = result
        #XXX kwc - i'm copying this from other solver targets, as
        #we are missing the GoalSucceededEvents on COEvent objectives
        if result is SUCCESS:
            agent.post_event(GoalSucceededEvent(event))
        else:
            agent.post_event(GoalFailedEvent(event, result))

    def find_tframes(self, agent):
        return find_do_tframes(agent, self, self._bindings, \
                               self._symbol, self._expr)
    def bindings(self):
        return self._bindings
    def zexpr(self):
        return self._expr
    def goalsym(self):
        return self._symbol
    def kind_string(self):
        return "Do"

    def result(self):
        return self._result

def anchors_to_labeled(anchors):
    result = []
    for anchor in icl_or_spark_elements(anchors):
        deadline = "none"
        for mod in icl_or_spark_elements(icl_or_spark_elements(anchor)[3]):
            if icl_or_spark_functor_string(mod) == "deadline":
                deadline = icl_or_spark_elements(mod)[0]
        result.append((deadline, anchor))
    return tuple(result)


def icl_or_spark_elements(x):
    if isinstance(x, types.TupleType):
        return x
    elif isStructure(x):
        return x.args
    elif isinstance(x, IclList):
        return tuple([x for x in x.listIterator()])
    elif isinstance(x, IclStruct):
        return tuple([x for x in x.iterator()])
    elif isinstance(x, IclStr):
        return ()
    else:
        raise Exception("Expecting ICL/SPARK list or structure or atom: %r"%x)

def icl_or_spark_functor_string(x):
    if isStructure(x):
        return x.functor.id
    elif isinstance(x, IclStruct):
        return x.iclFunctor()
    elif isinstance(x, IclStr):
        return x.toUnquotedString()
    else:
        raise Exception("Expecting ICL/SPARK structure or atom: %r"%x)
