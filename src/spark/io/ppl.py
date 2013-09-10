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
#* "$Revision:: 191                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

def dropme():
    import sys
    del sys.modules[__name__]


from spark.internal.version import *
from spark.internal.common import NEWPM, DEBUG
from spark.internal.repr.common_symbols import P_Do, P_ArgTypes, P_Roles
#from spark.internal.repr.patexpr import * #NonAnonVarPatExpr
from spark.internal.repr.taskexpr import *
#from spark.internal.repr.predexpr import SimplePredExpr
#from spark.internal.repr.newbuild import ActSymInfo
from spark.lang.builtin import requiredargnames
from spark.internal.parse.basicvalues import Symbol, isSymbol
from spark.internal.repr.procedure import ProcedureValue
from spark.internal.parse.basicvalues import value_str, objectId, String, isString, Integer, isInteger, Float, isFloat, Symbol, isSymbol
from spark.internal.exception import CapturedError
debug = DEBUG(__name__)#.on()


PROC = None

def ppl_translate_procname(agent, procname, map=None, output=None):
    """Translate a procedure into PPL.
    map is a mapping from variables to Skolem constants.
    output is a list of tuples - the list is appended to"""
    if map is None:
        map = {}
    if output is None:
        output = []
    procname = str(procname)
    # Find the procedure
    do_facts = agent.factslist0(P_Do)
    for (sym, proc, namesym) in do_facts:
        if namesym.id == procname or namesym.name == procname:
            break
    else:
        return "No Procedure"
    global PROC
    PROC = proc
    ppl_translate_procedure(agent, procname, proc, map, output)
    # return the output
    return "".join(["(%s)\n"%(" ".join(tup)) for tup in output if None not in tup])

#MAP = {}                                # global map
def ppl_translate_procinst(agent, procinst):
    output = []
    map = ProcInstMap(procinst, {})
    proc = procinst.procedure()
    procname = str(proc.name())
    ppl_translate_procedure(agent, procname, proc, map, output)
    for subtask in map.executedSubevents:
        if isinstance(subtask, GoalEvent):
            if subtask.result:
                output.append(("succeeded", map.mapfind(subtask, "t")))
                # SHOULD ALSO PRINT VALUES OF ARGUMENTS BOUND
            else:
                output.append(("failed", map.mapfind(subtask, "t")))
    return "".join(["(%s)\n"%(" ".join(tup)) for tup in output if None not in tup])


def ppl_translate_procedure(agent, procname, proc, map, output):
    debug("Start ppl_translate_procedure %s", procname)
    procid = map.mapfind(proc, "p")
    # get the cue
    cueexpr = proc.closed_expr.cueexpr
    task = cueexpr[0]
    if isinstance(task, DoTaskExpr):
        actexpr = task[0] # was .actexpr
        # actsym = actexpr.actsym # doesn't work for cue as cue is not processed
        actsym = actexpr.term.key_term().sym_check_arity(ActSymInfo, actexpr)
        actid = actsym.id
    else:
        actid = "UNKNOWN"
    if map.mapfirst(procname, ""):
        output.append(("superclasses", procname, actid))
    output.append(("instance-of", procid, procname))
    ppl_translate_task(agent, task, map, output, procid)
    #output.append(("possibleExpansion", taskid, procid))
    # process the body
    ppl_translate_body(agent, proc.closed_expr.taskexpr, map, output, procid, NULL_FROM_CONDS)


