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
#* "$Revision:: 309                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from __future__ import generators
import threading
import sys
from sets import Set
from Queue import Queue

from spark.internal.version import *
from spark.internal.common import paranoid, NEWPM, DEBUG, ABSTRACT, SOLVED
from spark.internal.init import is_persist_state, is_persist_intentions
from spark.internal.persist_aux import set_resuming, is_resuming, is_reload_process_models


# from spark.internal.persist import persist_report_load_modpath, persist_report_load_string

from spark.internal.instrument import report_instrumentation_point, OBJECTIVE_COMPLETED, SPARK_SHUTDOWN, NEWFACT_COMPLETED
     
from spark.pylang.implementation import ImpInt, PersistablePredImpInt, Imp
from spark.pylang.defaultimp import AddFactEvent, RemoveFactEvent, SparkEvent, \
     MetaFactEvent, ObjectiveEvent, FactEvent

from spark.internal.engine.core import Internal, External, Test
#from spark.internal.engine.compute import compute_2
from spark.internal.engine.find_module import drop_modpath, ensure_modpath_installed

from spark.internal.parse.basicvalues import Symbol, isSymbol, STANDARD_ID_SAVE
from spark.internal.parse.usages import TERM_EVAL, PRED_SOLVE, TASK_EXECUTE
#from spark.module_symbols import FUN_IMP_GEN, PRED_IMP_GEN, ACT_IMP_GEN
from spark.internal.exception import SignalFailure, NoGoalResponseFailure, LowError, ExceptionFailure, LocatedError, InternalException
from spark.internal.repr.taskexpr import TaskExprTFrame, SUCCESS, TFrame, \
     GoalPostedEvent, GoalSucceededEvent, GoalFailedEvent
from spark.internal.repr.common_symbols import SOAPI, P_LoadedFileFacts
from spark.internal.parse.basicvalues import ConstructibleValue, installConstructor, List, value_str
from spark.internal.parse.processing import load_file_into_agent, load_decls_into_agent, SPUBindings, printErrors
from spark.internal.repr.varbindings import valuesBZ, optBZ
from spark.internal.parse.expr import EXPR_IMPS
from spark.internal.parse.usagefuns import *
from spark.util.logger import get_sdl    

#import spark.lang.builtin                 # ensure builtin module loaded
import spark.internal.version
if spark.internal.version.isPython:
    import gc #Python garbage collector interface
elif spark.internal.version.isJython:
    from java.lang import System
    
debug = DEBUG(__name__)#.on()

#@-timing# from spark.internal.timer import TIMER
#@-# T_iterate = TIMER.newRecord("iterate")
#@-# T_process_tframe = TIMER.newRecord("process_tframe")
#@-# T_leaf_tframe_tfcont = TIMER.newRecord("leaf_tframe_tfcont")
#@-# T_executor = TIMER.newRecord("executor")
#@-# T_wait = TIMER.newRecord("wait")
#@-# T_gc = TIMER.newRecord("gc")



AGENTS = {}                             # dict mapping agent names to agents

SAFE_ACTIVITY_CHECKING = True
IDLE_WAIT_TIME = 10.0 # How many seconds we wait in Agent.iterate before we consider ourselves idle

#list of objective symbol names which we explicitly do not persist
NON_PERSISTING_OBJECTIVES = ['spark.io.oaa.agentStatus', 'task_manager.subscribeTmTodos', 'task_manager.tmUiUserUid', 'iris.events.psReceiveControlUnsub', 'iris.events.psReceiveControlSub', 'iris.events.psReceivePub', 'calendar_manager.ptime_processes.potential_location', 'calendar_manager.ptime_processes.potential_participant', 'calo.multicalo_handler.inform_calo']
#The desire manager ones should be persisted, but they hammer performance too much right now
NON_PERSISTING_NEWFACTS = ['spark.io.oaa.OnlineAgent', 'iris.events.ControlMessageSubscribe', 'iris.events.PubSubInitialized', 'calendar_manager.ptime_data.InitiateDCOP', 'calo.user.User', 'iris.events.PubSubSubscription'] 

#Testing Script. Begin:
#from spark.internal.debug.chronometer import chronometer, chronometers, print_chronometers, reset_chronometers
#chronometers["process_tframe"] = chronometer("process_tframe")
#chronometers["process_events"] = chronometer("process_events")
#Testing Script. End.

################################################################
# IntentionStructure

MAX_SOAPI_DEPTH = 5                      # maximum number of soapi iterations

class LeafQueue(object):
    """A list of objects that can also act as an iterator over itself.

    Advantage over ordinary lists: If an element is added while the
    list is being iterated over, that element will appear in the
    iteration. Similarly, if an element is removed while the list is
    being iterated over, then that element will not appear in the
    remainder of the iteration and no other elements will be skipped.

    Disadvantage with respect to ordinary lists: As this is its own
    iterator, there can only be one iterator at any time.

    Assumes single-threaded access.
    """
    __slots__ = (
        "_list",
        "_pos"                          # position within list
        )

    def __init__(self):
        self._list = []
        self._pos = None

    def __iter__(self):
        if self._pos is not None:
            raise LowError("Cannot use LeafQueue as more than one iterator at a time")
        self._pos = 0
        return self

    def next(self):
        l = self._list
        p = self._pos
        if p is None or p >= len(l):
            self._pos = None
            raise StopIteration
        else:
            val = l[p]
            self._pos = p + 1
            return val

    def add(self, value):
        #print " adding leaf", value
        self._list.append(value)

    def remove(self, value):
        #print " removing leaf", value
        i = self._list.index(value)
        #print self._list, i
        del self._list[i]
        p = self._pos
        if p is not None and p > i:
            self._pos = p - 1           # adjust for deleted element
        #print self._list

    def __contains__(self, x):
        return x in self._list

    def __len__(self):
        return len(self._list)

    def __repr__(self):
        return "<LeafQueue %s>"%self._list

