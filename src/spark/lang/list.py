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
#* "$Revision:: 461                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from __future__ import generators
import random
import types

from spark.internal.version import *
from spark.internal.exception import LowError, LocatedError
from spark.internal.repr.varbindings import valuesBZ
from spark.internal.parse.basicvalues import List, isList, ConstructibleValue, installConstructor
from spark.internal.parse.usagefuns import *
from spark.pylang.implementation import Imp, PredImpInt, FunImpInt
##################################################
#
# Common list operators
#
# Note that SPARK lists are actually python tuples
#
#####

def sort_spark_list(x):
    y = list(x)
    y.sort()
    return List(y)

def custom_sort_list(x, fun_str):
    import code
    y = list(x)
    y.sort(eval(fun_str))
    return List(y)

def print_list_elements(args):
    for x in args:
        print x
    return True

def empty_list (list):
    if (len(list)==0):
        return True
    else:
        return False

CHECK_VALID_LIST = False

def list_elements(x):
    if CHECK_VALID_LIST and not isinstance(x, types.TupleType):
        raise LowError("Expecting a SPARK list, not %r", x)
    return x
         
def map_call(agent, funvalue, *args):
        if len(args) < 1:
            raise LowError("map requires at least one list argument")
        imp = agent.value_imp(funvalue)
        l = len(args[0])
        for arg in args:
            if len(arg) != l:
                raise LowError("Mismatched lengths of lists supplied to map")
        # apply imp to each tuple
        result = []
        for tup in zip(*args):
            if None in tup:             # NULL ELEMENT
                # result is partial if any input list is partial
                result.append(None)
            else:
                b, z = valuesBZ(tup)
                result.append(imp.call(agent, b, z))
        return List(result)


def sparkZip(*lists):
    return List(zip(*lists))

def sparkZipStar(lists):
    return List(zip(*lists))

def subset(superset, subset):
    ss = []
    for e in superset:
        if not e in ss:
            ss.append(e)
    if subset == None:
        return List(constructSubsets(ss))
    else:
        return testHasSubset(ss, subset)

def constructSubsets(l):
    "Create a sequence of subsets of the spark list l"
    print "l = %s"%(l,)
    if len(l) == 0:
        x = []
        x.append(())
        return x
    else:
        firstElementList = (l[0],)
        restSolutions = constructSubsets(l[1:])
        x = restSolutions + [firstElementList + x for x in restSolutions]
        return x

def testHasSubset(superset, subset):
    for elt in subset:
        if not elt in superset:
            return False
    return subset

def intersection(set1, set2):
    return List([x for x in set1 if x in set2])

def union(set1, set2):
    l = list(set1)
    for x in set2:
        if x not in l:
            l.append(x)
    return List(l)


def first(x):
    return x[0]

def rest(x):
    return x[1:]

def second(x):
    return x[1]

def third(x):
    return x[2]
    
def last(x):
	return x[len(x) - 1]    

def reduce(agent, fun, list):
    if None in list:                    # NULL ELEMENT
        raise LowError("Cannot apply reduce to a partial list")
    imp = agent.value_imp(fun)
    val = list[0]
    index = 1
    while index < len(list):
        b, z = valuesBZ((val, list[index]))
        val = imp.call(agent, b, z)
        index += 1
    return val
    
class Accumulator(ConstructibleValue):
    __slots__ = (
        "_contents",
        )
    def __init__(self, initSeq=None):
        ConstructibleValue.__init__(self)
        if initSeq is None:
            self._contents = []
        else:
            self._contents = list(initSeq)

    def set_state(self, agent, contents):
        self._contents[:] = contents
        
    cvcategory="AC"
    constructor_mode = ""
    def constructor_args(self):
        return []
    def state_args(self):
        return (List(self._contents),)

    def __len__(self):
        return len(self._contents)
    def __getitem__(self, index):
        if isinstance(index, types.SliceType):
            return List(self._contents[index])
        else:
            return self._contents[index]
    def __delitem__(self, index):
        del self._contents[index]
    def __setitem__(self, index, value):
        self._contents[index] = value
    def __contains__(self, elt):
        return elt in self._contents
    def set(self, seq):
        self._contents[:] = seq
    def append(self, elt):
        self._contents.append(elt)
    def remove(self, elt):
        return self._contents.remove(elt)
    def pop(self, index = -1):
        return self._contents.pop(index)
    def reverse(self):
        self._contents.reverse()
    def coerceToSPARKForOAA(self):
        return List(self._contents)
installConstructor(Accumulator)

accumulator_append = Accumulator.append
accumulator_getitem = Accumulator.__getitem__
accumulator_setitem = Accumulator.__setitem__
accumulator_delitem = Accumulator.__delitem__
accumulator_set = Accumulator.set

