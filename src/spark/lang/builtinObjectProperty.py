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
from __future__ import generators
from weakref import WeakKeyDictionary
from spark.internal.repr.common_symbols import P_ObjectProperty, P_ObjectPropertyChangeListener
from spark.pylang.implementation import Imp, PersistablePredImpInt, ImpGenInt
from spark.internal.parse.usagefuns import termEvalOpt, termEvalErr, termMatch
from spark.pylang.defaultimp import AddFactEvent, RemoveFactEvent
from spark.internal.common import SOLVED, NOT_SOLVED
from spark.internal.parse.basicvalues import *

NULLDICT = {}
def makeSequence(x):
    if x is None:
        return ()
    else:
        return (x,)
    
################################################################
# NOTES:
#
# There should be a tie-in with idobject, so that we only keep track
# of objects that are really necessary, saving the properties
# information on the object itself. For persistence, maybe we should
# write the ObjectProperty facts after all the other predicates are
# written (perhaps with, but after all the Object facts).
#
# Should only allow properties on constructible objects?


################################################################
################
####
#
# Python routines for accessing object properties
#

def getObjectProperty(agent, object, propertyName, default=None):
    "Returns the value of the propertyName property of object, or default if not set"
    d1 = agent.getInfo(P_ObjectProperty)
    return d1.get(object, NULLDICT).get(propertyName, default)

def setObjectProperty(agent, object, propertyName, value, kbResume=False):
    if (propertyName == EMPTY_SPARK_LIST): raise AssertionError
    return setObjectProperties(agent, object, ((propertyName, value),), kbResume)

def setObjectProperties(agent, object, nameValuePairs, kbResume=False):
    """Sets the value of the properties of object (or unsets the value if None).
    Calls associated property change listener functions as a side effect and posts events unless kbResume."""
    def callListeners(prop, val):
        listenerfactss = agent.factslist1(P_ObjectPropertyChangeListener, prop)
        for listenerfact in listenerfactss:
            listenerfact[1](agent, object, prop, val)
    # get the property list for object
    d1 = agent.getInfo(P_ObjectProperty)
    d2 = d1.get(object)
    if d2 is None:
        d2 = {}
        d1[object] = d2
    # Process each change
    changes = []
    for nv in nameValuePairs:
        # get the property name and value
        if len(nv) == 1:
            value = None
            nv = createList(nv[0], None)
        elif len(nv) == 2:
            value = nv[1]
            nv = List(nv)
        else:
            continue                    # ignore it
        propertyName = nv[0]
        # check the old value
        oldval = d2.get(propertyName)
        if oldval == value:
            continue
        # set the new value
        d2[propertyName] = value
        changes.append(nv)
        # post events and call property-specific listeners if not resuming
        if not kbResume:
            if oldval is not None:
                agent.post_event(RemoveFactEvent(P_ObjectProperty, (object, propertyName, oldval)))
            if value is not None:
                agent.post_event(AddFactEvent(P_ObjectProperty, (object, propertyName, value)))
            callListeners(propertyName, value)
    # call generic listeners 
    if changes and not kbResume:
        callListeners(EMPTY_SPARK_LIST, List(changes))

def getObjectProperties(agent, object, createDictIfNotPresent=False):
    """Returns a dict-like object that maps property names to values.
    Modifications will NOT call the listener functions or post events"""
    d1 = agent.getInfo(P_ObjectProperty)
    d2 = d1.get(object)
    if d2 is None and createDictIfNotPresent:
        d2 = {}
        d1[obj] = d2
    return d2

################################################################
################
####
#
# Helper function
    
def objectPropertySolutions(agent, bindings, zexpr, propname_given):
    "Generator that returns a tuple (obj, propname, val) for each solution"
    d1 = agent.getInfo(P_ObjectProperty)
    obj_iter = makeSequence(termEvalOpt(agent, bindings, zexpr[0]))
    propname_iter = makeSequence(propname_given)
    for obj in obj_iter or d1:
        d2 = d1.get(obj, NULLDICT)
        if d2 and (obj_iter or termMatch(agent, bindings, zexpr[0], obj)):
            for propname in propname_iter or d2:
                val = d2.get(propname)
                if val is not None \
                       and termMatch(agent, bindings, zexpr[2], val) \
                       and (propname_iter or termMatch(agent, bindings, zexpr[1], propname)):
                    yield (obj, propname, val)



################################################################
################
####
#
# Implementation of the ObjectProperty predicate 

