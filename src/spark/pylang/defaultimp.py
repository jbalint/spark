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
#* "$Revision:: 173                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from __future__ import generators
from spark.internal.version import *
from spark.internal.exception import Failure, LowError, Unimplemented
from spark.internal.common import delete_all, NEWPM, DEBUG, breakpoint, USE_WEAKDICT_NAME_TABLES, re_raise
from spark.internal.persist_aux import is_resume_block_concludes
from spark.internal.common import ABSTRACT, SOLVED, NOT_SOLVED

import weakref
import types

from spark.pylang.implementation import Imp, ActImpInt, PredImpInt, PersistablePredImpInt, FunImpInt, ImpGenInt
from spark.internal.repr.common_symbols import P_NewFact, P_Do, P_Features
from spark.internal.parse.basicvalues import Structure, isStructure, ConstructibleValue, Symbol, installConstructor, Value, value_str, inverse_eval
from spark.internal.repr.varbindings import valuesBZ
from spark.internal.parse.usagefuns import *

#from spark.internal.engine.compute import compute_2

debug = DEBUG(__name__)


class DefaultImp(Imp, PersistablePredImpInt, ActImpInt, FunImpInt):
    __slots__ = (
        "_detindices_lists",
        "_det_check_all", # must all factslists be tested for facts to retract?
        "_idsym",
        )

    def __init__(self, decl):
        Imp.__init__(self, decl)
        self._detindices_lists = ()
        self._det_check_all = False
        self._idsym = Symbol(self.symbol.id)

    ################
    # Function implementation

    def call(self, agent, bindings, zexpr):
        args = [termEvalErr(agent, bindings, zitem) for zitem in zexpr]
        return self._idsym.structure(*args)

    def match_inverse(self, agent, bindings, zexpr, obj):
        if not isStructure(obj):
            return False
        if obj.functor != self._idsym:
            return False
        length = len(obj)
        if length != len(zexpr):
            return False
        i = 0
        while i < length:
            if not termMatch(agent, bindings, zexpr[i], obj[i]):
                return False
            i += 1
        return True

    ################
    # Action implememtation

    def tframes(self, agent, event, bindings, zexpr):
        return get_all_tframes(agent, event, bindings, P_Do, self.symbol, zexpr)
    
    ################
    # Predicate implementation

    #PERSIST
    def persist_arity_or_facts(self, agent):
        return agent.factslist0(self.symbol)
    
    def generateInfo(self):
        return {}
    
    def solution(self, agent, bindings, zexpr):
        for x in self.solutions(agent, bindings, zexpr):
            if x:
                return SOLVED
        return NOT_SOLVED
    
    def solutions(self, agent, bindings, zexpr):
        d = agent.getInfo(self.symbol)
        nargs = len(zexpr)
        if nargs == 0:
            if d.get(None):   # a list containing a single empty tuple
                yield SOLVED
        else:
            val0 = termEvalOpt(agent, bindings, zexpr[0])
            if val0 is not None:
                for x in self._solutions_aux(agent, bindings, val0, zexpr, nargs, d):
                    yield x
            else:
                for val0 in d:
                    if val0 is not None and termMatch(agent, bindings, zexpr[0], val0):
                        for x in self._solutions_aux(agent, bindings, val0, zexpr, nargs, d):
                            yield x
                        
    def _solutions_aux(self, agent, bindings, val0, zexpr, nargs, d):
        for fact in d.get(val0, ()):
            if nargs == len(fact):
                i = 1
                while i < nargs:
                    if not termMatch(agent, bindings, zexpr[i], fact[i]):
                        break
                    i += 1
                else:                   # no arg match failed
                    yield SOLVED

    def retractall(self, agent, bindings, zexpr):
        d = agent.getInfo(self.symbol)
        if len(zexpr) > 0:
            val0 = termEvalOpt(agent, bindings, zexpr[0])
            if val0 is not None:
                if val0 in d:
                    self._retract_matching_facts(agent, bindings, val0, zexpr, d)
            else:
                for key in d.keys():
                    if termMatch(agent, bindings, zexpr[0], key):
                        self._retract_matching_facts(agent, bindings, key, zexpr, d)
        else:
            factslist = d.get(None, ())
            if factslist:
                event = RemoveFactEvent(self.symbol, factslist[0])
                agent.post_event(event)
                del factslist[:]

    #PERSIST
    def resume_conclude(self, agent, bindings, zexpr):
        self.conclude(agent, bindings, zexpr, True)
    
    def conclude(self, agent, bindings, zexpr, kbResume=False):
        d = agent.getInfo(self.symbol)
        if (d is None): raise AssertionError
        #PERSIST
        #have to 'fake' conclude during resuming so that objectIds are set
        #properly and can be mapped during the persist_kb().
        #TODO: redo the loadFacts flag check to make sure that we only
        #call conclude on PersistablePredImpInts
        from spark.internal.persist_aux import is_resume_block_concludes
        if is_resume_block_concludes() and not kbResume:
            for z in zexpr:
                termEvalErr(agent, bindings, z)#generate objects (will be stored using objectId, so we don't need to cache)
            return

        if len(zexpr) > 0:
            newfact = tuple([termEvalErr(agent, bindings, z) for z in zexpr])                
            #print " CONCLUDING", self.symbol, str(newfact)
            key = newfact[0]
            if self._detindices_lists:          # may need to deleted things
                if self._det_check_all: # need to check all factslists
                    for key1 in d.keys():
                        self._retract_similar_facts(agent, key1, newfact, d, kbResume)
                elif key in d:
                    self._retract_similar_facts(agent, key, newfact, d, kbResume)
        else:
            newfact = ()
            #print " CONCLUDING", self.symbol, newfact
            key = None
        try:
            factslist = d[key]
        except KeyError:
            factslist = []
            d[key] = factslist
        if newfact not in factslist:
            factslist.append(newfact)
            #PERSIST
            if not kbResume: #don't generate events on a resume
                agent.post_event(AddFactEvent(self.symbol, newfact))

    def _retract_matching_facts(self, agent, bindings, val0, zexpr, d, kbResume=False):
        facts = d[val0]
        length = len(facts)
        arity = len(zexpr)
        i = 0
        some_deleted = False
        while i < length:
            oldfact = facts[i]
            if len(oldfact) != arity:  # allow different arities
                continue
            j = 1
            while j < arity:
                if not termMatch(agent, bindings, zexpr[j], oldfact[j]):
                    break               # continue with next fact
                j = j + 1
            else:
                #self._retracts.append(oldfact)
                #PERSIST
                if not kbResume:
                    from spark.pylang.defaultimp import RemoveFactEvent
                    agent.post_event(RemoveFactEvent(self.symbol, oldfact))
                facts[i] = None
                some_deleted = True
            i = i + 1
        if some_deleted:
            delete_all(facts, None)
            if not facts:
                del d[val0]

    def _retract_similar_facts(self, agent, val0, newfact, d, kbResume=False):
        facts = d[val0]
        length = len(facts)
        arity = len(newfact)
        i = 0
        some_deleted = False
        while i < length:
            oldfact = facts[i]
            if len(oldfact) != arity:  # allow different arities
                continue
            for detindices in self._detindices_lists:
                for index in detindices:
                    if newfact[index] != oldfact[index]:
                        break           # continue with next detmode
                else:
                    #PERSIST
                    if not kbResume:                    
                        agent.post_event(RemoveFactEvent(self.symbol, oldfact))
                    #self._retracts.append(oldfact)
                    facts[i] = None
                    some_deleted = True
                    break               # continue with next old
            i = i + 1
        if some_deleted:
            delete_all(facts, None)
            if not facts:
                del d[val0]