class IntentionStructure(object):
    __slots__ = (
        "_root_tframes",
        "_leaf_tframes",
        "_tframe_children",
        #"_tframe_monitors",
        )

    def __init__(self):
        self._root_tframes = []
        self._leaf_tframes = LeafQueue()
        self._tframe_children = {}
        #self._tframe_monitors = {}

    def __repr__(self):
        return "<roots: %s leaves: %s>"%(self._root_tframes, self._leaf_tframes)

    def leaf_iterator(self):
        """Return something to iterate over the leaves (i.e., intended
        TFrames with no children). Note that you may only have one
        iterator at a time, but it does allow new leaves to be added
        and old leaves to be removed during the iteration"""
        return self._leaf_tframes

    def tframe_children(self, tframe):
        "Returns a sequence of the children of the TFrame"
        return self._tframe_children[tframe]

    def add_tframe(self, parent, tframe):
        "Adds tframe (add as child if tframe has a parent)"
        #debug("add_tframe(%s, %s)", parent, tframe)
        tframe_children = self._tframe_children
        if (tframe_children.has_key(tframe)): raise AssertionError
        if parent is None:
            self._root_tframes.append(tframe)
        else:
            parents_children = tframe_children.get(parent, None)
            if (parents_children is None): raise AssertionError
            if len(parents_children) == 0:
                self._leaf_tframes.remove(parent)
            parents_children.append(tframe)
        self._leaf_tframes.add(tframe)
        tframe_children[tframe] = []
        #debug("add_tframe() done")

    def replace_tframe(self, parent, oldtframe, newtframe):
        "Substitutes newtframe for oldtframe"
        #debug("replace_tframe(agent, %s, %s)", oldtframe, newtframe)
        tframe_children = self._tframe_children
        children = tframe_children.get(oldtframe, None)
        if (children is None): raise AssertionError, \
            "oldtframe not intended"
        if (tframe_children.has_key(newtframe)): raise AssertionError, \
            "new tframe already intended"
        if parent is None:
            if not (oldtframe in self._root_tframes): raise AssertionError
            self._root_tframes.remove(oldtframe)
            self._root_tframes.append(newtframe)
        else:
            parents_children = tframe_children.get(parent, None)
            if (parents_children is None): raise AssertionError, \
                "parent tframe is not intended"
            if not (oldtframe in parents_children): raise AssertionError, \
                "oldtframe is not listed as a child of its parent"
            parents_children.remove(oldtframe)
            parents_children.append(newtframe)
        if len(children) > 0:
            for child in children:
                child.tf_set_sync_parent(newtframe)
        else:
            self._leaf_tframes.remove(oldtframe)
            self._leaf_tframes.append(newtframe)
        del tframe_children[oldtframe]
        tframe_children[newtframe] = children

    def remove_tframe(self, ignore_agent, tframe):
        "Removes tframe from its parent"
        #debug("remove_tframe(agent, %s)", tframe)
        tframe_children = self._tframe_children
        children = tframe_children.get(tframe, None)
        if (children is None): raise AssertionError
        if (len(children) != 0): raise AssertionError, \
               "Trying to remove a TFrame with children"
        if not (tframe in self._leaf_tframes): raise AssertionError, \
               "Trying to remove a TFrame that is not a leaf"
        parent = tframe.tf_sync_parent()
        if parent is None:
            if not (tframe in self._root_tframes): raise AssertionError
            self._root_tframes.remove(tframe)
        else:
            parents_children = tframe_children.get(parent, None)
            if (parents_children is None): raise AssertionError
            if not (tframe in parents_children): raise AssertionError
            parents_children.remove(tframe)
            if len(parents_children) == 0:
                self._leaf_tframes.add(parent)
        self._leaf_tframes.remove(tframe)
        del tframe_children[tframe]
        #debug("remove_tframe() done")
        #tframe.remove_all_monitors(agent)

    def get_root_tframes(self):
        return self._root_tframes

    def append_tframe_descendants(self, tframe, list):
        children = self.tframe_children(tframe)
        for child in children:
            list.append(child)
            self.append_tframe_descendants(child, list)

################################################################
class CurrentlyIntended(Imp, PersistablePredImpInt):
    __slots__ = ()

    def currentlyIntendedList(self, agent):
        list = []
        intention_structure = agent._intention_structure
        for root in intention_structure.get_root_tframes():
            list.append(root)
            intention_structure.append_tframe_descendants(root, list)
        return list
        
    def persist_arity_or_facts(self, agent):
        if is_persist_intentions():
            print "PERSISTING INTENTION STRUCTURE"
            return 1 #[(tframe,) for tframe in self.currentlyIntendedList(agent)]
        else:
            return ()

    def solutions(self, agent, bindings, zexpr):
        for tframe in self.currentlyIntendedList(agent):
            if termMatch(agent, bindings, zexpr[0], tframe):
                yield SOLVED
                #bindings.bfound_solution(agent, zexpr)

    def resume_conclude(self, agent, bindings, zexpr):
        self.conclude(agent, bindings, zexpr)

    def conclude(self, agent, bindings, zexpr):
        tframe = termEvalErr(agent, bindings, zexpr[0])
        agent.add_tframe(tframe)

    def retractall(self, agent, bindings, zexpr):
        cil = self.currentlyIntendedList(agent)
        cil.reverse()
        for tframe in cil:
            if termMatch(agent, bindings, zexpr[0], tframe):
                agent.remove_tframe(tframe)
                

                        
        

################################################################

class ExternalEvent(External):
    __slots__ = (
        "_event",
        )
    def __init__(self, event):
        External.__init__(self)
        self._event = event

    def perform(self, agent):
        agent.post_event(self._event)

    constructor_mode = "I"
    def constructor_args(self):
        return [self._event]

installConstructor(ExternalEvent)


#PERSIST: used to raise the NewSparkAgent/SparkAgentRestored ephemeral predicates

class InternalRaisePersistFlags(Internal):
    """An internally driven conclude that raises the AgentRestored flag."""
    __slots__ = ("_agent",  "_sym", )

    def __init__(self, agent, sym):
        self._agent = agent
        self._sym = sym

    def perform(self, agent):
		self._agent.add_ephemeral(self._sym, self._agent.name)
        #pass

#PERSIST: used to reconclude facts on a resume where the original
#fact could not be concluded
class InternalConclude(Internal):
    """An internally driven conclude/adjustment of knowledge base state that
    nevertheless generates add/remove events. An internal conclude might result,
    for example, from alterations made to the knowledge base state after
    resuming from a persisted state."""
    __slots__ = ("_imp", "_bindings", "_zexpr", )

    def __init__(self, imp, bindings, zexpr):
        self._imp = imp
        self._bindings = bindings
        self._zexpr = zexpr

    def perform(self, agent):
        self._imp.conclude(agent, self._bindings, self._zexpr)
        agent.setChanged()


