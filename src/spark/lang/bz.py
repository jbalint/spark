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

from __future__ import generators
from spark.internal.version import *
from spark.pylang.implementation import ActImpInt, PredImpInt, FunImpInt
from spark.internal.repr.varbindings import optBZ
from spark.internal.parse.usagefuns import termEvalErr, termEvalEnd
from spark.internal.parse.basicvalues import List
"""
Support for explicit representation and use of SPARK internal bindings and zexpr objects from SPARK language.

DO NOT USE THIS UNLESS YOU HAVE A GOOD UNDERSTANDING OF THE SPARK INTERNALS!
"""

################################################################
# Generic routines for dealing with bindings and zexprs


def termsEvalEnd(agent, bindings, zexprs):
    return List([termEvalEnd(agent, bindings, zexpr) for zexpr in zexprs])

################################################################

# Idiom for making a non-deterministic function into a SPARK predicate
# rather than a SPARK action.

# A SPARK function must return values that equal each other if the KB
# hasn't changed since the last time it was called. SPARK function
# calls and predicate tests are n't allowed to change the
# KB. Therefore for example, a random number generator could not be
# used as a SPARK function, since if you call it twice in succession
# you *want* it to return different values.

# You could represent it by a SPARK action, but this restricts you
# from using it in term expressions and predicate expressions.

# Instead you can represent it by a predicate with multiple solutions,
# where testing the predicate "picks" one of the many possible
# solutions tat it could return. This is fine if you only ever ask for
# one solution to the predicate, but technically, it should return
# *every* possible value if you ask for every solution.

# To get around this, we have a generator that returns one solution,
# and if another is requested, generates an error.

# You also need to ensure that if the predicate is used with the
# (normally output) parameter bound, the implementation should raise
# an exception or test that it is a valid output value, rather than
# generate an output value and test for equality.

# TODO: We should probably implement a variant of pyPredicate for this.

def partialBZ(partial, bindings, zexprs):
    "Bindings and zexprs are derived from a partial sequence where missing values denote output arguments"
    if partial is None:
        raise LowError("First argument must be bound")
    if bindings is None:
        if zexprs is None:
            return generateBZ(partial)
    raise LowError("Neither the second nor third argument may be bound")

def generateBZ(partial):
    b, z = optBZ(partial)
    yield (partial, b, z)
    raise LowError("Only one solution to PartialBZ is allowed to be returned")

# The following is based on code from the CALO task_manager/tirmodes.py.

# Unlike the applyact action, which can create tframes using the same
# bindings and a modified zexpr (just dropping the first element),
# applyToBZ is more complex. It must use a new bindings and zexpr
# constructed from the given partial structure, and after the chosen
# tframe is executed there must be a separate step to construct the
# output structure. Thus applyToBZ is implemented by a procedure
# that uses a function to generate the bindings/zexpr pair, an action
# to apply the functor of the input structure to this bindings/zexpr
# pair, and then a function to extract the output values from
# bindings/zexpr pair.

def helper(agent, bindings, zexpr):
    # Get the symbol/closure
    symvalue = termEvalErr(agent, bindings, zexpr[0])
    # get the relevant implementation
    imp = agent.value_imp(symvalue)
    # Get the bindings/zexpr pair
    b = termEvalErr(agent, bindings, zexpr[1])
    z = termEvalErr(agent, bindings, zexpr[2])
    return imp, b, z

class ApplyActToBZ(ActImpInt):
    __slots__ = ()
    def __init__(self, _symbol):
        pass

    def tframes(self, agent, event, bindings, zexpr):
        imp, b, z = helper(agent, bindings, zexpr)
        return imp.tframes(agent, event, b, z)

class ApplyPredToBZ(PredImpInt):
    __slots__ = ()
    def __init__(self, _symbol):
        pass

    def solutions(self, agent, bindings, zexpr):
        imp, b, z = helper(agent, bindings, zexpr)
        return imp.solutions(agent, b, z)

    def solution(self, agent, bindings, zexpr):
        imp, b, z = helper(agent, bindings, zexpr)
        return imp.solution(agent, b, z)

    def conclude(self, agent, bindings, zexpr):
        imp, b, z = helper(agent, bindings, zexpr)
        return imp.conclude(agent, b, z)

    def retractall(self, agent, bindings, zexpr):
        imp, b, z = helper(agent, bindings, zexpr)
        return imp.retractall(agent, b, z)

class ApplyFunToBZ(FunImpInt):
    __slots__ = ()
    def __init__(self, _symbol):
        pass

    def call(self, agent, bindings, zexpr):
        imp, b, z = helper(agent, bindings, zexpr)
        return imp.call(agent, b, z)

    def match_inverse(self, agent, bindings, zexpr, obj):
        imp, b, z = helper(agent, bindings, zexpr)
        return imp.match_inverse(agent, b, z, obj)