class ProcInstMap(object):
    __slots__ = (
        "commonMap",                    # global map object->name, None-> count
        "procedureInstance",
        "objectToName",                     # map object to name
        #"nameToObject",                     # map name to object
        "counter",                          # counter for creating new names
        "executedSubevents",                # sequence of subevents that were executed
        "baseId",                           # basename to be used when generating new names
        )
    def __init__(self, procedureInstance, commonMap):
        self.commonMap = commonMap
        self.procedureInstance = procedureInstance
        self.objectToName = {}
        #self.nameToObject = {}
        self.counter = 0
        self.executedSubevents = []
        self.addExecutedSubevents(procedureInstance)
        # Because KM does not distinguish between a procedure instance
        # and a task instance, we must identify the procedure instance
        # with the task it achieves.
        self.baseId = objectId(self.procedureInstance.event())

    def getNewId(self):
        self.counter += 1
        return self.counter

    def addExecutedSubevents(self, tframe):
        for e in tframe.all_subgoal_events():
            if isinstance(e, TaskExprTFrame):
                self.addExecutedSubevents(e)
            else:
                self.executedSubevents.append(e)

    def mapfind(self, obj, prefix):
        result = self.objectToName.get(obj, None)
        if result is not None:
            return result
        if isinstance(obj, ProcedureValue) \
               and obj == self.procedureInstance.procedure():
            result = "t%s" % self.baseId
        elif isinstance(obj, DoTaskExpr):
            for event in self.executedSubevents:
                if isinstance(event, DoEvent) \
                   and event.taskexpr()[0] == obj[0]: # was obj.actexpr
                    result = "%s%s" % (prefix, objectId(event))
        elif isinstance(obj, DoEvent):
            result = "%s%s" % (prefix, objectId(obj))
        if result is None:
            result = "%s%s-%s" % (prefix, self.baseId, self.getNewId())
        self.objectToName[obj] = result
        return result

    def mapfirst(self, obj, prefix):
        map = self.commonMap
        result = map.get(obj, None)
        if result is None:
            num = map.get(None, 0) + 1
            map[None] = num
            result = "%sg%d" % (prefix, num)
            map[obj] = result
            return result
        else:
            return None

    def meval(self, agent, expr):
        "Evaluate expr if possible, else return None"
        bindings = self.procedureInstance.getBaseBindings()
        if not expr.isProcessed(): # cue isn't currently processed
            return None
        try:
            if expr.evalpx(agent, bindings):
                return termEvalErr(agent, bindings, expr)
            else:
                return None
        except:
            return None

class StaticMap(object):
    """Use this for static processing of procedures"""
    __slots__ = (
        "dict",
        "counter",
        )

    def __init__(self):
        self.dict = {}
        self.counter = 0

    def mapfind(self, obj, prefix):
        result = self.dict.get(obj, None)
        if result is None:
            result = "%s%d"%(prefix, self.getNewId())
            self.dict[obj] = result
        return result

    def mapfirst(self, obj, prefix):
        result = self.dict.get(obj, None)
        if result is None:
            result = "%sg%d"%(prefix, self.getNewId())
            self.dict[obj] = result
            return result
        else:
            return None

    def meval(self, agent, expr):
        return None

    def getNewId(self):
        self.counter += 1
        return self.counter


def ppl_translate_task(agent, task, map, output, taskid):
    debug("Start ppl_translate_task %s", task)
    if isinstance(task, DoTaskExpr):
        actexpr = task[0] # was .actexpr
        # actsym = actexpr.actsym # doesn't work for cue as cue is not processed
        actsym = actexpr.term.key_term().sym_check_arity(ActSymInfo, actexpr)
        #print "ACTSYM", actsym
        if map.mapfirst(actsym.id, "taskname"):
            # first occurrence of this task name
            output.append(("superclasses", actsym.id, "Task"))
        if taskid is None:
            # We haven't been told to use a different id (e.g. procedurename)
            taskid = map.mapfind(task, "t")
            output.append(("instance-of", taskid, actsym.id))
        argnames = requiredargnames(actsym) # doesn't handle rest args
        argtypefacts = agent.factslist1(P_ArgTypes, actsym)
        #print "argtypefacts", argtypefacts
        if argtypefacts:
            for argexpr, type in zip(actexpr, argtypefacts[0][1]):
                argid = ppl_term(agent, argexpr, map, output)
                output.append(("instance-of", argid, type.id))
        rolefacts = agent.factslist1(P_Roles, actsym)
        #print "rolefacts", rolefacts
        role_dict = {}
        if rolefacts:
            for role in rolefacts[0][1]:
                varsym = role[0]
                rolesym = role.functor
                role_dict[varsym] = rolesym
        for (argexpr, namesym, argnum) \
                in zip(actexpr, argnames, range(len(actexpr))):
            role = role_dict.get(namesym, None)
            if role is None:
                role = Symbol("arg%d"%argnum)
            argid = ppl_term(agent, argexpr, map, output)
            output.append((role.id, taskid, argid))
        return taskid
    else:
        pass # TODO: work out what this should really be
        #raise Exception("InvalidType", task)