def accumulator_values(acc):
    return List(acc[:])

def accumulator_set_key_value(acc, key, value):
    "Remove any existing key-value pair for key and add a new key value pair"
    contents = acc._contents
    newpair = List((key, value))
    for i in range(len(contents)):
        if contents[i][0] == key:
            contents[i] = newpair
            return True
    contents.append(newpair)
    return True

class AccumulatorKeyValue(Imp, PredImpInt):
    """Predicate to test and set accumulator key-value pairs"""
    def solutions(self, agent, bindings, zitems):
        acc = termEvalErr(agent, bindings, zitems[0])
        for kv in acc._contents:
            if len(kv) == 2 \
               and termMatch(agent, bindings, zitems[1], kv[0]) \
               and termMatch(agent, bindings, zitems[2], kv[1]):
                yield SOLVED
    solution = PredImpInt.default_solution

    def conclude(self, agent, bindings, zitems):
        acc = termEvalErr(agent, bindings, zitems[0])
        key = termEvalErr(agent, bindings, zitems[1])
        value = termEvalErr(agent, bindings, zitems[2])
        accumulator_set_key_value(acc, key, value)

    def retractall(self, agent, bindings, zitems):
        acc = termEvalErr(agent, bindings, zitems[0])
        contents = acc._contents
        for i in range(len(contents)):
            kv = contents[i]
            if len(kv) == 2 \
               and termMatch(agent, bindings, zitems[1], kv[0]) \
               and termMatch(agent, bindings, zitems[2], kv[1]):
                contents[i] = None
        contents[:] = [x for x in contents if x is not None]
            
def add_to_list (x, l):
	new_l = list (l)
	new_l.append(x)
	return tuple(new_l)
	
def remove_from_list (x, l):
    new_l = list (l)
    new_l.remove(x)
    return tuple(new_l)

def remove_list_from_list (x, l):
    new_l = list (l)
    for el in x:
        if el in new_l:
            new_l.remove(el)
    return tuple(new_l)

# Flatten a list of list into a list of elements
def flatten_List(splist):
	result = []
	for element in splist:
		result.extend(list(element))
	return tuple(result)
	
def remove_Duplicates(x):
	result = []
	for element in x:
		if element not in result:
			result.append(element)
	return tuple(result)

def listify(x):
    if isList(x):
        return x
    else:
        return List((x,))


class ListFun(Imp, FunImpInt):
    __slots__ = ()

    def call(self, agent, bindings, zexpr):
        l = [termEvalErr(agent, bindings, zitem) for zitem in zexpr]
        return List(l)

    def match_inverse(self, agent, bindings, zexpr, obj):
        # require sequence type for obj
        if len(obj) != len(zexpr):
            return False
        else:
            for zitem, value in zip(zexpr, obj):
                if not termMatch(agent, bindings, zitem, value):
                    return False
            return True

class ListStar(Imp, FunImpInt):
    __slots__ = ()


    def call(self, agent, bindings, zexpr):
        l = [termEvalErr(agent, bindings, zitem) for zitem in zexpr]
        if not l:
            raise LocatedError(zexpr, "list* function requires at least one argument")
        else:
            result = l[:-1]
            try:
                result.extend(l[-1])
            except TypeError:
                raise LocatedError(zexpr, "Last argument to list* is not a sequence")
            return List(result)

    def match_inverse(self, agent, bindings, zexpr, obj):
        # require sequence type for obj
        try:
            temp = list(obj)
        except TypeError:
            return False
        numElements = len(zexpr) - 1
        if len(temp) < numElements:
            return False
        else:
            vals = temp[:numElements] + [List(temp[numElements:])]
            for zitem, value in zip(zexpr, vals):
                if not termMatch(agent, bindings, zitem, value):
                    return False
            return True

class StarList(Imp, FunImpInt):
    __slots__ = ()

    def call(self, agent, bindings, zexpr):
        l = [termEvalErr(agent, bindings, zitem) for zitem in zexpr]
        if not l:
            raise LocatedError(zexpr, "*list function requires at least one argument")
        else:
            try:
                temp = list(l[0])
            except TypeError:
                raise LocatedError(zexpr, "First argument to *list is not a sequence")
            return List(temp + l[1:])

    def match_inverse(self, agent, bindings, zexpr, obj):
        # require sequence type for obj
        try:
            temp = list(obj)
        except TypeError:
            return False
        numElements = len(zexpr) - 1
        if len(temp) < numElements:
            return False
        else:
            vals = [List(temp[:-numElements])] + temp[-numElements:]
            for zitem, value in zip(zexpr, vals):
                if not termMatch(agent, bindings, zitem, value):
                    return False
            return True
