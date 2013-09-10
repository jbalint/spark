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
#* "$Revision:: 359                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
import types
import weakref

from spark.internal.version import *
from spark.internal.common import pair_up, NEWPM, DEBUG, ABSTRACT, USE_WEAKDICT_NAME_TABLES, POSITIVE, NEGATIVE, SUCCESS, SOLVED
from spark.internal.exception import TestFailure, LocatedError, UnlocatedError, CapturedError, ExceptionFailure, \
     FailFailure, Failure, Unimplemented, NoGoalResponseFailure

from spark.internal.repr.common_symbols import P_Achieve, GOAL_POSTED, GOAL_SUCCEEDED, \
      GOAL_FAILED, GOAL_TERMINATED
#from spark.internal.repr.zexpr import PatsZexpr

from spark.internal.debug.trace import step_fn, EXECUTING, SUCCEEDED, FAILED, TESTFALSE, TESTTRUE, WAITING

from spark.pylang.defaultimp import get_all_tframes, SparkEvent, MetaFactEvent
from spark.pylang.implementation import ActImpInt
from spark.internal.parse.basicvalues import ConstructibleValue, installConstructor, List, isList, value_str, createList

from spark.internal.parse.processing import Imp, Context
from spark.internal.repr.common_symbols import *
from spark.internal.parse.usagefuns import *
from spark.util.logger import get_sdl

debug = DEBUG(__name__)#.on()

################################################################
#
YIELD = intern('YIELD')
HALT = intern('HALT')

################################################################
# Signals
INTERRUPT = intern("INTERRUPT")

################################################################
# TFrame
#
# A TFrame is something that is being executed, for example: a
# TaskExprTFrame keeps track of the state of execution of a task
# expression; a ProcedureTFrame keeps track of the state of an
# executing procedure; a BasicImpTFrame records the (instantaneous)
# execution of a primitive action; a ThreadImpTFrame records the
# (extended) execution of an action in another thread.
#
# To be persisted, each TFrame, being a ConstructibleValue, must
# define the standard ConstructibleValue methods and be installed.
#
# The behavior of a TFrame is specified by:
#
# tfcont - which performs a "single step" of the TFrame, possibly
# calling its own tf_set_completed method to indicate success or
# failure.

def id_tframe(id):
    return TFrame._weakdict[id]

class TFrame(ConstructibleValue):
    __slots__ = (
        #"__weakref__",
        "_name",
        "_event",
        "_completed",                       # keep result if completed
        "_parent",                          # parent TFrame if sync
        #"_monitors",
        )

    cvcategory = "TF"

    _weakdict = weakref.WeakValueDictionary()

    def __init__(self, name, event):
        if not (isinstance(event, SparkEvent)): raise AssertionError
        ConstructibleValue.__init__(self)
        self._name = name
        self._event = event
        self._completed = None
        #self._monitors = []
        if USE_WEAKDICT_NAME_TABLES:
            self._weakdict[name] = self
        self._parent = self.tf_is_sync()

    def tf_is_sync(self):
        # by default use event type
        return self._event.e_sync_parent()

    def tf_sync_parent(self):
        return self._parent

    def tf_set_sync_parent(self, tframe):
        self._parent = tframe

    def completed(self):
        return self._completed

    def event(self):
        return self._event

    def name(self):
        return self._name

#     def solver_target(self):
#         return self._event.e_solver_target()

    def tfcont(self, agent):
        raise Unimplemented()
        
    def tfterminated(self, agent):
        "Called when self is about to be terminated (allows clean-up)."
        pass
    
    def tfhandlesig(self, agent, signal):
        return None                    # Default: can't handle signals

    def tf_set_completed(self, agent, result):
        "Method called by subclasses to indicate completion of the event"
        # TODO: DNM - post the SUCCESS/FAILURE event here
        agent.setChanged()
        self._completed = result

    def rebind_parameters(self, agent):
        pass

    def constructor_args(self):
        return [self._name, self._event]
    constructor_mode = "VI"

    def state_args(self):
        if self._completed is not None:
            return (self._completed,)

    def set_state(self, ignore_agent, completed):
        self._completed = completed

installConstructor(TFrame)

        
def ancestor_tframes(event_or_tframe):
    result = []
    if isinstance(event_or_tframe, SparkEvent):
        tf = event_or_tframe.e_sync_parent()
    elif isinstance(event_or_tframe, TFrame):
        tf = event_or_tframe.tf_sync_parent()
    else:
        raise Exception("Invalid argument to ancestor_tframes: %s" % event_or_tframe)
    while tf is not None:
        if not isinstance(tf.event(), PseudoGoalEvent):
            result.append(tf)
        tf = tf.tf_sync_parent()
    return result

def ancestor_events(event_or_tframe):
    result = []
    if isinstance(event_or_tframe, SparkEvent):
        tf = event_or_tframe.e_sync_parent()
    elif isinstance(event_or_tframe, TFrame):
        tf = event_or_tframe.tf_sync_parent()
    else:
        raise Exception("Invalid argument to ancestor_tframes: %s" % event_or_tframe)
    while tf is not None:
        ev = tf.event()
        if not isinstance(ev, PseudoGoalEvent):
            result.append(ev)
        tf = tf.tf_sync_parent()
    return result

