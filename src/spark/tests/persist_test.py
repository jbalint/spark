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
#* "$Revision:: 129                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.version import *
from spark.pylang.implementation import Imp, PersistablePredImpInt
from spark.internal.parse.basicvalues import List
from spark.internal.repr.varbindings import valuesBZ
from spark.internal.parse.usagefuns import *
from spark.internal.common import SOLVED, NOT_SOLVED

class TestPersistImp(Imp, PersistablePredImpInt):
    #NOTE: single agent implementation (SINGLEAGENT). easy to make multiagent
    __slots__ = ('val')

    def __init__(self, decl):
        Imp.__init__(self, decl)
        self.val = "Test-Failed"

    def persist_arity_or_facts(self, ignore_agent):
        return [["Test-Failed"]]

    def resume_conclude(self, agent, bindings, zexpr):
        #as part of the test, we fail on the resume conclude
        b, z = valuesBZ(("Test-Succeeded",))
        return (b, z)
        
    def solution(self, agent, bindings, zexpr):
        if len(zexpr) != 1:
            raise zexpr.error("Invalid arity -- must have arity of 1")
        if self.val is not None and \
           termMatch(agent, bindings, zexpr[0], self.val):
            return SOLVED
        else:
            return NOT_SOLVED

#     def find_solutions(self, agent, bindings, zexpr):
#         if len(zexpr) != 1:
#             raise zexpr.error("Invalid arity -- must have arity of 1")
#         if self.val is not None and \
#                termMatch(agent, bindings, zexpr[0], self.val):
#             bindings.bfound_solution(agent, zexpr)

    def conclude(self, agent, bindings, zexpr):
        """Conclude this predicate and return whether the database has
        been changed."""
        from spark.internal.persist_aux import is_resuming
        if is_resuming():
            return
        self.val = termEvalErr(agent, bindings, zexpr[0])
        print "TestPersistPred: setting to %s"%self.val
        print "TestPersistPred: posting add fact event"
        from spark.pylang.defaultimp import AddFactEvent
        agent.post_event(AddFactEvent(self.symbol, List([termEvalErr(agent, bindings, z) for z in zexpr])))

    def retractall(self, agent, bindings, zexpr):
        """Retract anything matching this predicate and return whether
        the datadase has been changed."""
        raise zexpr.error("Cannot retractall on a test persist implementation")
