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
from threading import Condition

from spark.internal.version import *
from spark.internal.parse.expr import varsBeforeAndHere
from spark.internal.debug.trace import StepTrace, bindings_level, get_trace_fn, PRINT_TRACE, optionalGetVariableValueString, SUCCEEDED
from com.sri.ai.spark.debugger import SparkDebuggerPyCallback

# spark.internal.debug.tracejava
#
# defines trace/stepping extensions necessary for SPARK IDE Java harness
# author: kwc
#
# SINGLEAGENT
# NOTE: tracejava assumes a single agent debugging model.  In the future, we will
# have to rewrite this logic so that the stepper can be multi-agent

def jd_step_init(agent):
    return JavaStepController(agent)

def createVarHashMap(bindings, event, expr):
    #adapted from trace.variables()
    from java.util import HashMap
    from java.lang import String
    map = HashMap()
    if event is SUCCEEDED:
        vars = varsBeforeAndHere(expr)[2]
    else:
        vars = varsBeforeAndHere(expr)[0]

    for var in vars:
        map.put(String(str(var)), String(optionalGetVariableValueString(bindings, var)))
    return map

def jd_trace(agent, bindings, event, expr, info=""):
    PRINT_TRACE(agent, bindings, event, expr, info)
    bindingsMap = createVarHashMap(bindings, event, expr)
    SparkDebuggerPyCallback.pyDoTrace(agent, bindingsMap, bindings_level(bindings), event, expr, info)


################################################################

def jd_report_step(agent, bindings, event, expr, info):
    #print "jd_report_step"
    bindingsMap = createVarHashMap(bindings, event, expr)
    SparkDebuggerPyCallback.pyDoStep(agent, bindingsMap, bindings_level(bindings), event, expr, info)

class JavaStepController(StepTrace):

    def on_event(self, agent, bindings, event, expr, info):
#        XXX: todo if _step_filter value applies
        jd_report_step(agent, bindings, event, expr, info)
        return True

    def step(self):
        self.proceed()