################################################################
# TaskExprTFrame        

DSTACK_UNUSED_VALUE = 0          # A persistable value instead of None

class TaskExprTFrame(TFrame):
    __slots__ = (
        #"taskexprs",
        "_bindings",
        "_estack",                     # stack of exprs being executed
        "_dstack",                      # data stack for imps to use
        #"_istack",                       # stack of imps
        "_subgoal_event",               # there is an active subgoal
        "_subgoal_event_list", # history of weakrefs to posted subgoals and subtframes  (NOT CURRENTLY PERSISTENT)
        "_root_taskexpr",               # record for display purposes
        )

    # DNM - for getting properties about procedures we should ref procedure
    def __init__(self, name, event, bindings, taskexpr):
        TFrame.__init__(self, name, event)
        self._bindings = bindings
        from spark.internal.parse.expr import Expr
        if isinstance(taskexpr, Expr): # ordinary creation
            self._estack = [taskexpr]
            self._dstack = [DSTACK_UNUSED_VALUE]
            self._root_taskexpr = taskexpr
        elif isList(taskexpr): # taskexpr = [root_taskexpr] when resuming
            self._root_taskexpr = taskexpr[0]
            # rely on set_state to set the following
            self._estack = []
            self._dstack = []
        else:
            raise UnlocatedError("Not an Expr or SPARK list of Exprs: %r"%taskexpr)
        self._subgoal_event = None
        self._subgoal_event_list = []

    def getBaseBindings(self):
        return self._bindings

    def constructor_args(self):
        return TFrame.constructor_args(self) + [self.getBaseBindings(), createList(self._root_taskexpr)]
    constructor_mode = "VIIV"

    def state_args(self):
        if self._completed is not None:
            return (self._completed, )
        elif self._subgoal_event is None:
            return (List(self._estack), List(self._dstack))
        else:
            return (List(self._estack), List(self._dstack), self._subgoal_event)
    def set_state(self, ignore_agent, arg1, arg2=None, arg3=None):
        if arg2 is None:
            self._completed = arg1
            return
        self._estack = list(arg1)
        self._dstack = list(arg2)
        if arg3 is not None:
            self._subgoal_event = arg3
    
    def subgoal_event(self):
        return self._subgoal_event

    def all_subgoal_events(self):
        return [x() for x in self._subgoal_event_list]

    def root_taskexpr(self):
        return self._root_taskexpr

    def __XXXrepr__(self):
        try:
            if self._estack:
                return "<TF %s %s>"%(self._root_taskexpr, \
                                     self._estack[-1])
            elif self.completed():
                return "<TF %s SUCCEEDED>"%(self._root_taskexpr,)
            else:
                return "<TF %s FAILED>"%(self._root_taskexpr,)
        except:
            NEWPM.displayError()
            return "!"+object.__repr__(self)

    def tfterminated(self, agent):
        subevent = self._subgoal_event
        if subevent is not None and not isinstance(subevent, PseudoGoalEvent):
            # Post goal terminated event
            agent.post_event(GoalTerminatedEvent(subevent))

        
    ################
    # Methods called from outside to progress execution

    def tfcont(self, agent):
        """tfcont will call agent.setChanged if something changed"""
        debug("=> tfcont - TOS=%r", self._estack[-1])
        if self._subgoal_event:               # subgoal has not been processed
            debug("== tfcont - existing subgoal = %r", self._subgoal_event)
            failure = NoGoalResponseFailure(self, self._subgoal_event)
            return self.tfhandlecfin(agent, self._subgoal_event, failure)
        else:
            try:
                taskexpr = self._estack[-1]
                debug("=== .tresume %r", taskexpr)
                imp = taskImp(agent, self, taskexpr)
                return imp.tresume(agent, self, taskexpr)
            except AnyException, err:
                estack = self._estack[:] # a copy for when we debug
                errid = NEWPM.displayError() # we are trapping error so print it
                failure = ExceptionFailure(self, err, errid)
                return self.tfcompleted(agent, failure)

    def tfhandlecfin(self, agent, subevent, result):
        if (subevent != self._subgoal_event): raise AssertionError
        debug("=> tfhandlecfin - TOS=%r, subevent=%r, result=%r", self._estack[-1], subevent, result)
        self._subgoal_event.result = result # TODO: explain why this is necessary
        self._subgoal_event = None
        taskexpr = self._estack[-1]
        if not isinstance(subevent, PseudoGoalEvent):
            # Post goal succeeded/failed events
            if result is SUCCESS:
                agent.post_event(GoalSucceededEvent(subevent))
            else:
                agent.post_event(GoalFailedEvent(subevent, result))
        debug("=== .tsubgoal_complete %r %r %r", taskexpr, subevent, result)
        imp = taskImp(agent, self, taskexpr)
        return imp.tsubgoal_complete(agent, self, taskexpr, subevent, result)

    def tfhandlesig(self, agent, signal):
        if not self._estack: # TODO: find out why a completed TFrame gets signalled
            return False
        debug("=> tfhandlesig %r %r", self._estack[-1], signal)
        for taskexpr in self._estack:
            debug("=== .thandle_signal %r %r", taskexpr, signal)
            imp = taskImp(agent, self, taskexpr)
            if imp.thandle_signal(agent, self, taskexpr, signal):
               return True
        return False

    ################
    # Methods called by task implementations to access taskexpr local variable

    def tfset(self, value):
        "Set the value of the variable allocated to the top taskexpr"
        #if not (self._estack[-1].thas_local): raise AssertionError
        self._dstack[-1] = value

    def tfget(self):
        "Return the value of the variables allocated to the top taskexpr"
        #if not (self._estack[-1].thas_local): raise AssertionError
        return self._dstack[-1]

    ################
    # Methods called by task implementations  on completion of processing

    def tfyield(self, ignore_agent):
        "Cease processing taskexprs and yield control"
        debug("<= yielding")
        return None

    def tfpost_subgoal(self, agent, subgoal):
        "Cease processing taskexprs and post a subgoal"
        if isinstance(subgoal, PseudoGoalEvent):
            # don't post event, just insert tframes
            #self._subgoal_event_list.append(weakref.ref(subgoal))
            debug("<= posting pseudogoal %r", subgoal)
            for tframe in subgoal.find_tframes(agent):
                # keep track of all sub tframes for ppl
                self._subgoal_event_list.append(weakref.ref(tframe))
                agent.add_tframe(tframe)
            agent.setChanged()          # not otherwise set
        else:
            debug("<= posting goal %r", subgoal)
            agent.post_event(GoalPostedEvent(subgoal))
            agent.post_event(subgoal)     # sets agent changed
            # keep track of all subevents for ppl 
            self._subgoal_event_list.append(weakref.ref(subgoal))
        self._subgoal_event = subgoal
        return None

    def tfpost_child(self, agent, index):
        "Start procesing the index'th child of the current taskexpr"
        child_taskexpr = self._estack[-1][index]
        if True: #child_taskexpr.thas_local:
            self._dstack.append(DSTACK_UNUSED_VALUE)
        self._estack.append(child_taskexpr)
        agent.setChanged()
        debug("=== pushing %r", child_taskexpr)
        debug("=== .tenter %r", child_taskexpr)
        imp = taskImp(agent, self, child_taskexpr)
        return imp.tenter(agent, self, child_taskexpr)
    

    def tfcompleted(self, agent, result):
        "Indicate to parent that the current taskexpr has completed"
        agent.setChanged()
        taskexpr = self._estack.pop()
        debug("=== popping %r", taskexpr)
        if True: #taskexpr.thas_local:
            self._dstack.pop()
        if self._estack:
            parent = self._estack[-1]   # top of stack
            index = len(parent)
            while index > 0:
                index -= 1
                if taskexpr == parent[index]:
                    debug("=== .tchild_complete %r %r %r", parent, index, result)
                    imp = taskImp(agent, self, parent)
                    return imp.tchild_complete(agent, self, parent, index, result)
            # Error - parent should have taskexpr as a child
            raise Exception("Invalid tframe _estack")
        else:
            # stack is empty mark success of tframe
            debug("<= complete %r", result)
            self.tf_set_completed(agent, result)
            return None

    def features(self, _agent):
        return ()

    def tfPrintState(self):
        print "Display of TFrame %s"%self
        if self._estack:
            taskexpr = self._estack[-1]
            for v in taskexpr.used_before():
                try:
                    print "Var %s=%s"%(v, value_str(self.bindings.get_either(v)))
                except:
                    print "Var %s=?"%v
            if self._subgoal_event:
                print taskexpr.error("Subgoal=%s\n", self._subgoal_event)
            else:
                print taskexpr.error("")
        else:
            print "State=%s"%self._completed

    def tfPrintStack(self, ignore_if_pseudosubgoal=False):
        parent = self.tf_sync_parent()
        if parent is not None:
            parent.tfPrintStack(True)
        if not (isinstance(self._subgoal_event, PseudoGoalEvent) \
                and ignore_if_pseudosubgoal):
            self.tfPrintState()
        