#class TestExternalExprMixin(object):
class TestExternalExprMixin:
# NOTE: a mixin class should not declare slots - it leads to layout-conflict
# adding a __dict__ by not specifying any slots is okay.
# #DNM: 2007-01-31 it isn't okay any more -
# #     jython changed to disallow this and require old-style classes for mixins
#     __slots__ = (
#         "expr",
#         "sparklUnit",
#         "bindings",
#         "modpath",
#         "thread_event",
#         "result",
#         "bindsvars",
#         "_dict",
#         #"varvalues",
#         )

    expr_usage = ABSTRACT
    def __init__(self, text, modpath, saveSparklUnit=False):
        """text is the SPARK-L source text.
        modpath is the SPARK modpath to interpret the source text in.
        varvalueslist is the sequence of tuples mapping argument names to
        values (argument names should be of the form 'foo', not '$foo'.
        saveSparklUnit is a flag passed to the SparklUnit creation
        that indicates whether or not the module system is allowed to
        keep a reference to the SparklUnit (i.e. for purposes of
        mapping loadIds to SparklUnits). We do not want to keep
        references to SparklUnits created for tests and evals."""
        self.modpath = modpath
        #self.load_modpath(modpath)
        #module = ensure_modpath_installed(modpath)
        #newdict = dict([("$"+x, v) for x,v in varvalueslist])
        from spark.internal.parse.processing import StringSPU
        #vbbefore = Set([Variable(varname) for varname in newdict.keys()])
        spu = StringSPU(str(modpath)).textUpdate(None, text)
        #freevars = spu.process(self.expr_usage, vbbefore, is_persist_state() and saveSparklUnit)
        #freevars = spu.stageOneprocess(self.expr_usage, Set(), is_persist_state() and saveSparklUnit)
        # TODO: must fix persistence side
        from spark.internal.parse.errormsg import OK0
        if not spu.atLeast(OK0):
            raise AssertionError, "Could not parse the string"
        freevars = spu.process(self.expr_usage)
        if freevars is None:
            printErrors(spu, True)
            raise AssertionError, "There was an error processing the string"
        if len(spu) == 1:
            self.expr = spu[0]
        else:
            raise AssertionError, "The string did not contain exactly one term"
        self.spu = spu                  # keep the SPU around otherwise getSPU on the expr will fail
        #self.bindsvars = freevars.difference(vbbefore)
        self.bindsvars = freevars
        #XPERSIST - moved into newparse
        #if is_persist_state() and saveSparklUnit:
        #    console_persist(self.sparklUnit)
        
        #self.expr.process(newdict.keys())
        self._dict = {} # newdict
        #self.bindings = DictBindings(newdict)
        self.thread_event = threading.Event()
        self.result = None

    def setBindings(self, agent):
        spu = ensure_modpath_installed(self.modpath)
        self.bindings = SPUBindings(agent, spu)
        self.bindings.setVariables(self._dict)

    def wait_result(self, timeout=None):
        self.thread_event.wait(timeout)
        return self.result              # None if timeout

    def isWaiting(self):
        return not self.thread_event.isSet()

    def completed(self):
        return self.result

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.expr)


class TestEvalExpr(Test, TestExternalExprMixin):
    __slots__ = ()

    def __init__(self, text, modpath):
        Test.__init__(self)
        TestExternalExprMixin.__init__(self, text, modpath)

    expr_usage = TERM_EVAL
    
    def perform(self, agent):
        try:
            #debug("EVAL - agent.load_modpath(%s)", type(self.modpath))
            agent.load_modpath(self.modpath)
            self.setBindings(agent)
            #self.sparklUnit.load_decls_into_agent(agent)
            #self.sparklUnit.load_facts_into_agent(agent)
            #debug("performing eval")
            #from spark.internal.common import breakpoint
            #breakpoint()
            self.result = termEvalErr(agent, self.bindings, self.expr)
            #debug("performed eval -> %r", self.result)
        finally:
            if self.result is None:
                print "ERROR PERFORMING EVAL, SETTING RESULT TO 0"
                self.result = 0
            self.thread_event.set()
        
class TestTestExpr(Test, TestExternalExprMixin):
    __slots__ = (
        "outvarids",
        )

    def __init__(self, text, modpath):
        Test.__init__(self)
        TestExternalExprMixin.__init__(self, text, modpath)

    expr_usage = PRED_SOLVE

    def perform(self, agent):
        try:
            #debug("TEST - agent.load_modpath(%s)", self.modpath)
            agent.load_modpath(self.modpath)
            self.setBindings(agent)
            #self.sparklUnit.load_decls_into_agent(agent)
            #self.sparklUnit.load_facts_into_agent(agent)
            vars = list(self.bindsvars)
            vars.sort()
            bindings = self.bindings
            result = []
            for x in predSolve(agent, bindings, self.expr):
                if x:
                    sol = [bindings.getVariableValue(agent, var) for var in vars]
                    result.append(tuple(sol))
            self.result = result
            self.outvarids = [str(var) for var in vars]
        finally:
            self.thread_event.set()

#     def perform(self, agent):
#         try:
#             #debug("TEST - agent.load_modpath(%s)", self.modpath)
#             agent.load_modpath(self.modpath)
#             self.sparklUnit.load_decls_into_agent(agent)
#             self.sparklUnit.load_facts_into_agent(agent)
#             self.outvarids = self.expr.free_nblocals_used_first_here().elements()
#             self.result = []
#             compute_2(agent, self.bindings, self.expr, self)
#         finally:
#             self.thread_event.set()

#     def compute(self, agent, _bindings):
#         sol = [self.bindings.get_either(varid) for varid in self.outvarids]
#         self.result.append(tuple(sol))

    def printme(self):
        count = 1
        #mod = ensure_modpath_installed(self.modpath) # will look up modpath
        for sol in self.result:
            print "%d."%count,
            for varid,val in zip(self.outvarids, sol):
                print "%s:"%varid, value_str(val),
            count = count + 1
            print


class EREEvent(ObjectiveEvent):
    __slots__ = ()

    def getParams(self):
        return ()
    def find_tframes(self, agent):
        # There is a single tframe to respond to this event, a TaskExprTFrame
        name = "External.%d"%agent.nextid()
        return [ERETFrame(name, self, self.base.bindings, self.base.expr)]

    def bindings(self):
        return valuesBZ((str(self.base.expr),))[0]
    def zexpr(self):
        return valuesBZ((str(self.base.expr),))[1]
    def goalsym(self):
        return Symbol("exteval")
    def getTaskResultArgs(self, agent): # DNM - for Mei
        bindings = self.base.bindings
        exprs = self.base.expr[0]
        return List([termEvalEnd(agent, bindings, e) for e in exprs])
    def getArgs(self, agent): # DNM - for Ken
        bindings = self.base.bindings
        exprs = self.base.expr[0]
        return List([termEvalOpt(agent, bindings, e) for e in exprs])
    def kind_string(self):
        return "Do"

installConstructor(EREEvent)

class ERETFrame(TaskExprTFrame):
    __slots__ = ()
installConstructor(ERETFrame)

