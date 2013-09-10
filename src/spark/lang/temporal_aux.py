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
from spark.internal.version import *
#from spark.common import PM
from spark.internal.repr.procedure import ProcedureTFrame
from spark.internal.repr.taskexpr import TFrame, GoalEvent, SUCCESS
from spark.internal.parse.basicvalues import Symbol

from spark.pylang.defaultimp import Structure, isStructure
from spark.pylang.defaultimp import ObjectiveEvent, SparkEvent
from spark.pylang.implementation import ActImpInt, PredImpInt

from spark.lang.meta_aux import find_first_taskexpr, find_next_taskexpr
    
def pi_task_structure(agent, pi):
    if not (isinstance(pi, ProcedureTFrame)): raise AssertionError
    proc = pi.procedure()
    prefix = pi.name() + "|"
    return procedure_task_structure(agent, proc, prefix)

AVG_EXEC_TIME = Symbol("spark.lang.temporal.avgExecTime")
AVG_RECOVERY_TIME = Symbol("spark.lang.temporal.avgRecoveryTime")
DEADLINE = Symbol("spark.lang.temporal.Deadline")
PROPERTY = Symbol("spark.module.property")

def procedure_task_structure(agent, proc, prefix=""):
    """Get the task structure of a procedure.
    If prefix is not "" then assume we are looking at task instances rather
    than task expressions. Also check for deadlines and only out put structure
    if there is at least one deadline."""
    print "procedure_task_structure%s"%((agent, proc, prefix),)
    body = proc.closed_zexpr.keyget0("body:")
    todo = find_first_taskexpr(body)
    done = []
    label_task = {}
    successors = {}
    predecessors = {}
    for expr in todo:
        predecessors[prefix + expr.label()] = []
    while todo:
        expr = todo.pop()
        done.append(expr)
        label = prefix + expr.label()
        label_task[label] = expr
        sucs = find_next_taskexpr(expr)
        #print "next of", expr, "is", sucs
        successors[label] = [prefix + suc.label() for suc in sucs]
        for suc in sucs:
            if suc not in done:
                todo.append(suc)
            slabel = prefix + suc.label()
            try:
                predecessors[slabel].append(label)
            except KeyError:
                predecessors[slabel] = [label]
    #print successors
    results = []
    is_a_deadline = False
    for (label, preds) in predecessors.items():
        taskexpr = label_task[label]
        statement = "?"
        etime = "none"
        rtime = "none"
        deadline = "none"
        try:
            sym = taskexpr.actexpr.actsym
            statement = sym.id
            for (_sym, prop) in agent.factslist1(PROPERTY, sym):
                #print "Property of %r: %r"%(sym, prop)
                if isStructure(prop):
                    if prop.functor == AVG_EXEC_TIME:
                        etime = prop[0]
                    elif prop.functor == AVG_RECOVERY_TIME:
                        rtime = prop[0]
            #print "Deadlines for %r are %r"%(label, agent.factslist1(DEADLINE, label))
            if prefix != "":
                for (_taskid, dl) in agent.factslist1(DEADLINE, label):
                    is_a_deadline = True
                    deadline = dl
        except AttributeError:
            print "Not a do task: %s"%taskexpr
        results.append((label, statement, etime, rtime, deadline, tuple(preds)))
    if prefix != "" and not is_a_deadline:
        return None
    # Shift results across to list if all the predecessors are present
    #print results
    #count = len(results)
    transfered = []
    labels = []
    while len(transfered) < len(results):
        for result in results:
            if result not in transfered:
                #print "checking result", result, labels
                for p in result[5]:
                    if p not in labels:
                        #print "  pred not transfered", result, p
                        break
                else:                   # no p was not in labels
                    #print "  transfering", result
                    transfered.append(result)
                    labels.append(result[0])
        #count = count - 1
        #if not (count >= 0): raise AssertionError, \
        #    "Too many loops"
    return tuple(transfered)