installConstructor(TaskExprTFrame)

################################################################
# TaskExpr

# class TaskExpr(Expr):
#     __slots__ = ()

#     thas_local = False              # default, overriden by subclasses

#     def thandle_signal(self, agent, tf, zexpr, signal):
#         return False

#     def tinit(self, tframe):
#         pass

#     def tend(self, agent, tframe):
#         pass

#     def tcont(self, agent, tframe):
#         raise Unimplemented()

#     def tcfin(self, agent, tframe, _sub, result):
#         tframe.t_result_pop(agent, result) # default is to pass s/f up

#     def thandlecfin(self, agent, tframe, _sub, result):
#         tframe.t_result_pop(agent, result) # default is to pass s/f up

#     def thandlesig(self, agent, tframe, signal):
#         return False

#     def thandlemod(self, agent, tframe, monitor):
#         raise Unimplemented()

#     def tmonitors(self, agent, tframe):
#         return tframe._monitors

#     def taddmonitor(self, agent, tframe, monitor):
#         monitor.install(tframe)

    # for a task, static means the precondition is static

# class BasicTaskExpr(TaskExpr):
#     __slots__ = ()
#     def task_expr_run(self, bindings):
#         #try:
#             step_fn(bindings, EXECUTING, self)
#             self.basic_run(bindings)
#             bindings.set_completed(self)
#             #step_fn(bindings, SUCCEEDED, self)
#         #except:
#             #step_fn(bindings, FAILED, self)
#             #re_raise()