class ExternalRunExpr(External, TestExternalExprMixin):
    """An ExternalTaskExpr is an external influence that is also
    a solver_target."""
    __slots__ = (
        "_text",
        "_modpath",
        )

    def __init__(self, text, modpath, saveSparklUnit=False):
        External.__init__(self)
        #True signifies that we always save the SparklUnit generated
        #for ExternalRunExprs
        TestExternalExprMixin.__init__(self, text, modpath, saveSparklUnit)
        self._text = text
        self._modpath = modpath

    def constructor_args(self):
        return (self._text, self._modpath)
    constructor_mode = "VV"

    def state_args(self):
        result = self.result
        if result is not None:
            return (result,)
        else:
            return ()

    def set_state(self, ignore_agent, result):
        self.result = result
        self.thread_event.set()

    expr_usage = TASK_EXECUTE

    # External method
    def perform(self, agent):
        try:
            agent.load_modpath(self.modpath)
            self.setBindings(agent)
            #debug("loading source into agent")
            #self.sparklUnit.load_decls_into_agent(agent)
            #self.sparklUnit.load_facts_into_agent(agent)
            
            #PERSIST
            #report that a specific agent has loaded in a console source into it's KB
#             if is_persist_state():
# 				#TODO: PERSISTBROKEN: NO SPARKLUNIT
#                 persist_report_load_string(agent, self.modpath, self.sparklUnit.loadid)
            
            event = EREEvent(self)
            agent.post_event(GoalPostedEvent(event))
            agent.post_event(event)
        except AnyException, e:
            errid = NEWPM.displayError()
            print 'EXTERNAL TASK RAISED AN EXCEPTION'
            self.result = e
            self.thread_event.set()
            
    def wait_result(self, timeout=None):
        self.thread_event.wait(timeout)
        if self.result is SUCCESS:
            return None
        elif self.result is None:
            return self
        else:
            pm = getattr(self.result, "pm", None)
            raise self.result

    # Solver target methods
    def tfhandlecfin(self, agent, subevent, result):
        # On notification of a result, save the result and notify others
        if result is SUCCESS:
            agent.post_event(GoalSucceededEvent(subevent))
        else:
            agent.post_event(GoalFailedEvent(subevent, result))
        self.result = result
        self.thread_event.set()

installConstructor(ExternalRunExpr)


################################################################

class Agent(object):
    __slots__ = (
        "name",
        #"_intentions",                   # list of intentions
        #"_change_monitors",
        "_rlock",                         # RLock on agent structures
        "_nextid",                       # next nextid
        "_symbolDI",                # symbol -> DI
        "_symbolImpSym",                # symbol -> importedSym
        "_filenameCache",                     # filename -> {idsym -> DI}
#        "_compute_stack",
        "_changed",
        "_eventSubscribers",
        "_misbehaved",
        "loaded_from_persist_data",      # agent initialized with persistence data
        #"_pred_imp",                    # absname -> PredImp
        #"_fun_imp",                     # absname -> FunImp
        #"_task_imp",                    # absname -> ActImp
        #"loadedFileEvents",  # map file to events that occurred during load
        "_externals_queue",             # Queue of externals to process
        "_internals_queue",             # Queue of internals to process        
        "_externals_present", # Boolean set after adding something to the queue
        "_internals_present", # Boolean set after adding something to the queue        
        "_tests_queue",             # Queue of tests to process
        "_gcDirtyBit",              # flag for garbage collection, currently set when we generate events objects
        "_tests_present", # Boolean set after adding something to the queue
        "_something_to_do_event",       # 
        "_events",                      # list of events to handle
        "_intention_structure",
        "_current_tframe",
        "_current_event",
        "_executor_thread",
        "_kill",
        "allPostedEvents", # either None or a list of every event posted
   )

    def __init__(self, name):
        self.name = name
        AGENTS[name] = self
        self.reInit()
        # load persisted state if indicated in initialization. is_resume_state()
        # may raise an Exception if init_spark() has not been called with the
        # initialization parameters
        from spark.internal.init import is_resume_state
        if is_resume_state():
            self._load_persisted_state()
            self.allPostedEvents = None     # by default, don't record every event

    def reInit(self):
        #self._intentions = []
        #self._change_monitors = []
        self._rlock = threading.RLock()
        self._nextid = 0
        #self.loadedFileEvents = {}
        self._symbolDI = {}
        self._symbolImpSym = {}
        for (functor, imp) in EXPR_IMPS.items():
            self._symbolDI[functor] = _DI(None, imp(None))
        self._filenameCache = {}
#        self._compute_stack = []
        self._events = []
        self._changed = False
        self._externals_present = False
        self._internals_present = False
        self.loaded_from_persist_data = False #not true until persist data used
        self._internals_queue = Queue()
        self._externals_queue = Queue()        
        self._tests_present = False
        self._tests_queue = Queue()
        self._something_to_do_event = threading.Event()
        #self._perception_handler = PerceptionHandler()
        #self.add_intention(self._perception_handler)
        self._intention_structure = IntentionStructure()
        self._current_tframe = None
        self._current_event = None
        self._executor_thread = None
        self._kill = False
        self._gcDirtyBit = False
        self._eventSubscribers = [] #probably only have about 1 of these
        self._misbehaved = [] #misbehaving components
        self.allPostedEvents = None     # by default, don't record every event

    def setChanged(self):
        #debug("set changed")
        self._changed = True

    def nextid(self):
        next = self._nextid
        self._nextid = next + 1
        return next

    #PERSIST
    #note: the agent will not call this method on its own. it's up to the controlling
    #logic to determine whether or not the agent should resume it state and thus
    #call this method
    def _load_persisted_state(self):
        """loads the persisted agent state from disk."""
        # DNM 2006/01/02 - loading the state of an agent has been
        # simplified. Now we just reload the declarations from the
        # FileSPUs that were previously loaded into the agent and then
        # restore the KB.
        if self._executor_thread is not None:
            raise InternalException("Cannot load persisted state after executor has been started")

        from spark.internal.resume import get_console_source_expr_and_unit, \
             get_persist_modpath_load_order, resume_kb

        #check initial persist state, get load order
        modpath_load_order = get_persist_modpath_load_order(self)
        if modpath_load_order:
            self.loaded_from_persist_data = True
            print "(persist) resuming agent '%s' from persisted state"%(self.name)
        else:
            self.loaded_from_persist_data = False
            print "(persist) no persist state for agent '%s'"%(self.name)            
            return #nothing to load

        #set resuming flag and switch the source locator so that we load from persisted files
        #the resuming flag is raised at least twice -- once during init, and once for each agent
        set_resuming(True)
        STANDARD_ID_SAVE.set_resuming(True)

        for (command, modname, loadid) in modpath_load_order:
            if (command != 'load'): raise AssertionError
            spu = ensure_modpath_installed(modname)
            load_decls_into_agent(spu, self)
        
        #load in the persisted kb
        # - failedConcludes are facts that could not be restored from persisted state,
        #   e.g. connection status
        failedConcludes = resume_kb(self)
        if failedConcludes:
            print "(persist) not all persisted state for agent '%s' could be restored"%self.name
            for (imp, bindings, zexpr) in failedConcludes:
                self.add_internal(InternalConclude(imp, bindings, zexpr))
        
        self.add_internal(InternalRaisePersistFlags(self, Symbol("spark.lang.builtin.SparkAgentRestored")))
        #reset the resuming flag
        set_resuming(False)
        STANDARD_ID_SAVE.set_resuming(False)
        print "(persist) persistent state for agent '%s' loaded"%self.name
    
    def start_executor(self):
        if not (self._executor_thread is None): raise AssertionError, \
               "Cannot call start_executor when the executor is already started"
        thread = threading.Thread(target=self.executor, name="Executor")
        self._executor_thread = thread
        if (self._kill != False): raise AssertionError
        self._kill = False
        #print "STARTING EXECUTOR", self, self._executor_thread, self._kill
        thread.start()

    def stop_executor(self):
        if self._executor_thread is not None:
            report_instrumentation_point(self, SPARK_SHUTDOWN)
            #thread = self._executor_thread
            self._kill = True
            #print "REQUESTING EXECUTOR STOPS", self, self._executor_thread, self._kill
            self._something_to_do_event.set()

    def add_internal(self, internal):
        if not (isinstance(internal, Internal)): raise AssertionError
        self._internals_present = True
        self._internals_queue.put(internal)
        self._something_to_do_event.set()
        
    def add_external(self, external):
        if not (isinstance(external, External)): raise AssertionError
        self._externals_queue.put(external)
        self._externals_present = True
        self._something_to_do_event.set()
        if not (self._executor_thread): raise AssertionError, \
           "Executor should be running to execute %s"%self.expr
