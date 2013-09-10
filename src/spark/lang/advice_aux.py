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

from types import IntType

from spark.internal.version import *
from spark.internal.exception import Unimplemented

from spark.internal.parse.basicvalues import Symbol
from spark.internal.repr.taskexpr import GoalMetaEvent
from spark.internal.repr.common_symbols import APPLIED_ADVICE
from spark.internal.parse.basicvalues import installConstructor

from spark.pylang.defaultimp import SparkEvent

#ADVICE = Symbol("spark.builtin.Advice")

ADVICE_WEIGHT = {"strong_prefer":10000,
                 "strong_avoid":-10000,
                 "prefer":100,
                 "avoid":-100,
                 "weak_prefer":1,
                 "weak_avoid":-1}


class AppliedAdviceEvent(GoalMetaEvent):
    __slots__ = ()
    numargs = 2
    event_type = APPLIED_ADVICE
installConstructor(AppliedAdviceEvent)

def calc_weight(kind):
    if isinstance(kind, IntType):
        weight = kind
    else:
        weight = ADVICE_WEIGHT[kind.id]
    return weight
    
def resolveAdvice(agent, tframes, advice, event):
    #print "resolveAdvice", (agent, tframes, advice, event)
    values = {}
    for tframe in tframes:
        values[tframe] = 0
    for (tf, label, kind) in advice:
        values[tf] = values[tf] + calc_weight(kind)
    max = -999999
    best = []
    for (tf, sum) in values.items():
        if sum > max:
            del best[:]
            max = sum
            best.append(tf)
        elif sum == max:
            best.append(tf)
    advice_used = []
    advice_gone_against = []
    for (tf, label, kind) in advice:
        if tf in best:
            if calc_weight(kind) > 0:
                pushnew(advice_used, label)
            else:
                pushnew(advice_gone_against, label)
        else:
            if calc_weight(kind) > 0:
                pushnew(advice_gone_against, label)
            else:
                pushnew(advice_used, label)
    for label in advice_used:
        agent.post_event(AppliedAdviceEvent(event, label))
    #print "Advice", tframes, "->", best
    return tuple(best)

def myprint(format, *args):
    done = False
    try:
        print_str = format%args
        print print_str
        done = True
    finally:
        if not done:
            print "ERROR IN PRINT ACTION: format=%r, args=%r" % (format, args)
    return done

#       print format%args
#       return True

def pushnew(list, element):
    if element not in list:
        list.append(element)

def get_features(agent, object):
    features = object.features(agent)
    #print "features(%r)->%r"%(object, features)
    #from spark.common import breakpoint
    #breakpoint()
    return features