# ################################################################
class NewFactColon(Imp):
    __slots__ = (
        #"predexpr",
        )
    synchronous = False
    predsym = P_NewFact
#     def __init__(self, term, predexpr):
#         Expr.__init__(self, term, (predexpr,), False)
#         self.predexpr = predexpr
#     def key_symbol(self):
#         return self.predexpr.predsym

class SynchronousColon(Imp):
    __slots__ = ()
    synchronous = True
    predsym = P_NewFact


################################################################
class DoColon(Imp):
    __slots__ = (
        #"actsym",
        #"actexpr",                      # should deprecate use of this
        #"zexpr",
        )
    synchronous = True
    predsym = P_Do

    def tenter(self, agent, tframe, zexpr):
        bindings = tframe.getBaseBindings()
        step_fn(agent, bindings, EXECUTING, zexpr)
        symbol = bindings.bEntity(agent, zexpr[0])
        event = DoEvent(tframe, zexpr, symbol)
        return tframe.tfpost_subgoal(agent, event)

    def tsubgoal_complete(self, agent, tframe, zexpr, subevent, result):
        bindings = tframe.getBaseBindings()
        if result is SUCCESS:
            step_fn(agent, bindings, SUCCEEDED, zexpr)
        else:
            step_fn(agent, bindings, FAILED, zexpr)
        return tframe.tfcompleted(agent, result)

class GoalEvent(SparkEvent):
    __slots__ = (
        "_tframe",
        "_taskexpr",
        "result",                       # set by tframe.tfhandlecfin  on completion
        )

    def __init__(self, tframe, taskexpr):
        name = "%s|thing"%(tframe.name(),) # TODO: fix this
        SparkEvent.__init__(self, name)
        self._tframe = tframe
        self._taskexpr = taskexpr
        self.result = None

    def constructor_args(self):
        return [self._tframe, self._taskexpr]
    constructor_mode = "IV"

    def e_sync_parent(self):
        return self._tframe

    def e_solver_target(self):
        return self._tframe

    def is_solver(self):
        return True

    def getBindings(self):
        return self._tframe.getBaseBindings()

    def getArgs(self, agent): 
        bindings = self._tframe.getBaseBindings()
        return List([termEvalOpt(agent, bindings, expr) \
                     for expr in self._taskexpr[0]])

    def taskexpr(self):
        return self._taskexpr

    def getTaskResultArgs(self, agent):        # DNM - for Mei
        bindings = self._tframe.getBaseBindings()
        return List([termEvalEnd(agent, bindings, expr) \
                                 for expr in self._taskexpr[0]])

    def __repr__(self):
        return "<GE:%s>" % self.name()  # DNM - CHANGE TO objectId

installConstructor(GoalEvent)

class PseudoGoalEvent(GoalEvent):
    __slots__ = (
        "_tframes",
        )

    def __init__(self, tframe, taskexpr):
        GoalEvent.__init__(self, tframe, taskexpr)
        self._tframes = []

    def addTFrame(self, tframe):
        self._tframes.append(tframe)

    def hasTFrames(self):
        return self._tframes
        
    def find_tframes(self, agent):
        "Returns a list of tframes the first time, then an empty list"
        tframes = self._tframes
        self._tframes = []
        return tframes
    
installConstructor(PseudoGoalEvent)

def find_do_tframes(agent, event, bindings, symbol, zexpr):
    imp = agent.getImp(symbol)
    debug("find_do_tframes, imp=%r", imp)
    if not (isinstance(imp, ActImpInt)): raise AssertionError, \
           "Symbol %s is not implemented as an action" % symbol
    return imp.tframes(agent, event, bindings, zexpr)

class DoEvent(GoalEvent):
    __slots__ = (
        "_symbol",
        )
    eventKind = "DO"
    cvcategory = "ED"
    def __init__(self, tframe, taskexpr, symbol):
        GoalEvent.__init__(self, tframe, taskexpr)
        bindings = tframe.getBaseBindings()
        self._symbol = symbol

    def find_tframes(self, agent):
        debug("DoEvent.find_tframes")
        try:
            imp = agent.getImp(self._symbol)
            tframes = imp.tframes(agent, self, self.getBindings(), self._taskexpr[0])
            debug("DoEvent.find_tframes -> %s", tframes)
            return tframes
        except NotLocatedError, err:
            errid = NEWPM.recordError()
            raise CapturedError(self._taskexpr, errid, "doing")

    def constructor_args(self):
        return [self._tframe, self._taskexpr, self._symbol]
    constructor_mode = "ZZZ" #contents are meaningless, only length matters

    def goalsym(self):
        return self._symbol

    def kind_string(self):
        return "Do"
installConstructor(DoEvent)