#         if not self._executor_thread:   # hack to make debugging easier
#             self.iterate()
#             external.thread_event.set() # DNM - This is BOGUS!

    def add_test(self, test):
        if not (isinstance(test, Test)): raise AssertionError
        self._tests_queue.put(test)
        self._tests_present = True
        self._something_to_do_event.set()
        if not (self._executor_thread): raise AssertionError, \
           "Executor should be running to execute test %s"%self.expr
#         if not self._executor_thread:   # hack to make debugging easier
#             self.iterate()
#             test.thread_event.set() # DNM - This is BOGUS!

    def run(self, text, modname):
        #saveSparklUnit=True
        ext = ExternalRunExpr(text, Symbol(modname), True)
        self.add_external(ext)
        return ext

    #TODO: it should be the responsibility of the interpreter loop to do the
    #printing, not agent
    def test(self, text, modname):
        test = TestTestExpr(text, Symbol(modname))
        #debug("add_test(%r)", test)
        self.add_test(test)
        #debug("add_test flag is %r"%test.thread_event.isSet())
        result = test.wait_result(10)     # should not wait too long
        #debug("add_test flag is %r"%test.thread_event.isSet())
        #debug("add_test -> %r", result)
        if result is None:
            print "no results (possibly due to internal error) or taking too long"
        else:
            test.printme()

    def eval(self, text, modname): # NO LOCKING!
        test = TestEvalExpr(text, Symbol(modname))
        self.add_test(test)
        #print "Waiting for a result"
        result = test.wait_result(40)       # should not wait too long
        #print result
        while result is None:
            if not (test.isWaiting()): raise AssertionError, \
               "TestEvalExpr set completed flag with no result"
                
            print "WARNING - EVAL RETURNED NONE - WAITING ANOTHER 10 SECONDS"
            result = test.wait_result(10)       # should not wait too long
        return result

    def add_ephemeral(self, symbol, *args):
        "Add an AddFactEvent to the event queue"
        self.add_external(ExternalEvent(AddFactEvent(symbol, args)))

    def get_intentions(self):
        return [x for x in self._intention_structure.get_root_tframes()]
        
    #### EVERYTHING BELOW MUST BE CALLED FROM EXECUTOR THREAD ####

    def post_event(self, event): # Must be called from executor thread
        if isinstance(event, FactEvent) and is_resuming():
            return #ignore events posted during a resume
        #debug("posting event %s", event)
        # DEBUG START
        #ignore = event.getArgs(self)
        # DEBUG END
        self._events.append(event)
        #note: not thread-safe
        for listener in self._eventSubscribers:
            try:
                listener.eventPosted(self, event)
            except AnyException, e:
                if listener not in self._misbehaved:
                    self._misbehaved.append(listener)
                    print "ERROR: Agent event listener", listener, "is misbehaving (squelching future errors)"
                    errid = NEWPM.displayError()
                else:
                    errid = NEWPM.recordError()

        if self.allPostedEvents is not None:
            self.allPostedEvents.append(event)
        if SAFE_ACTIVITY_CHECKING:
            self.setChanged()

    def executor(self):
        #print "Starting executor, _kill=", self._kill
        #@-timing# T_executor.start()
        try:
            waitTime = 0.0
            waitInterval = 0.1
            while not self._kill:
                #debug("Executor processing ...")
                anyActivity = self.iterate()
                if anyActivity:
                    waitTime = 0.0
                #need to invoke the circular gc to get rid of our
                #tframes and events that leak otherwise

                #debug("... executor processing done")
                #NOTE: chose .1sec timeout because this is mainly for
                #testing temporal predicates, and .1sec granularity seems
                #to preserve CPU performance when there is nothing to do
                #@-timing# T_executor.stopstart(T_wait)
                self._something_to_do_event.wait(waitInterval)
                #@-timing# T_wait.stopstart(T_executor)
                if not self._something_to_do_event.isSet():
                    #@-timing# T_gc.start()
                    if self._gcDirtyBit:
                        if spark.internal.version.isPython:
                            gc.collect()
                        elif spark.internal.version.isJython:
                            System.gc()
                        self._gcDirtyBit = False
                    #@-timing# T_gc.stop()
                    waitTime = waitTime + waitInterval
                    if waitTime > IDLE_WAIT_TIME:
                        P_NowIdle = Symbol("spark.util.misc.NowIdle")
                        #print P_NowIdle, waitTime
                        self.add_ephemeral(P_NowIdle)
                self._something_to_do_event.clear()
                
            #persist action are processed as internals, so we want to clear these out
            self.process_internals()
