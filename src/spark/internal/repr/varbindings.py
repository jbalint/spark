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
from spark.internal.set import IBITS
from spark.internal.common import paranoid, DEBUG, POSITIVE, NEGATIVE
from spark.internal.exception import InternalException, RuntimeModeException, LowError, Unimplemented
from spark.internal.parse.basicvalues import ConstructibleValue, installConstructor, List


debug = DEBUG(__name__).on()

# Bindings
class BindingsInt(object):
    """Interface for bindings objects"""
    __slots__ = ()
    # Method to include in all old-style bindings
#     def bInfo(self, agent, symbol, initializer):
#         info = agent.getInfo(symbol)
#         if info is None:
#             info = initializer()
#             agent.setInfo(symbol, info)
#         return info

    def level(self):
        return 0

    def bTermEval(self, agent, zitem):
        "Evaluate zitem assuming it is evaluable, either because it is always evaluable, or because it has now been bound."
        raise Unimplemented()
        
    def bTermEvalP(self, agent, zitem):
        "Is zitem evaluable in its normal execution context"
        raise Unimplemented()

    def bTermMatch(self, agent, zitem, value):
        "Match zitem to value, save any bindings, return whether the match succeeded"
        raise Unimplemented()

    def bQuotedEval(self, agent, zitem):
        "Evaluated zitem as being quoted"
        raise Unimplemented()

    def bQuotedMatch(self, agent, zitem, value):
        "Match zitem considering it to be quoted, return whether the match succeeded"
        raise Unimplemented()

    def bEntity(self, agent, zitem):
        "Find the fully qualified symbol name for zitem"
        raise Unimplemented()
        

    def bImp(self, agent, zitem):
        "Return the implementation to use for processing zitem"
        raise Unimplemented()

################################################################


################
# For a simple values
# bindings=VALUES_BINDINGS
# zexpr=sequence of values

class ValuesBindings(BindingsInt, ConstructibleValue):
    # This doesn't really need to be a ConstructibleValue - it is
    # really an immutable singleton - but making it a
    # ConstructibleValue means that persistence is simple.
    __slots__ = ()

    def set_state(self, agent):
        pass
    
    # bindings methods
    def bTermEval(self, agent, zitem):
        return zitem
        
    def bTermEvalP(self, agent, zitem):
        return True

    def bTermMatch(self, agent, zitem, value):
        return zitem == value

    constructor_mode = ""

installConstructor(ValuesBindings)

VALUES_BINDING = ValuesBindings()

def values_binding():
    return VALUES_BINDING

def valuesBZ(values):
    return (VALUES_BINDING, values)

################################################################


################
# For optional values
# bindings = OptBindings instance
# zexpr = sequence of indices (negative for bindable)

class OptBindings(BindingsInt, ConstructibleValue):
    __slots__ = (
        "_contents",
        )

    def __init__(self, seq=()):
        ConstructibleValue.__init__(self)
        self._contents = list(seq)

    def set_state(self, agent, contents):
        self._contents[:] = contents
        
    cvcategory="AC"
    constructor_mode = ""
    def constructor_args(self):
        return []
    def state_args(self):
        return (List(self._contents),)

    def bTermEval(self, agent, zitem):
        return self._contents[zitem]
        
    def bTermEvalP(self, agent, zitem):
        return zitem >= 0

    def bTermMatch(self, agent, zitem, value):
        if zitem < 0:
            self._contents[zitem] = value
            return True
        else:
            return self._contents[zitem] == value


installConstructor(OptBindings)

def optBZ(optvalues):
    length = len(optvalues)
    indices = range(length)
    for index in indices:
        if optvalues[index] is None:
            indices[index] = index - length # negative index for bindable
    return (OptBindings(optvalues), List(indices))

################################################################
# ValueZB/OptZB interface for old code


class ZB(BindingsInt, ConstructibleValue):
    """This is an object that simultaneously performs the role of
    bindings and zexpr."""
    # This doesn't really need to be a ConstructibleValue - it is
    # really an immutable pair - but making it a
    # ConstructibleValue means that persistence is simple.
    __slots__ = (
        "bindings",
        "zexpr",
        )

    def __init__(self, (bindings, zexpr)):
        ConstructibleValue.__init__(self)
        self.bindings = bindings
        self.zexpr = zexpr

    def set_state(self, agent):
        pass
    def constructor_args(self):
        return [self.bindings, self.zexpr]
        
    def __getitem__(self, index):
        return self.zexpr[index]

    def __len__(self):
        return len(self.zexpr)
    
    def bTermEval(self, agent, zitem):
        return self.bindings.bTermEval(agent, zitem)
        
    def bTermEvalP(self, agent, zitem):
        return self.bindings.bTermEvalP(agent, zitem)

    def bTermMatch(self, agent, zitem, value):
        return self.bindings.bTermMatch(agent, zitem, value)

def OptZB(optvalues):
    return ZB(optBZ(optvalues))

def ValueZB(seq):
    return ZB(valuesBZ(seq))