class AchieveColon(Imp):
    __slots__ = ()

    synchronous = True
    predsym = P_Achieve

    def tenter(self, agent, tframe, zexpr):
        bindings = tframe.getBaseBindings()
        if predSolve1(agent, bindings, zexpr[0]):
            return tframe.tfcompleted(agent, SUCCESS)
        else:
            step_fn(agent, bindings, EXECUTING, zexpr)
            symbol = bindings.bEntity(agent, zexpr[0])
            event = AchieveEvent(tframe, zexpr, symbol)
            return tframe.tfpost_subgoal(agent, event)

    def tsubgoal_complete(self, agent, tframe, zexpr, subevent, result):
        bindings = tframe.getBaseBindings()
        if result is SUCCESS:
            step_fn(agent, bindings, SUCCEEDED, zexpr)
        else:
            step_fn(agent, bindings, FAILED, zexpr)
        return tframe.tfcompleted(agent, result)
#     def thandlecfin(self, agent, tframe, subevent, result):
#         if result is SUCCESS:
#             step_fn(agent, tframe.getBaseBindings(), SUCCEEDED, self)
#             agent.post_event(GoalSucceededEvent(subevent))
#         else:
#             step_fn(agent, tframe.getBaseBindings(), FAILED, self)
#             agent.post_event(GoalFailedEvent(subevent, result))
#         tframe.t_result_pop(agent, result) # default is to pass s/f up


class AchieveEvent(GoalEvent):
    __slots__ = (
        "_symbol",
        )
    eventKind = "ACHIEVE"
    cvcategory = "EA"
    def __init__(self, tframe, taskexpr, symbol):
        GoalEvent.__init__(self, tframe, taskexpr)
        bindings = tframe.getBaseBindings()
        self._symbol = symbol

    def constructor_args(self):
        return [self._tframe, self._taskexpr, self._symbol]
    constructor_mode = "ZZZ" #contents are meaningless, only length matters

    def find_tframes(self, agent):
        predexpr = self._taskexpr[0]
        bindings = self._tframe.getBaseBindings()
        #predsym = bindings.getSymbolValue(agent, predexpr.functor)
        return get_all_tframes(agent,self,bindings,P_Achieve,self._symbol,predexpr)

    def goalsym(self):
        return self._symbol

    def kind_string(self):
        return "Achieve"
installConstructor(AchieveEvent)


class SetColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        bindings = tframe.getBaseBindings()
        step_fn(agent, bindings, EXECUTING, zexpr)
        value = termEvalErr(agent, bindings, zexpr[1])
        if not termMatch(agent, bindings, zexpr[0], value):
            step_fn(agent, bindings, FAILED, zexpr)
            s = bindings.constraintString(zexpr[0])
            raise LocatedError(zexpr, "Cannot set term %s to the calculated value" % s)
        step_fn(agent, bindings, SUCCEEDED, zexpr)
        return tframe.tfcompleted(agent, SUCCESS)

################################################################
class SeqColon(Imp):
    __slots__ = ()

    thas_local = True
    
    def tenter(self, agent, tframe, zexpr):
        if len(zexpr) > 0:
            return tframe.tfpost_child(agent, 0)
        else:
            return tframe.tfcompleted(agent, SUCCESS)

    def tresume(self, agent, tframe, zexpr):
        x = tframe.tfget()
        return tframe.tfpost_child(agent, x)

    def tchild_complete(self, agent, tframe, zexpr, index, result):
        next = index + 1
        if result == SUCCESS and next < len(zexpr):
            tframe.tfset(next)
            return tframe.tfyield(agent)
        else:
            return tframe.tfcompleted(agent, result)

################################################################
class OrColon(Imp):            # just perform the first option for now
    __slots__ = ()

    thas_local = False
    
    def tenter(self, agent, tframe, zexpr):
        if len(zexpr) > 0:
            return tframe.tfpost_child(agent, 0)
        else:
            return tframe.tfcompleted(agent, Failure(tframe, "No choices"))

    def tchild_complete(self, agent, tframe, zexpr, index, result):
        return tframe.tfcompleted(agent, result)

################################################################
# ContiguousTaskExpr

class ContiguousColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        if len(zexpr) > 0:
            return tframe.tfpost_child(agent, 0)
        else:
            return tframe.tfcompleted(agent, SUCCESS)
        
    def tresume(self, agent, tframe, zexpr):
        # Special case of top level task in a TaskExprTFrame:
        # tenter is never called directly
        # the first call on the taskexpr is a tresume
        return self.tenter(agent, tframe, zexpr)

    def tchild_complete(self, agent, tframe, zexpr, index, result):
        next = index + 1
        if result == SUCCESS and next < len(zexpr):
            return tframe.tfpost_child(agent, next)
        else:
            return tframe.tfcompleted(agent, result)

#LIST_IMP = ContiguousColon(Context.LIST_DECL)   # TODO: fix reference

################################################################
# ParallelTaskExpr

def parallel_tsubgoal_complete(agent, tframe, zexpr, subevent, result):
    """result=None - post goal for the first time if necessary
    result=SUCCESS - continue executing other branches if any
    result is a failure - interrupt other branches"""
    if result is None:
        children = subevent.hasTFrames()
        tframe.tfset(SUCCESS)
    else:
        children = agent.tframe_children(tframe)
        if result != SUCCESS and tframe.tfget() is SUCCESS: # first failure
            tframe.tfset(result)
            for child in children:
                agent.signal(child, INTERRUPT)
    if children:
        # repost subgoal - not finished yet
        return tframe.tfpost_subgoal(agent, subevent)
    else:
        return tframe.tfcompleted(agent, tframe.tfget())


