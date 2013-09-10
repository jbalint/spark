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
#* "$Revision:: 71                                                        $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
import types

from spark.internal.version import *
#from spark.internal.engine.find_module import ensure_modpath_installed
from spark.internal.engine.agent import Agent
#from spark.internal.repr.newkinds import STATEMENT
from spark.internal.parse.basicvalues import Symbol, String, isString, List, isList
from spark.internal.common import NEWPM
from spark.internal.exception import ProcessingError, LocatedError, UnlocatedError
from spark.internal.repr.taskexpr import SUCCESS, TFrame
#from spark.lang.builtin import ProcedureFactExpr
from spark.pylang.defaultimp import SparkEvent
from spark.internal.parse.processing import PseudoFileSPU, load_file_into_agent, printErrors
from spark.internal.parse.usages import PRED_UPDATE

class Writeable(object):
    __slots__ = ("strings","softspace")
    def __init__(self):
        self.strings = []
    def write(self, string):
        self.strings.append(string)
    def __str__(self):
        return "".join(self.strings)

def parseAndConclude(agent, statement, packagename):
    if not (isinstance(agent, Agent)): raise AssertionError
    if not (isString(statement)): raise AssertionError
    if not (isString(packagename)): raise AssertionError
    spu = PseudoFileSPU(packagename)
    spu.textUpdate(None, statement)
    if spu.if_OK2_insert_info_FILENAME_SPU():
        if load_file_into_agent(spu.filename, agent):
            return List(spu.getExprs())
    w = Writeable()
    printErrors(spu, False, w)
    raise UnlocatedError(str(w))
#     if spu.if_OK2_insert_info_FILENAME_SPU() \
#            and load_file_into_agent(spu.filename, agent):
#         #print "Succeeded", spu._exprs
#         return List(spu.getExprs())
#     else:
#         #print "Failed"
#         return None

def defprocedure_exprs_name(agent, exprs):
    if not (isList(exprs)): raise AssertionError
    if (len(exprs) != 1): raise AssertionError
    pfe = exprs[0]
    if pfe.functor != Symbol('defprocedure{}'):
        raise LocatedError(pfe, "must be {defprocedure ...}")
    return pfe[0].asValue()

def remove_children(agent, tframe):
     "Prune all children of tframe"
     # WARNING
     # This does not do any cleanup of children tframes
     # This will cause unexpected results if variable bindings are expected
     if not (isinstance(tframe, TFrame)): raise AssertionError, \
            "remove_children requires a TFrame argument, not %r"%(tframe,)
     children = agent.tframe_children(tframe)
     for child in children[:]:
         remove_children(agent, child)
         agent.remove_tframe(child)
     children = agent.tframe_children(tframe)
     if (children): raise AssertionError, \
        "Tframe %s still has children: %s"%(tframe,children)

def setSucceeded(agent, task):
    if not (isinstance(task, SparkEvent)): raise AssertionError
    parent_pi = task.e_sync_parent()
    if parent_pi is not None:
        remove_children(agent, parent_pi)
        parent_pi.tfhandlecfin(agent, task, SUCCESS)
    else:
        raise Exception("Cannot handle top level tasks")
    return True