def ppl_translate_body(agent, task, map, output, procid, fromConds):
    comp = task._components
    if isinstance(task, DoTaskExpr):
        debug("Start ppl_translate_body DoTaskExpr %s", task)
        taskid = ppl_translate_task(agent, task, map, output, None)
        output.append(("possibleTask", procid, taskid))
        ppl_translate_fromConds(fromConds, taskid, output)
        return createNewFromConds(taskid)
    elif isinstance(task, AchieveTaskExpr):
        debug("Start ppl_translate_body AchieveTaskExpr %s", task)
        raise Exception("AchieveTaskExpr not handled yet")
    elif isinstance(task, SetTaskExpr):
        debug("Start ppl_translate_body SetTaskExpr %s", task)
        return appendFromConds(fromConds, task)
    elif isinstance(task, SeqTaskExpr) or isinstance(task, ContiguousTaskExpr)\
             or isinstance(task, InternalBracketTaskExpr):
        debug("Start ppl_translate_body Seq/Contiguous/BracketTaskExpr %s", task)
        for t in comp:
            fromConds = ppl_translate_body(agent, t, map, output, procid, fromConds)
        return fromConds
    elif isinstance(task, ParallelTaskExpr):
        debug("Start ppl_translate_body ParallelTaskExpr %s", task)
        resultFromConds = NULL_FROM_CONDS
        for t in comp:
            newFromConds = ppl_translate_body(agent, t, map, output, procid, fromConds)
            resultFromConds = mergeFromConds(resultFromConds, newFromConds)
        return resultFromConds
    elif isinstance(task, TryTaskExpr):
        debug("Start ppl_translate_body TryTaskExpr %s", task)
        resultFromConds = NULL_FROM_CONDS
        for i in range(0, len(comp), 2):
            newFromConds = ppl_translate_body(agent, comp[i], map, output, procid, fromConds)
            fromConds = appendFailureFromConds(fromConds)
            if i+1 < len(comp):
                newFromConds = ppl_translate_body(agent, comp[i+1], map, output, procid, newFromConds)
            resultFromConds = mergeFromConds(resultFromConds, newFromConds)
        return resultFromConds
    elif isinstance(task, CondLikeTaskExpr):
        debug("Start ppl_translate_body CondLikeTaskExpr %s", task)
        resultFromConds = NULL_FROM_CONDS
        for i in range(0, len(comp), 2):
            newFromConds = appendFromConds(fromConds, comp[i])
            fromConds = appendNotFromConds(fromConds, comp[i])
            if i+1 < len(comp):
                newFromConds = ppl_translate_body(agent, comp[i+1], map, output, procid, newFromConds)
            resultFromConds = mergeFromConds(resultFromConds, newFromConds)
        return resultFromConds
#     elif isinstance(task, EffectTaskExpr):
#         debug("Start ppl_translate_body EffectTaskExpr %s", task)
#         return fromConds
    elif isinstance(task, SucceedTaskExpr):
        debug("Start ppl_translate_body SucceedTaskExpr %s", task)
        return fromConds
    elif isinstance(task, FailTaskExpr):
        debug("Start ppl_translate_body FailTaskExpr %s", task)
        return NULL_FROM_CONDS
    elif isinstance(task, ForallTaskExpr) \
             or isinstance(task, ForinTaskExpr) \
             or isinstance(task, WhileTaskExpr):
        debug("Start ppl_translate_body Loop %s", task)
        taskexpr = comp[-1]             # last component
        predexpr = comp[-2]
        looptaskid = map.mapfind(task, "nullt")
        output.append(("instance-of", looptaskid, "NULLTASK"))
        ppl_translate_fromConds(fromConds, looptaskid, output)
        loopFromConds = createNewFromConds(looptaskid)
        newFromConds = appendFromConds(loopFromConds, predexpr)
        newFromConds = ppl_translate_body(agent, taskexpr, map, output, procid, newFromConds)
        ppl_translate_fromConds(newFromConds, looptaskid, output)
        return appendNotFromConds(loopFromConds, predexpr)
    elif isinstance(task, ContextTaskBodyTag):
        debug("Start ppl_translate_body ContextTaskBodyTag %s", task)
        return ppl_translate_body(agent, comp[-1], map, output, procid, appendFromConds(fromConds, comp[0]))
    elif isinstance(task, ConcludeTaskBodyTag) \
             and isinstance(comp[0], SimplePredExpr):
        debug("Start ppl_translate_body ContextTaskBodyTag %s", task)
        ## predname = comp[0].predsym.id
        ## args = [value_km_str(map.meval(agent, pat)) for pat in comp[0]._components]
        ## output.append((predname,)+tuple(args))
        return ppl_translate_body(agent, comp[-1], map, output, procid, appendFromConds(fromConds, comp[0]))
    elif isinstance(task, BodyTaskBodyTag):
        debug("Start ppl_translate_body BodyTaskBodyTag %s", task)
        newFromConds = ppl_translate_body(agent, comp[0], map, output, procid, fromConds)
        return ppl_translate_body(agent, comp[-1], map, output, procid, newFromConds)
    elif isinstance(task, EndTaskBodyTag):
        return fromConds
    elif isinstance(task, TaskBodyTag):
        debug("Start ppl_translate_body TaskBodyTag %s", task)
        return ppl_translate_body(agent, comp[-1], map, output, procid, fromConds)
    else:
        print "Ignoring", task
        return fromConds