class ParallelColon(Imp):
    __slots__ = ()

    thas_local = True      # first failure reported, otherwise SUCCESS
    
    def tenter(self, agent, tframe, zexpr):
        if len(zexpr) == 0:
            return tframe.tfcompleted(agent, SUCCESS)
        else:
            event = PseudoGoalEvent(tframe, zexpr)
            bindings = tframe.getBaseBindings()
            for component in zexpr:
                name = "%s-PARA"%tframe.name() # TODO: CHANGE TO objectId
                event.addTFrame(TaskExprTFrame(name, event, bindings, component))
            return parallel_tsubgoal_complete(agent, tframe, zexpr, event, None)

    def tsubgoal_complete(self, agent, tframe, zexpr, subevent, result):
        return parallel_tsubgoal_complete(agent, tframe, zexpr, subevent, result)

################################################################

class TryColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        return tframe.tfpost_child(agent, 0)

    def tchild_complete(self, agent, tframe, zexpr, index, result):
        if index%2 == 0:                # was a guard
            if result is SUCCESS:
                next = index + 1
            else:
                next = index + 2
            if next < len(zexpr):
                return tframe.tfpost_child(agent, next)
            else:
                return tframe.tfcompleted(agent, result)
        else:
            return tframe.tfcompleted(agent, result)

class TryexceptColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        return tframe.tfpost_child(agent, 0)

    def tchild_complete(self, agent, tframe, zexpr, index, result):
        if index == 0:
            if result is SUCCESS:
                return tframe.tfpost_child(agent, 1)
            patindex = 2
            while patindex < len(zexpr):
                if termMatch(agent, tframe.getBaseBindings(), zexpr[patindex], result):
                    return tframe.tfpost_child(agent, patindex + 1)
                patindex += 2
            else:
                return tframe.tfcompleted(agent, result)
        else:
            return tframe.tfcompleted(agent, result)

################################################################

NO_MATCHING_TASKEXPR = intern('NO_MATCHING_TASKEXPR')

class CondLikeColon(Imp):
    __slots__ = (
        )

    verbose = ABSTRACT
    
#     def __init__(self, term, *predtaskexprs):
#         TaskExpr.__init__(self, term, predtaskexprs, True)

    def tenter(self, agent, tframe, zexpr):
        length = len(zexpr)
        index = 0
        while index < length:
            zitem = zexpr[index]
            bindings = tframe.getBaseBindings()
            if predSolve1(agent, bindings, zitem):
                step_fn(agent, bindings, TESTTRUE, zitem)
                #step_fn(agent, bindings, SUCCEEDED, zitem)
                debug("predexpr %r, taskexpr %r", zitem, zexpr[index+1])
                next = index + 1
                if next >= length:
                    # No corresponding taskexpr
                    return tframe.tfcompleted(agent, SUCCESS)
                else:
                    return tframe.tfpost_child(agent, next)
            elif self.verbose:
                step_fn(agent, bindings, TESTFALSE, zitem)
                #step_fn(agent, bindings, FAILED, zitem)
            index += 2
        # No matching condition
        if self.verbose:
            step_fn(agent, bindings, FAILED, zitem)
        return self._tenter_no_match(agent, tframe)

    def tchild_complete(self, agent, tframe, ignore_zexpr, ignore_index, result):
        return tframe.tfcompleted(agent, result)

    def _tenter_no_match(self, ignore_agent, ignore_tframe):
        raise Unimplemented()


class SelectColon(CondLikeColon):
    __slots__ = ()

    verbose = True
    
    def _tenter_no_match(self, agent, tframe):
        result = TestFailure(tframe, "No optional has a valid condition")
        return tframe.tfcompleted(agent, result)

class ChoiceColon(SelectColon):
    __slots__ = ()
                

class WaitColon(CondLikeColon):
    __slots__ = ()

    verbose = False

    def _tenter_no_match(self, agent, tframe):
        return tframe.tfyield(agent)

    ##def tenter(self, agent, tframe, zexpr):
    ##    result = CondLikeColon.tenter(self, agent, tframe, zexpr)
    ##    ## TODO: if yield display a 'waiting' message
    ##    return result
        
    def tresume(self, agent, tframe, zexpr):
        return CondLikeColon.tenter(self, agent, tframe, zexpr)

class SucceedColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        return tframe.tfcompleted(agent, SUCCESS)
                
################################################################
# FailTaskExpr - do nothing

class FailColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        bindings = tframe.getBaseBindings()
        value = termEvalErr(agent, bindings, zexpr[0])
        result = FailFailure(tframe, value)
        return tframe.tfcompleted(agent, result)

################################################################
# ForallTaskExpr

