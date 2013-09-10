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
from spark.internal.exception import Unimplemented
from spark.internal.common import ONE_SOLUTION, NO_SOLUTIONS, SOLVED, NOT_SOLVED

################################################################
################################################################
# Interfaces

class ImpInt(object):           # Interface
    __slots__ = ()

    def generateInfo(self):
        """Create an info for use with the implementation if none exists"""
        raise Unimplemented("Implementation must define generateInfo")

class ImpGenInt(object):
    """A prototype implementation - call __call__ with symbol to produce an implementation"""
    __slots__ = ()
    def __call__(self, decl):
        """Construct an instance of ImpInt"""
        raise Unimplemented("Implementation generator must define __call__")

class FunImpInt(ImpInt):      # Interface
    __slots__ = ()

    def call(self, agent, bindings, zexpr):
        """Calls the function on the given arguments"""
        raise Unimplemented("Function implementation must define call")
#     def call(self, agent, *args):
#         """Calls the function on the given arguments"""
#         raise Unimplemented("Function implementation must define call")

    def match_inverse(self, agent, bindings, zexpr, obj):
        """Attempt to match the inverse function applied to obj"""
        raise Unimplemented("Function implementation must define inverse")

class PredImpInt(ImpInt):     # Interface
    __slots__ = ()

#     def find_solutions(self, agent, bindings, zexpr):
#         """For each solution to the predicate, match the zexpr and call
#         bindings.bfound_solution(agent, zexpr)."""
#         raise Unimplemented()

    def default_solutions(self, agent, bindings, zitems):
        """Generator - of solutions to the predicate, return True for
        each solution after matching the zitems."""
        if self.solution(agent, bindings, zitems):
            return ONE_SOLUTION
        else:
            return NO_SOLUTIONS

    def solutions(self, agent, bindings, zitems):
        """Generator - of solutions to the predicate, return True for
        each solution after matching the zitems."""
        if self.solution == PredImpInt.solution:
            raise Unimplemented()
        if self.solution(agent, bindings, zitems):
            return ONE_SOLUTION
        else:
            return NO_SOLUTIONS

    def default_solution(self, agent, bindings, zitems):
        for x in self.solutions(agent, bindings, zitems):
            if x:
                return SOLVED
        return NOT_SOLVED

    def solution(self, agent, bindings, zitems):
        if self.solutions == PredImpInt.solutions:
            raise Unimplemented()
        for x in self.solutions(agent, bindings, zitems):
            if x:
                return SOLVED
        return NOT_SOLVED

    def conclude(self, agent, bindings, zexpr):
        """Conclude this predicate and return whether the database has
        been changed."""
        raise Unimplemented("Predicate implementation for %s must define conclude"%self.__class__.__name__)

    def retractall(self, agent, bindings, zexpr):
        """Retract anything matching this predicate and return whether
        the datadase has been changed."""
        raise Unimplemented("Predicate implementation must define retractall")    
#PERSIST
class PersistablePredImpInt(PredImpInt):     # Interface
    __slots__ = ()

    def resume_conclude(self, agent, bindings, zexpr):
        """conclude as part of a resume operation. If the conclude is
        successful, return None.  If the conclude cannot be
        successfully completed, return a tuple (Bindings, ValuesZexpr)
        representing a new set of values to be concluded after the
        resume operation completes. This new set of values will
        trigger newfact: events"""
        
        raise Unimplemented("Persistable predicate implementation for %s must define resume_conclude"%self.__class__.__name__)
    
    def persist_arity_or_facts(self, agent):
        """Return either a list of facts (sequences of argument
        values) to be persisted or the number of arguments of the
        predicate (to generate the facts)"""
        raise Unimplemented("Persistable predicate implementation for %s must define persist_arity_or_facts"%self.__class__.__name__)




class ActImpInt(ImpInt):            # Interface
    __slots__ = ()

    def tframes(self, agent, event, bindings, zexpr):
        "return a list of tframes to handle the task"
        raise Unimplemented("Task implementation must define tframes")

class TaskImpInt(ImpInt):               # unused
    __slots__ = ()

    def enter(self, agent, tf, zexpr):
        raise Unimplemented()

    def subgoal_complete(self, agent, tf, zexpr, subgoal, result):
        raise Unimplemented()

    def resume(self, agent, tf, zexpr):
        raise Unimplemented()

    def child_complete(self, agent, tf, zexpr, index, result):
        raise Unimplemented()

    def handle_signal(self, agent, tf, zexpr, signal):
        return False
    


#     def execute(self, agent, bindings, zexpr):
#         "Execute the task"
#         raise Unimplemented("Task implementation must define execute")

################################################################
################
####
#
# Base implementations

class Imp(ImpInt):
    __slots__ = (
        "symbol",
        )
    def __init__(self, decl):
        self.symbol = decl and decl.asSymbol()
        
    def __str__(self):
        return "<%s:%s>"%(self.__class__.__name__, self.symbol)
    def __repr__(self):
        return self.__str__()
    def thandle_signal(self, agent, tf, zexpr, signal): # default
        return False
