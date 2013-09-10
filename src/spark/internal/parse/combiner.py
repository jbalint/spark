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
#* "$Revision:: 139                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.version import *
from sets_extra import Set, union_of, EMPTY_SET
from spark.internal.parse.errormsg import ErrorMsg, F2

# ErrorMsgs returned by validateVars. These will have expr set later.

class E241VarsParallelMultiple(ErrorMsg):
    level = F2
    argnames = ["vars"]
    format = "%(vars)s bound in multiple parameters"

class E242VarsQuanifiedBound(ErrorMsg):
    level = F2
    argnames = ["vars"]
    format = "%(vars)s bound before being quantified"



################################################################
################
####
#
# Combiners
#
# How do we combine the variables of the components of a ProcCompound

class Combiner(object):
    __slots__ = ()

    def validateVars(self, argfrees, vbbefore, free, hidden):
        return None

    def prior(self, ignore_indexkey):
        return None

    def varsAlternatives(self, subfreevars):
        return None

class Serial(Combiner):
    def prior(self, indexkey):
        if indexkey == 0:
            return None
        else:
            # also works for keyword arguments if there is at least on positional argument
            return indexkey - 1

SERIAL = Serial()

class Parallel(Combiner):
    def validateVars(self, argfrees, vbbefore, free, hidden):
        # check for any previously unbound variable appearing in multiple branches
        duplicateVars = Set()
        for var in free:
            if var not in vbbefore:
                # var can only appear in one branch
                found = False
                for argfree in argfrees:
                    if var in argfree:
                        if found:
                            duplicateVars.add(var)
                            break
                        found = True
        if duplicateVars:
            return E241VarsParallelMultiple(None, varsString(duplicateVars))
        else:
            return None

PARALLEL = Parallel()

def varsString(vars):
    if vars:
        if len(vars) == 1:
            return "Variable %s is" % list(vars)[0]
        else:
            return "Variables %s are"%(" and ".join([str(v) for v in vars]))
    else:
        return ""

class Disjunctive(Combiner):
    def varsAlternatives(self, subfreevars):
        return subfreevars

DISJUNCTIVE = Disjunctive()


class CondLike(Combiner):
    def prior(self, index):
        if index % 2 == 0:
            return None
        else:
            return index - 1

    def varsAlternatives(self, subfreevars):
        alternatives = [subfreevars[index].union(subfreevars[index+1]) \
                        for index in range(0,len(subfreevars)-1,2)]
        if len(subfreevars) % 2 == 1:              # odd
            alternatives.append(subfreevars[-1])
        #print "CondLike varsAlternatives=", alternatives
        return alternatives

COND_LIKE = CondLike()

class Negated(Combiner):
    def varsAlternatives(self, subfreevars):
        return (subfreevars[0], EMPTY_SET)

NEGATED = Negated()

class Quantified(Combiner):
    def prior(self, indexkey):
        if indexkey <= 1:
            return None
        else:
            return indexkey - 1

    def validateVars(self, argfrees, vbbefore, free, hidden):
        badvars = argfrees[0].intersection(vbbefore)
        if badvars:
            return E242VarsQuanifiedBound(None, varsString(badvars))
        else:
            return None

    def varsAlternatives(self, subfreevars):
        return (subfreevars[1], subfreevars[1].difference(subfreevars[0]))

QUANTIFIED = Quantified()
class Locals(Combiner):
    def prior(self, indexkey):
        if indexkey <= 1:
            return None
        else:
            return indexkey - 1

    def validateVars(self, argfrees, vbbefore, free, hidden):
        badvars = argfrees[0].intersection(vbbefore)
        if badvars:
            return E242VarsQuanifiedBound(None, varsString(badvars))
        else:
            return None

    def varsAlternatives(self, subfreevars):
        return (union_of(subfreevars[1:]), EMPTY_SET)

LOCALS = Locals()
class Forin(Combiner):
    def prior(self, indexkey):
        if indexkey == 0:
            return None
        elif indexkey == 1:
            return None
        elif indexkey == 2:
            return 0
        elif indexkey % 2 == 1:
            return 2
        else:
            return None

    def validateVars(self, argfrees, vbbefore, free, hidden):
        badvars = argfrees[0].intersection(vbbefore)
        if badvars:
            return E242VarsQuanifiedBound(None, varsString(badvars))
        else:
            return None

    def varsAlternatives(self, subfreevars):
        return (union_of(subfreevars[1:]), union_of(subfreevars[4::2]))

FORIN = Forin()


class Defprocedure(Serial):
    def validateVars(self, argfrees, vbbefore, free, hidden):
        badvars = argfrees[0].intersection(vbbefore)
        if badvars:
            return E242VarsQuanifiedBound(None, varsString(badvars))
        else:
            return None

    def varsAlternatives(self, subfreevars):
        return (union_of(subfreevars[1:]), EMPTY_SET)

DEFPROCEDURE = Defprocedure()