class DeterminedPredImp(ImpGenInt):
    __slots__ = ("_detindices_lists",
                 "_det_check_all",
                 )
    def __init__(self, *detstrings):
        from spark.internal.repr.mode import RequiredMode
        self._detindices_lists = [RequiredMode(detstring).required_indices() \
                                  for detstring in detstrings]
        self._det_check_all = False
        for detindices in self._detindices_lists:
            if 0 not in detindices:     # i.e., detmode == "-..."
                self._det_check_all = True
        
    def __call__(self, decl):
        imp = DefaultImp(decl)
        imp._detindices_lists = self._detindices_lists
        imp._det_check_all = self._det_check_all
        return imp

# class DeterminedPredImp(ImpGenInt):
#     __slots__ = ("_detstrings",)
#     def __init__(self, *detstrings):
#         self._detstrings = detstrings
#     def __call__(self, sym):
#         return BasePredImp(sym, self._detstrings)
                           
            


################################################################



def mybreak():
    raise Exception("break")

def get_all_tframes(agent, event, bindings, cuesymbol, sym, zexpr):
    """Return a sequence of tframes from procedures stored in predicate
    (<cuesymbol> <sym> <proc> ...)."""
    #collector = TFramesCollector()
    tframes = []
    try:
        relevant = agent.factslist1(cuesymbol, sym)
    except LowError, e:
        # Handle the case at startup where we have newfact events
        # occurring, but there is no NewFact predicate yet
        if cuesymbol != P_NewFact:
            re_raise()
        relevant = ()
    #print "  Relevant:",[x[1].name() or mybreak() for x in relevant]
    for procedure_fact in relevant:
        procedure = procedure_fact[1]
        #collector.set_procedure(procedure, event)
        #b = procedure.make_bindings(agent, bindings, zexpr)
        #compute_2(agent, b, procedure, collector)
        procedure.append_tframes(agent, event, bindings, zexpr, tframes)
    #print "  Applicable:",[x._procedure.name() for x in tframes]
    return tframes


def id_event(id):
    try:
        return SparkEvent._weakdict[id]
    except KeyError:
        return None