class ForallSolutionsCollector(ConstructibleValue):
    __slots__ = (
        "vars",
        "solutions",
        )

    def __init__(self, vars, solutions):
        ConstructibleValue.__init__(self)
        self.vars = tuple(vars)
        self.solutions = list(solutions)
        
    def constructor_args(self):
        solns = [List(soln) for soln in self.solutions]
        return [List(self.vars), List(solns)]
    constructor_mode = "VV"

    def add_solution(self, agent, bindings):
        self.solutions.append([bindings.getVariableValue(agent, var) \
                               for var in self.vars])

    def finished(self):
        self.solutions.reverse()

    def pop_solution(self, agent, bindings):
        while self.solutions:
            solution = self.solutions.pop()
            for (value, var) in zip(solution, self.vars):
                #bindings.setVariableValue(agent, var, value)
                if not bindings.matchVariableValue(agent, var, value):
                    break # break out of 'for' loop
            else:                       # everything matched
                return True
        return False

    def __len__(self):
        return len(self.solutions)

installConstructor(ForallSolutionsCollector)

def constructForallSolutionsCollector(predexpr):
    from spark.internal.parse.expr import varsBeforeAndHere
    varsargs = varsBeforeAndHere(predexpr)[1]
    #varsargs = predexpr.free_nblocals_used_first_here() \ # TODO: ZZZZZZZ
    #           & predexpr.needed_after()
    return ForallSolutionsCollector(varsargs, [])
    

class ForallColon(Imp):
    __slots__ = ()

    thas_local = True                   # a ForallSolutionsCollector

    def _collect_solutions(self, agent, tframe, zexpr):
        # collect solutions
        # TODO: why use varsBeforeAndHere(zexpr[1]) rather than just zexpr[0]?
        collector = constructForallSolutionsCollector(zexpr[1])
        bindings = tframe.getBaseBindings() # using bindings.get method so need raw bindings
        for x in predSolve(agent, bindings, zexpr[1]):
            if x:
                collector.add_solution(agent, bindings)
        collector.finished()
        return collector

    def tenter(self, agent, tframe, zexpr):
        collector = self._collect_solutions(agent, tframe, zexpr)
        tframe.tfset(collector)
        return self.tchild_complete(agent, tframe, zexpr, 2, SUCCESS)

    def tchild_complete(self, agent, tframe, zexpr, index, result):
        # if (index != 2): raise AssertionError
        if result != SUCCESS:
            return tframe.tfcompleted(agent, result)
        else:
            return tframe.tfyield(agent)

    def tresume(self, agent, tframe, zexpr):
        collector = tframe.tfget()
        bindings = tframe.getBaseBindings()
        if collector.pop_solution(agent, bindings): # more solutions left
            return tframe.tfpost_child(agent, 2)
        else:
            return tframe.tfcompleted(agent, SUCCESS)


class ForallpColon(ForallColon):
    __slots__ = (
        )
    
    thas_local = True      # first failure reported, otherwise SUCCESS

    def tenter(self, agent, tframe, zexpr):
        collector = self._collect_solutions(agent, tframe, zexpr)
        bindings = tframe.getBaseBindings()
        #clone bindings for each parallel branch
        #NOTE: this implementation results in bindings.copy()
        #getting called two times more than necessary.
        event = PseudoGoalEvent(tframe, zexpr)
        bindingscopy = bindings.copy()
        while collector.pop_solution(agent, bindingscopy):
            name = "%s.%s"%(tframe.name(), len(collector))
            event.addTFrame(TaskExprTFrame(name, event, bindingscopy, zexpr[2]))
            bindingscopy = bindings.copy()
        return parallel_tsubgoal_complete(agent, tframe, zexpr, event, None)

    def tsubgoal_complete(self, agent, tframe, zexpr, subevent, result):
        return parallel_tsubgoal_complete(agent, tframe, zexpr, subevent, result)


################################################################
# ForinTaskExpr

class ForinColon(Imp):
    __slots__ = ()

    thas_local = True                   # remaining solutions

    def tenter(self, agent, tframe, zexpr):
        bindings = tframe.getBaseBindings()
        solutions = list(termEvalErr(agent, bindings, zexpr[1])) 
        solutions.reverse()
        from spark.lang.list import Accumulator
        tframe.tfset((Accumulator(solutions),Accumulator(()))) # an Accumulator is persistable
        return tframe.tfyield(agent)
        #return self.tchild_complete(agent, tframe, zexpr, 2, SUCCESS)

    def tchild_complete(self, agent, tframe, zexpr, index, result):
        # if (index != 2): raise AssertionError
        if result is SUCCESS:
            (_solutions,results) = tframe.tfget()
            bindings = tframe.getBaseBindings()
            r = List([termEvalErr(agent, bindings, zitem) for zitem in zexpr[3::2]])
            results.append(r)
            return tframe.tfyield(agent)
        else:
            return tframe.tfcompleted(agent, result)

    def tresume(self, agent, tframe, zexpr):
        bindings = tframe.getBaseBindings()
        (solutions,results) = tframe.tfget()
        if solutions:
            solution = solutions.pop()
            if termMatch(agent, bindings, zexpr[0], solution):
                return tframe.tfpost_child(agent, 2)
            else:
                raise zexpr.error("Pattern does not match value %s", solution)
        else:
            lsts = zip(*results)       # inverse of zip
            for (zitem, lst) in zip(zexpr[4::2], lsts):
                if not termMatch(agent, bindings, zitem, lst):
                    raise ziterm.error("Pattern does not match result %s", lst)
            return tframe.tfcompleted(agent, SUCCESS)
            