def createNewFromConds(taskid):
    "Create a fromConds corresponding to a single path from taskid"
    return ((taskid,),)

NULL_FROM_CONDS = ()                    # no possible path

def appendFromConds(fromConds, expr):
    "Append the condition expr to all paths in fromConds"
    str_expr = str(expr)
    if str_expr == "(True)":
        return fromConds
    elif str_expr == "(False)":
        return NULL_FROM_CONDS
    else:
        return tuple([x + (value_str(str_expr),) for x in fromConds])

def appendNotFromConds(fromConds, expr):
    "Append the negation of condition expr to all paths in fromConds"
    str_expr = str(expr)
    if str_expr == "(False)":
        return fromConds
    elif str_expr == "(True)":
        return NULL_FROM_CONDS
    else:
        return tuple([x + (value_str("~"+str_expr),) for x in fromConds])

def appendFailureFromConds(fromConds):
    "Append the requirement for some failure to all paths in fromConds"
    return tuple([x + ("SOME_FAILURE",) for x in fromConds])

def mergeFromConds(fromConds1, fromConds2):
    "Combine paths from alternative or parallel branches"
    return fromConds1 + fromConds2

def ppl_translate_fromConds(fromConds, taskid, output):
    "Output the conditional followed by constraints on taskid"
    for fromCond in fromConds:
        fromTask = fromCond[0]
        rest = fromCond[1:]
        if rest:
            cond = "(and " + " ".join(rest) + ")"
            output.append(("conditionalFollowedBy", fromTask, cond, taskid))
        else:
            output.append(("followedBy", fromTask, taskid))


def ppl_term(agent, expr, map, output):
    value = map.meval(agent, expr) # TODO: This assumes that variables are never rebound by failure
    if value is not None:
        return value_km_str(value)
    if isinstance(expr, NonAnonVarPatExpr):
        return map.mapfind(Symbol(expr.varid), "v")
    elif isinstance(expr, ConstantPatExpr):
        return value_km_str(expr.get_value())
    elif isinstance(expr, ListPatExpr):
        elements = [ppl_term(agent, elt, map, output) \
                    for elt in expr]
        return "(list " + " ".join(elements) + ")"
    else:
        return "(sparkeval " + value_str(str(expr)) + ")"
        #raise Exception("InvalidTerm", expr)

def value_km_str(x):
    "convert x to a KM string"
    # TODO: make this work for real
    if isString(x) or isInteger(x) \
           or isFloat(x) or isSymbol(x):
        return value_str(x)
    else:
        return None

from spark.main import runAgent
def main():
    out = ppl_translate_procname(run_agent, "Find_Matching_Computers")
    print out

def appendToFile(string, filename):
    print "APPENDING TO FILE", filename
    file = open(filename, 'a')
    file.write(string)
    file.close()

def removeFile(filename):
    import os
    try:
        print "=== REMOVING FILE %s ==="%filename
        os.remove(filename)
        print "=== SUCCEEDED IN REMOVING FILE %s ==="%filename
        return True
    except:
        NEWPM.displayError()
        return False