class SparkEvent(ConstructibleValue):                       
    __slots__ = (
        #"__weakref__",
        "_name",
        )
    eventKind = "UNKNOWN"
    name_base = "SparkEvent"
    _weakdict = weakref.WeakValueDictionary()
    idCounter = 0
    
    cvcategory = "E"
    def cvname(self):
        return self.goalsym().id

    def goalsym(self):
        raise Unimplemented("subclass must define goalsym method")

    def __init__(self, name):
        #self.time = time.time()
        ConstructibleValue.__init__(self)
        if name is None:
            SparkEvent.idCounter += 1
            name = "%s%d"%(self.name_base, SparkEvent.idCounter)
        else:
            if not (isinstance(name, basestring)): raise AssertionError
        self._name = name
        if USE_WEAKDICT_NAME_TABLES:        
            self._weakdict[name] = self
    
    def name(self):
        return self._name
    
    def find_tframes(self, agent):
        raise Unimplemented()

    def e_solver_target(self):  # by default not a solver
        return None

    def e_sync_parent(self):    # by default asynchronous
        return None

    def is_solver(self):
        return self.e_solver_target()        # default

    def features(self, agent):
        try:
            sym = self.goalsym()
            if sym.modname is None:  # DNM - Hack for @exteval
                return ()
            facts = agent.factslist1(P_Features, sym)
            if facts:
                return facts[0][1]
            else:
                return ()
        except:
            NEWPM.displayError()
            return ()

    def constructor_args(self):
        return [self._name]
    constructor_mode = "V"

installConstructor(SparkEvent)

class ObjectiveEvent(SparkEvent):
    __slots__ = ("base",)
    name_base = "Objective"
    cvcategory = "EO"
    def __init__(self, base):
        SparkEvent.__init__(self, None)
        self.base = base

    def constructor_args(self):
        return [self.base]
    constructor_mode = "I"

    def e_sync_parent(self):
        # This is an asynchronous event
        return None

    def e_solver_target(self):
        # Although this event is async, we want to notify base on a result
        return self.base

    def is_solver(self):
        return True

    def constructor_args(self):
        return [self.base]
    constructor_mode = "I"
installConstructor(ObjectiveEvent)


class FactEvent(SparkEvent):
    __slots__ = (
        "_symbol",
        "_fact",                        # tuple of args
        )
    cvcategory = "EF"
    def __init__(self, predicate_symbol, fact):
        SparkEvent.__init__(self, None)
        self._symbol = predicate_symbol
        self._fact = fact

    def getArgs(self, agent):
        return self._fact
    
    def getStructure(self, agent):
        return Structure(self._symbol, self._fact)

    def e_solver_target(self):
        return None

    def is_solver(self):
        return False

    def e_sync_parent(self):
        return None

    def __repr__(self):
        try:
            if self._fact:
                return "<%s%s %s>"%(self.estring, self._symbol.id, " ".join([`x` for x in self._fact]))
            else:
                return "<%s%s>"%(self.estring, self._symbol.id)
        except:
            return object.__repr__(self)
    def constructor_args(self):
        return [self._symbol, self._fact]
    constructor_mode = "VV"
installConstructor(FactEvent)
        

class AddFactEvent(FactEvent):
    __slots__ = ()
    estring = "+"
    name_base = "AddFact"
    eventKind = "NEWFACT"
    
    def find_tframes(self, agent):
        b, z = valuesBZ(self._fact)
        sym = self._symbol
        return get_all_tframes(agent, self, b, P_NewFact, sym, z)
    def kind_string(self):
        return P_NewFact.id
    def goalsym(self):
        return self._symbol
    def bindings(self):
        return valuesBZ(self._fact)[0]
    def zexpr(self):
        return valuesBZ(self._fact)[1]
installConstructor(AddFactEvent)


class MetaFactEvent(AddFactEvent):
    __slots__ = ()
    estring = "++"
    numargs = ABSTRACT
    event_type = ABSTRACT
    def __init__(self, *args):
        if (len(args) != self.numargs): raise AssertionError, \
               "expecting %d arguments, not %d"%(self.numargs, len(args))
        AddFactEvent.__init__(self, self.event_type, args)
        # should assert that every element of tframes was triggered by event
    def constructor_args(self):
        event_opt_reason = AddFactEvent.constructor_args(self)[1]
        return list(event_opt_reason)
    def base_tframe(self):      # override in subclasses
        return None
    def e_sync_parent(self):
        return self.base_tframe()
    def base_event(self):
        raise Unimplemented()
installConstructor(MetaFactEvent)

class RemoveFactEvent(FactEvent):
    __slots__ = ()
    estring = "-"

    def find_tframes(self, agent):
        return []  # DNM - for now, we cannot trigger off fact removal
    def kind_string(self):
        return "Removefact"
    def goalsym(self):
        return self._symbol
    def bindings(self):
        return valuesBZ(self._fact)[0]
    def zexpr(self):
        return valuesBZ(self._fact)[1]
installConstructor(RemoveFactEvent)