################################################################
# WhileTaskExpr

class WhileColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        return self.tchild_complete(agent, tframe, zexpr, 2, SUCCESS)

    def tchild_complete(self, agent, tframe, zexpr, index, result):
        # if (index != 2): raise AssertionError
        if result is SUCCESS:
            return tframe.tfyield(agent)
        else:
            tframe.tfcompleted(agent, result)

    def tresume(self, agent, tframe, zexpr):
        bindings = tframe.getBaseBindings()
        if predSolve1(agent, bindings, zexpr[1]):
            tframe.tfpost_child(agent, 2)
        else:
            tframe.tfcompleted(agent, SUCCESS)
            
################################################################
# RepeatTaskExpr


################################################################

# class BracketTaskExpr(ContiguousTaskExpr):
#     __slots__ = ()

#     def tresume(self, agent, tframe, zexpr):
#         # This is here purely for the case of starting a top level taskexpr
#         return self.tenter(agent, tframe, zexpr)

# class TaskBodyTag(TaskExpr):
#     __slots__ = ()
    

# class LabelTaskBodyTag(TaskBodyTag):
#     __slots__ = (
# #         "ltbtlabel",
#         )
#     link_class = TaskBodyTag
#     def __init__(self, term, labelpathexpr):
#         TaskBodyTag.__init__(self, term, (), True)
# #        self.ltbtlabel = labelpathexpr.get_value()


class ContextColon(Imp):
    __slots__ = ()
    
    def tenter(self, agent, tframe, zexpr):
        predexpr = zexpr[0]
        bindings = tframe.getBaseBindings()
        #step_fn(agent, bindings, TESTING, predexpr)
        if predSolve1(agent, bindings, predexpr):
            step_fn(agent, bindings, TESTTRUE, predexpr)
            #step_fn(agent, bindings, SUCCEEDED, predexpr)
            result = SUCCESS
        else:
            step_fn(agent, bindings, TESTFALSE, predexpr)
            #step_fn(agent, bindings, FAILED, predexpr)
            if len(zexpr)>1:
                formatString = termEvalErr(agent, bindings, zexpr[1])
                formatArgs = [termEvalErr(agent, bindings, zitem) \
                              for zitem in zexpr[2:]]
                from spark.lang.builtin import prin
                err = prin(formatString, formatArgs)
            else:
                err = "Context failed"
            result = TestFailure(tframe, err)
        return tframe.tfcompleted(agent, result)

class ConcludeColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        bindings = tframe.getBaseBindings()
        step_fn(agent, bindings, EXECUTING, zexpr)
        predUpdate(agent, bindings,  zexpr[0])
        return tframe.tfcompleted(agent, SUCCESS)


class RetractColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        bindings = tframe.getBaseBindings()
        step_fn(agent, bindings, EXECUTING, zexpr)
        predRetractall(agent, bindings,  zexpr[0])
        return tframe.tfcompleted(agent, SUCCESS)


class RetractallColon(Imp):
    __slots__ = ()

    def tenter(self, agent, tframe, zexpr):
        bindings = tframe.getBaseBindings()
        step_fn(agent, bindings, EXECUTING, zexpr)
        predRetractall(agent, bindings,  zexpr[1])
        return tframe.tfcompleted(agent, SUCCESS)

class GoalMetaEvent(MetaFactEvent):
    __slots__ = ()
    def base_event(self):
        return self._fact[0]

class GoalPostedEvent(GoalMetaEvent):
    __slots__ = ()
    def __init__(self, *args):
        GoalMetaEvent.__init__(self, *args)
        if isinstance(args[0], DoEvent):
            get_sdl().logger.debug("action started: [%s]", args[0]._symbol)
            #print "Args: %s"%(args[0].getArgs(G._AGENT),)

    numargs = 1
    event_type = GOAL_POSTED
    constructor_mode = "I"
installConstructor(GoalPostedEvent)

class GoalSucceededEvent(GoalMetaEvent):
    __slots__ = ()
    def __init__(self, *args):
        GoalMetaEvent.__init__(self, *args)
        if isinstance(args[0], DoEvent):
            get_sdl().logger.debug("action succeeded: [%s]", args[0]._symbol)

    numargs = 1
    event_type = GOAL_SUCCEEDED
    constructor_mode = "I"
installConstructor(GoalSucceededEvent)


class GoalTerminatedEvent(GoalMetaEvent):
    __slots__ = ()
    numargs = 1
    event_type = GOAL_TERMINATED
    constructor_mode = "I"
installConstructor(GoalTerminatedEvent)

class GoalFailedEvent(GoalMetaEvent):
    __slots__ = ()
    
    def __init__(self, *args):
        GoalMetaEvent.__init__(self, *args)
        if isinstance(args[0], DoEvent):
            # TODO: clean this up - this is a hack - DNM
            try:
                reason = str(args[1].getFailureValue())
            except AttributeError:
                reason = str(args[1])
            get_sdl().logger.debug("action failed: [%s]\n\treason: %s", args[0]._symbol, reason)
        
    numargs = 2
    event_type = GOAL_FAILED
    constructor_mode = "IV"
installConstructor(GoalFailedEvent)