#         except LocatedError, err:
#             pm.set()
#             print err
#             print "ERROR NOT HANDLED BY agent.iterate"
        except AnyException:
            NEWPM.displayError()
            print "ERROR NOT HANDLED BY agent.iterate"
            NEWPM.pm()
        self._kill = False
        self._executor_thread = None
        #@-timing# T_executor.stop()
        #print "EXECUTOR TERMINATING", self, self._executor_thread, self._kill
            
    def iterate(self):           # Must be called from executor thread
        """Work on progressable intentions and externals until nothing
        left to do."""
        #@-timing# T_iterate.start()
        if self._events:
            print "The events are: ", self._events
        if (self._events): raise AssertionError
        int_struct = self._intention_structure
        anyActivity = False         # has there been any activity yet?
        self._changed = False
        #debug("IS: %r", int_struct)
        while True:
            #debug( " check for new tests")
            self.process_tests()
            #debug( " check for new internals")
            #PERSIST: process any action items from the resume
            self.process_internals()            
            #debug(" check for new externals")
            self.process_externals()
            for leaf_tframe in self._intention_structure.leaf_iterator():
                if self._kill:
                    #@-timing# T_iterate.stop()
                    return True
                #debug("active threads %r", threading.enumerate())
                if (self._events ): raise AssertionError
                #debug(" processing leaf_tframe %r", leaf_tframe)
                # process the leaf_tframe
                #@-timing# T_process_tframe.start()
                self.process_tframe(int_struct, leaf_tframe)
                #@-timing# T_process_tframe.stop()
                #debug( " check for new tests")
                self.process_tests()
                #debug( " check for new internals")
                #PERSIST: process any action items from the resume
                self.process_internals()            
                #debug(" check for new externals")
                self.process_externals()
            if self._changed:
                #debug(" something changed")
                anyActivity = True
                self._changed = False
            elif not (self._internals_present or self._externals_present \
                      or self._tests_present):
                #@-timing# T_iterate.stop()
                return anyActivity
            #else:
                #debug("  looping")

    def process_tframe(self, int_struct, leaf_tframe):
        result = leaf_tframe.completed()
        if result is None:
            self._current_tframe = leaf_tframe
            self._current_event = leaf_tframe.event()
            #debug("process_tframe tcont on %s", leaf_tframe)
            try:
                #@-timing# T_leaf_tframe_tfcont.start()
                leaf_tframe.tfcont(self)
                #@-timing# T_leaf_tframe_tfcont.stop()
            except AnyException, exception:
                errid = NEWPM.displayError()
                print "EXCEPTION WHILE PROCESSING LEAF TFRAME"
                leaf_tframe.tf_set_completed(self, ExceptionFailure(leaf_tframe, exception, errid))
                self.setChanged()
            self._current_tframe = None
            self.process_events()
        else:
            #Testing Script. Begin:
#            global chronometers
#            chronometers["process_tframe"].start()
            #Testing Script. End.                    
            #debug("process_tframe leaf completed: %s", leaf_tframe)
            self.setChanged()
            #debug("Removing completed tframe %r", leaf_tframe)
            int_struct.remove_tframe(self, leaf_tframe)
            #self._current_tframe = leaf_tframe.tf_sync_parent()
            event = leaf_tframe.event()
            solver_target = event.e_solver_target()
            if solver_target is not None:
                #debug("process_tframe informing parent %s", solver_target)
                solver_target.tfhandlecfin(self,event,result)
                self.process_events()
            #PERSIST:INSTRUMENT
            if isinstance(event, ObjectiveEvent):
                goalsymName = event.goalsym().name
                if goalsymName not in NON_PERSISTING_OBJECTIVES:
                    if is_persist_state():
                        pass
                        #get_sdl().logger.info("persist[Objective[%s]]"%goalsymName)
                        #print "Persist objective complete:",goalsymName
                    report_instrumentation_point(self, OBJECTIVE_COMPLETED)
            if isinstance(event, AddFactEvent) and not isinstance(event, MetaFactEvent):
                goalsymName = event.goalsym().name
                if goalsymName not in NON_PERSISTING_NEWFACTS:
                    if is_persist_state():
                        pass
                        #get_sdl().logger.info("persist[NewFact[%s]]"%goalsymName)
                        #print "Persist factevent procedure complete:", goalsymName
                    report_instrumentation_point(self, NEWFACT_COMPLETED)
                
                
            #Testing Script. Begin:
#            chronometers["process_tframe"].stop()
            #Testing Script. End.    
                
    def process_tests(self):
        if self._tests_present:
            self._tests_present = False
            #self._current_tframe = None
            while not self._tests_queue.empty():
                test = self._tests_queue.get(0)
                #debug("selecting test %r", test)
                try:
                    #TestEvalExpr.perform(test, self)
                    test.perform(self)
                    #debug("test completed %r", test)
                except AnyException, e:
                    errid = NEWPM.displayError()
                    print "TEST RAISED AN EXCEPTION", test, e

    def process_internals(self):
        #PERSIST: when we persist resume, we add in 'internals',
        #which are the concludes that need to be done after the
        #kb has been resumed for state that could not be restored,
        #e.g. (IOConnected True) might be re-concluded as
        #(IOConnected False) 
        if self._internals_present:
            self._internals_present = False
            #self._current_tframe = None
            while not self._internals_queue.empty():
                ext = self._internals_queue.get(0)
                #debug("selecting external %r", ext)
                try:
                    ext.perform(self)
                    #debug("external completed %r", ext)
                except AnyException:
                    #debug("EXCEPTION IN EXTERNAL %r", ext)
                    errid = NEWPM.displayError()
                    print "EXTERNAL RAISED AN EXCEPTION", ext
                    print "(persist) re-concluding not all persisted state for agent '%s' could be restored"%self.name
                self.process_events()

    def process_externals(self):
        if self._externals_present:
            self._externals_present = False
            #self._current_tframe = None
            while not self._externals_queue.empty():
                ext = self._externals_queue.get(0)
                #debug("selecting external %r", ext)
                try:
                    ext.perform(self)
                    #debug("external completed %r", ext)
                except AnyException:
                    #debug("EXCEPTION IN EXTERNAL %r", ext)
                    errid = NEWPM.displayError()
                    print "EXTERNAL RAISED AN EXCEPTION", ext
                self.process_events()

    def process_events(self):
        #numevents = len(self._events)   # for later consistency check
        #for event in self._events:
        if not self._events:
            return
        #Testing Script. Begin:
#        global chronometers
#        chronometers["process_events"].start()
        #Testing Script. End.                
        while self._events:
            event = self._events.pop()
            #debug("Processing event %s", event)
            #print "Processing event", event
            try:
                new_tframe = self.soapi_chain(MAX_SOAPI_DEPTH, event, None, None)
            except AnyException:
                print "ERROR WHILE COMPUTING SET OF APPLICABLE PROCEDURE INSTANCES"
                errid = NEWPM.displayError()
                new_tframe = None
            self._current_event = None
            #debug("Processing event %s -> %s", event, new_tframe)
            if new_tframe is not None:
                #parent = new_tframe.tf_sync_parent()
                #self._intention_structure.add_tframe(parent, new_tframe)
                self.add_tframe(new_tframe)
                self.setChanged()       # some activity
            else:
                # DNM - this will inform the solver_target of an
                # object level event that no procedure was found so
                # long as no meta level procedures are
                # activated. However, it doesn't solve the problem of
                # a meta-level procedure that fails to intend a new
                # tframe. Also, we do not know for sure that the
                # target is a tframe as required by
                # NoGoalResponseFailure
                target = event.e_solver_target()
                if target is not None:
                    failure = NoGoalResponseFailure(target, event)
                    target.tfhandlecfin(self, event, failure)
                    self.setChanged()       # some activity
                elif SAFE_ACTIVITY_CHECKING:
                    self.setChanged()
            self._gcDirtyBit = True
        #Testing Script. Begin:
#        chronometers["process_events"].stop()
        #Testing Script. End.   
        #if (numevents != len(self._events) # consistency check): raise AssertionError
        #del self._events[:]

    def soapi_chain(self, limit, event, prev_tframes, prev_prev_tframes):
        if not (limit > 0): raise AssertionError
        self._current_event = event
        tframes = event.find_tframes(self)
        #debug("  event tframes: %r %r", event, tframes)
        if len(tframes) == 0 and prev_prev_tframes is not None \
           and len(prev_tframes) == 0:
            if len(prev_prev_tframes) > 0:
                if len(prev_prev_tframes) > 1:
                    pass
                    #print "Choosing first of %d tframes for event %s"%(len(prev_prev_tframes), event)
                    #raise Exception()
                return prev_prev_tframes[0] # DNM - or random selection
            else:
                return None
        else:
            newevent = SOAPIEvent(event, tuple(tframes))
            return self.soapi_chain(limit-1, newevent, tframes, prev_tframes)

    def signal(self, tframe, signal):
        if not tframe.tfhandlesig(self, signal):
            children = self._intention_structure.tframe_children(tframe)
            if len(children) == 0:
                tframe.tf_set_completed(self, SignalFailure(tframe, signal))
            else:
                for child in children:
                    self.signal(child, signal)

    def terminate_children(self, tframe, and_self=False):
        children = tuple(self._intention_structure.tframe_children(tframe)) # frozen copy
        #print "children=", children
        for child in children:
            #print "handling child", child
            self.terminate_children(child, True)
        if and_self:
            #print "terminating", tframe
            tframe.tfterminated(self)
            self.remove_tframe(tframe)
        
            
    def add_tframe(self, tframe):
        #debug("Adding tframe %r", tframe)
        tframe.rebind_parameters(self)
        parent = tframe.tf_sync_parent()
        self._intention_structure.add_tframe(parent, tframe)
        from spark.internal.repr.procedure \
             import ProcedureStartedEvent, ProcedureTFrame
        if not isinstance(tframe.event(), ProcedureStartedEvent) \
           and isinstance(tframe, ProcedureTFrame) \
           and not is_resuming():
            self.post_event(ProcedureStartedEvent(tframe))
        return True

    def replace_tframe(self, oldtframe, newtframe):
        newtframe.rebind_parameters(self)
        event = oldtframe.event()
        if (newtframe.event() != event): raise AssertionError, \
            "New TFrame must have the same event as the old TFrame"
        parent = oldtframe.tf_sync_parent()
        if (newtframe.tf_sync_parent() != parent): raise AssertionError, \
            "New TFrame must have the same parent as the old TFrame"
        self._intention_structure.replace_tframe(parent, oldtframe, newtframe)
        return True

    def remove_tframe(self, tframe):
        self._intention_structure.remove_tframe(self, tframe)

    def tframe_children(self, tframe):
        return self._intention_structure.tframe_children(tframe)

    def tframe_roots(self):
        return self._intention_structure.get_root_tframes()

    def fileLoaded(self, filename):
        "Has file filename been loaded? If so, return the LoadedFileFact fact, else return None"
        try:
            facts = self.factslist1(P_LoadedFileFacts, filename)
            if facts:
                return facts[0]
            else:
                return None
        except LowError: # may not have loaded LoadedFileFacts predicate yet
            return None
    
    def load_modpath(self, modpath):
        if (self._events): raise AssertionError
        filename = str(modpath)
        #if filename in self.loadedFileEvents:
        if self.fileLoaded(filename):
            return True
        #debug("Loading module %s into agent", modpath)
        #spu = ensure_modpath_installed(filename)
        try:
            success = load_file_into_agent(filename, self)
        finally:
            del self._events[:]
        if not success:
            raise LowError("Cannot load %s"%filename)

#         # Following moved into load_file_into_agent
#         #PERSIST
#         if is_persist_state():
#             persist_report_load_modpath(self, modpath)

        #self.loadedFileEvents.add(filename) # done in load_file_into_agent
        # Ignore all the events generated 
        del self._events[:]

#     def unload_modpath(self, modpath):
#         # Note - this only works for a single agent
#         print "Unloading module", modpath
#         drop_modpath(modpath)
#         # get rid of all implementations based on decls that have been dropped
#         to_drop = [name for name in self._imp.keys() \
#                    if not modpath_is_installed(Symbol(Symbol(name).modname))]
#         to_drop.sort()
#         for name in to_drop:
#             print "Deleting imp for %s"%name
#             del self._imp[name]
#         dead_modules = [modpath for modpath in self._modpaths_loaded \
#                        if not modpath_is_installed(modpath)]
#         for modpath in dead_modules:
#             print "Marking module unloaded: %s"%modpath
#             del self._modpaths_loaded[modpath]
        
#     def set_syminfo(self, syminfo):
#         sym = syminfo.symbol()
#         imp = syminfo.get_imp(self)
#         if imp is not None:
#             self._imp[sym.name] = imp
#         else:
#             pass
#             #debug("Symbol %s imp is None: %r", sym, syminfo._impexpr)
#         #    SHOW(syminfo)


    
    # Frame methods:

#     def add_event(self, event):
#         self._changed = True
#         self._events.append(event)

    def agent(self):
        return self

    def _getDI(self, symbol):
        try:
            return self._symbolDI[symbol]
        except KeyError:
            importedSym = self._symbolImpSym.get(symbol)
            if importedSym is None:
                #print "No implementation has been set for %s"%symbol
                raise LowError("%s - No implementation has been set", symbol)
            di = self._symbolDI.get(importedSym)
            if di is None:
                raise LowError("%s - No implementation imported symbol %s", \
                               symbol, importedSym)
            self._symbolDI[symbol] = di
            return di

    def getDeclaredSymbols(self):
        return self._symbolDI.keys()
        
    def getImp(self, symbol):
        return self._getDI(symbol).implementation

    def setImp(self, symbol, imp):
        self._getDI(symbol).implementation = imp

    def getInfo(self, symbol):
        di = self._getDI(symbol)
        info = di.info
        if info is None:
            di.info = di.implementation.generateInfo()
            return di.info
        else:
            return info
        
#     def setInfo(self, symbol, info):
#         self._getDI(symbol).info = info
        
    def getDecl(self, symbol):
        return self._getDI(symbol).decl

    def factslist0(self, symbol):       # specific to DefaultImp
        "List of all facts in predicate names symbol"
        result = []
        info = self.getInfo(symbol)
        if info:                        # handle case of info not set
            for facts in info.values():
                result.extend(facts)
        return result

    def factslist1(self, symbol, value): # specific to DefaultImp
        "List of facts with first arg = value in predicate symbol - DO NOT MODIFY THE RESULT!"
        info = self.getInfo(symbol)
        if info:                        # handle case of info not set
            return info.get(value, ())
        else:
            return ()

    def addfact(self, symbol, fact_tuple): # generic
        """Conclude a fact with predicate symbol, symbol, and
        arguments, fact_tuple. This should be called within the SPARK
        execution thread."""
        imp = self.getImp(symbol)
        b, z = valuesBZ(fact_tuple)
        imp.conclude(self, b, z)

    def removefact(self, symbol, fact_tuple): # generic
        """Remove a fact with predicate symbol, symbol, and arguments,
        fact_tuple. This should be called within the SPARK execution
        thread."""
        imp = self.getImp(symbol)
        b, z = valuesBZ(fact_tuple)
        imp.retractall(self, b, z)

    def matchfact(self, symbol, template_tuple, index=None):
        """Try to match a fact with predicate symbol, symbol, and
        arguments, template_tuple. A value of None for an argument
        means match anything.  If no match is found, return None. If a
        match is found and index is None, return it as a sequence that
        has non-None values for all the arguments that were None in
        template_tuple. If index is not None, return the index-th
        argument. This should be called within the SPARK execution
        thread."""
        imp = self.getImp(symbol)
        b, z = optBZ(template_tuple)
        if imp.solution(self, b, z):
            if index == None:
                return [b.bTermEval(self, zitem) for zitem in z]
            else:
                return b.bTermEval(self, z[index])
        else:
            return None

    def getCache(self, filename):
        try:
            return self._filenameCache[filename]
        except KeyError:
            cache = {}
            self._filenameCache[filename] = cache
            return cache
        

#     def hasDecl(self, symbol):
#         return self._symbolDI.has_key(symbol)

    def addDecl(self, decl):
        symbol = decl.asSymbol()
        if self._symbolDI.has_key(symbol):
            if self._symbolDI[symbol].decl != decl:
                raise LowError("The declaration for symbol %s has already been set"%symbol)
        else:
            self._symbolDI[symbol] = _DI(decl, decl.getImp())
            #print "Set agent._symbolDI[%s]"%symbol

    def addImport(self, asSym, fromSym):
        oldImpSym = self._symbolImpSym.get(asSym)
        oldDI = self._symbolDI.get(asSym)
        if oldImpSym and oldImpSym != fromSym:
            raise LowError("The symbol %s is already imported from %s" \
                           %(asSym, fromSym))
        fromSymDI = self._symbolDI.get(fromSym)
        if oldDI and oldDI != fromSymDI:
            raise LowError("The symbol %s is already known as %s" \
                           %(asSym, oldDI.decl.asSymbol()))
        self._symbolImpSym[asSym] = fromSym

    def value_imp(self, value):
        if isSymbol(value):
            return self.getImp(value)
        else:
            return value


def agentCurrentTFrame(agent):
    return agent._current_tframe

def agentCurrentEvent(agent):
    return agent._current_event


class _DI(object):
    __slots__ = (
        "decl",
        "implementation",
        "info",
        )
    def __init__(self, decl, implementation):
        self.decl = decl
        self.implementation = implementation
        self.info = None
        

class SOAPIEvent(MetaFactEvent):
    __slots__ = ()
    estring = "++"
    numargs = 2
    event_type = SOAPI
    constructor_mode = "VV"

    def base_tframe(self):
        return self._fact[0].e_sync_parent()

    def is_solver(self):
        return True                # Only want one procedure to be selected

    def meta_level(self):
        subevent = self._fact[0]
        if isinstance(subevent, SOAPIEvent):
            return 1 + subevent.meta_level()
        else:
            return 1

    def base_event(self):
        return self._fact[0]
installConstructor(SOAPIEvent)

class SolutionsPrinter(object):
    __slots__ = (
        "varids",
        "count",
        )
    def __init__(self, varids):
        self.varids = varids
        self.count = 0
        
    def compute(self, agent, bindings):
        self.count = self.count + 1
        print "%d."%(self.count),
        for varid in self.varids:
            print "%s:"%varid, bindings.get_either(varid),
        print


################################################################            
test_agent = None

def dotest():
    global test_agent
    test_agent = Agent("A")
    #testagent.start_executor()
    print "now run dotest1(), dotest2(), dotest3(), dotest4()"
    return test_agent
    
def dotest1():
    task = '[conclude: (new_customer `fred `toronto)]'
    print "Running the task:", task
    test_agent.run(task, 'spark_examples.delivery').wait_result(5)
    return

def dotest2():
    task = '[do: (deliver `fred `floral_goods)]'
    print "Running the task:", task
    test_agent.run(task, 'spark_examples.delivery').wait_result(5)
    return 

def dotest3():
    #import spark.trace
    #spark.trace.set_trace_fn(spark.trace.PRINT_TRACE)
    task = '[do: (task1 4 $x)]'
    print "Running the task:", task
    testint1 = test_agent.run(task, 'spark_examples.source1')
    if not (testint1.completed() is None): raise AssertionError
    import time
    print "Sleeping for 1 second"
    time.sleep(1)
    task = '[do: (print "hi" []) conclude:(q 7)]'
    print 'Running the task:', task
    testint2 = test_agent.run(task, 'spark_examples.source1')
    testint2.wait_result(5)
    if (testint2.completed() != SUCCESS): raise AssertionError
    if (testint1.completed() != SUCCESS): raise AssertionError
    print "Task", task, "is now completed"

def dotest4():
    task='[conclude: (p 9)]'
    print "Running the task:", task
    test_agent.run(task, 'spark_examples.example').wait_result(5)
    return