class ObjectPropertyImp(Imp, PersistablePredImpInt):
    __slots__ = ()

    ################
    # Predicate implementation

    #PERSIST
    def persist_arity_or_facts(self, agent):
        return 3
    
    def generateInfo(self):
        return WeakKeyDictionary()
    
    def solution(self, agent, bindings, zexpr):
        if (len(zexpr) != 3): raise AssertionError
        for x in objectPropertySolutions(agent, bindings, zexpr, termEvalOpt(agent, bindings, zexpr[1])):
            return SOLVED
        return NOT_SOLVED

    def solutions(self, agent, bindings, zexpr):
        if (len(zexpr) != 3): raise AssertionError
        for tup in objectPropertySolutions(agent, bindings, zexpr, termEvalOpt(agent, bindings, zexpr[1])):
            yield SOLVED

    def retractall(self, agent, bindings, zexpr):
        if (len(zexpr) != 3): raise AssertionError
        removefacts = list(objectPropertySolutions(agent, bindings, zexpr, termEvalOpt(agent, bindings, zexpr[1])))
        for fact in removefacts:
            setObjectProperty(agent, fact[0], fact[1], None, False)

    #PERSIST
    def resume_conclude(self, agent, bindings, zexpr):
        self.conclude(agent, bindings, zexpr, True)

    def conclude(self, agent, bindings, zexpr, kbResume=False):
        if (len(zexpr) != 3): raise AssertionError
        obj_given = termEvalErr(agent, bindings, zexpr[0])
        prop_given = termEvalErr(agent, bindings, zexpr[1])
        val_given = termEvalErr(agent, bindings, zexpr[2])
        if prop_given == EMPTY_SPARK_LIST:
            setObjectProperties(agent, obj_given, val_given, kbResume)
        else:
            setObjectProperty(agent, obj_given, prop_given, val_given, kbResume)

################################################################
################
####
#
# Implementation of the ObjectProperty predicate 

class GenericImpGenImp(ImpGenInt):
    __slots__ = ("impClass",
                 "args",
                 )
    def __init__(self, impClass, *args):
        self.impClass = impClass
        self.args = args
    def __call__(self, decl):
        return self.impClass(decl, self.args)

class PyPropertyPredicateImp(ImpGenInt):
    __slots__ = ("propertyName",
                 )
    def __init__(self, propertyName):
        self.propertyName = propertyName
    def __call__(self, decl):
        return ObjectSpecificPropertyImp(decl, self.propertyName)



class ObjectSpecificPropertyImp(Imp, PersistablePredImpInt):
    __slots__ = ("propertyName",)

    def __init__(self, decl, propertyName):
        Imp.__init__(self, decl)
        self.propertyName = propertyName
    ################
    # Predicate implementation

    def persist_arity_or_facts(self, agent):
        # These predicates don't need to save anything beyond what is
        # saved by ObjectProperty
        return ()

    def solution(self, agent, bindings, zexpr):
        if (len(zexpr) != 2): raise AssertionError
        for x in objectPropertySolutions(agent, bindings, (zexpr[0], None, zexpr[1]), self.propertyName):
            return SOLVED
        return NOT_SOLVED

    def solutions(self, agent, bindings, zexpr):
        if (len(zexpr) != 2): raise AssertionError
        for tup in objectPropertySolutions(agent, bindings, (zexpr[0], None, zexpr[1]), self.propertyName):
            yield SOLVED

    def retractall(self, agent, bindings, zexpr):
        if (len(zexpr) != 2): raise AssertionError
        removefacts = list(objectPropertySolutions(agent, bindings, (zexpr[0], None, zexpr[1]), self.propertyName))
        for fact in removefacts:
            setObjectProperty(agent, fact[0], fact[1], None, False)

    #PERSIST
    def resume_conclude(self, agent, bindings, zexpr):
        if not (False): raise AssertionError, \
           "Should not be asserting anything"

    def conclude(self, agent, bindings, zexpr, kbResume=False):
        if (len(zexpr) != 2): raise AssertionError
        obj_given = termEvalErr(agent, bindings, zexpr[0])
        val_given = termEvalErr(agent, bindings, zexpr[1])
        setObjectProperty(agent, obj_given, self.propertyName, val_given, kbResume)


################################################################

# Testing routines

def printListener(agent, obj, prop, val):
    if val is None:
        print "Property removed:", obj, prop
    else:
        print "Property set:", obj, prop, val
