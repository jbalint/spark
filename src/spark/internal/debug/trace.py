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
#* "$Revision:: 128                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from threading import Condition

from spark.internal.version import *
from spark.internal.common import NEWPM, ABSTRACT
from spark.internal.parse.expr import varsBeforeAndHere
from spark.internal.parse.basicvalues import value_str
from spark.internal.exception import LowError

#
# NOTE: all of the code written here is very single-agent oriented.
# It will have to be heavily retooled for multiagent SPARK
#

def NO_TRACE(agent, bindings, event, expr, info=""):
    #even though we're not tracing, still have to log
    if log_file is None:
        return
    try:
        varvals = variables(bindings, event, expr)
    except:
        errid = NEWPM.displayError()
        varvals = "ERROR PRINTING VARS"
    blevel = bindings_level(bindings)
    event_str = str(event)
    term_str = str(expr)
    vars_str = str(varvals)
    log_file.write("*"*blevel+' '+event_str+' '+term_str+' BINDINGS: '+vars_str+info+'\n')

def NO_STEP(agent, bindings, event, expr, info=""):
    #pass through to whatever the tracing fn might be
    _trace_fn(agent,bindings,event,expr)

#constants for _step_filter
LVL_STEP_INTO = 1
LVL_STEP_OVER = 2

log_file = None
step_controller = None
_trace_fn = NO_TRACE
_step_fn = NO_STEP
_is_stepping = False
#_is_tracing = False
_step_filter = LVL_STEP_INTO

STEP = None
TRACE = None

# TODO: we currently step at the same level regardless of actual step setting

def trace_cleanup():
    if log_file is not None:
        log_file.flush()
        log_file.close()
    #clean up the tracing so that the agent thread can terminate properly
    if get_step_controller() is not None:
        get_trace_filters().clear()
        disable_stepping()
        get_step_controller().step() #to break any step lock

def init_trace(agent, step_init_fn, trace_fn):
    """init function for tracing that abstracts differences between tracing in the python/jython
    interpreter and tracing within the Spark IDE.
    step_init is a function that takes in an agent param and returns a StepTrace object to
    use during stepping, step_trace_init is a function that takes in an agent param and returns
    a StepTrace object to use during stepping with tracing enabled. trace_fn is a function
    appropriate for calls to set_trace_fn()"""
    global STEP, TRACE, step_controller
    STEP = step_init_fn(agent)
    TRACE = trace_fn
    #req'd to init step_controller to non-None value. Once we set it to STEP we should be very
    #careful about changing its value as the existing controller may be pausing execution.
    step_controller = STEP
    #_trace_fn and _step_fn may be pointing to an older trace function
    disable_stepping()
    disable_tracing()
    
def get_step_controller():
    return step_controller

def set_trace_fn(fn):
    global _trace_fn
    _trace_fn = fn

#note: defined with this get-style signature even though it's more inconvenient in order to prevent older
#code from thinking that it should still call trace_fn instead of step_fn
def get_trace_fn():    
    return _trace_fn
    
# def set_tracing(boolval):
#     global _is_tracing
#     _is_tracing = boolval

def set_step_fn(fn):
    global _step_fn
    _step_fn = fn

def get_step_fn():
    return _step_fn

def set_stepping(boolval):
    global _is_stepping
    _is_stepping = boolval

def _set_step_level(level):
    #XXX: currently ignore step_filter
    global _step_filter
    step_filter = level
    
def get_trace_fn():
    return _trace_fn

def set_log_file(log_file_handle):
    global log_file
    log_file = log_file_handle
    #make sure 'print' commands get logged as well
    from spark.lang.builtin import set_print_log_file    
    set_print_log_file(log_file)

def step_into():
    if _is_stepping:
        _set_step_level(LVL_STEP_INTO)
        step_controller.step()

def step_over():
    if _is_stepping:
        _set_step_level(LVL_STEP_OVER)        
        step_controller.step()

def enable_stepping():
    if not _is_stepping:    
        set_stepping(True)
        set_step_fn(STEP)

def disable_stepping():
    if _is_stepping:    
        set_stepping(False)
        set_step_fn(NO_STEP)
        #release currently stepping process but leave the step controller defined
        step_controller.step()

def enable_tracing():
    #set_tracing(True)
    set_trace_fn(TRACE)

def disable_tracing():
    #set_tracing(False)    
    set_trace_fn(NO_TRACE)  

EXECUTING = intern("EXECUTING")
#TESTING = intern("TESTING")
TESTTRUE = intern("TESTTRUE")
TESTFALSE = intern("TESTFALSE")
WAITING = intern("WAITING")
WAIT_FINISHED = intern("WAIT_FINISHED")
#EXECUTED = intern("EXECUTED")
#USING = intern("USING")
STARTING = intern("STARTING")
SUCCEEDED = intern("SUCCEEDED")
FAILED = intern("FAILED")
EVENTS = (EXECUTING, WAITING, WAIT_FINISHED, STARTING, SUCCEEDED, FAILED, TESTTRUE, TESTFALSE)
END_EVENTS = (SUCCEEDED, TESTTRUE)
#STARTING_INTENTION = intern("STARTING_INTENTION")
#SUCCEEDED_INTENTION = intern("SUCCEEDED_INTENTION")
#FAILED_INTENTION = intern("FAILED_INTENTION")

def short_str(x, maxlength=70):
    s = str(x)
    if len(s) > maxlength - 3:
        return s[:maxlength-3]+"..."
    else:
        return s

def bindings_level(bindings):
    return bindings.level()
#     from spark.internal.repr.varbindings import ExprBindings
#     if isinstance(bindings, ExprBindings):
#         return bindings_level(bindings.pat_bindings)+1
#     else:
#         return 0

def PRINT_TRACE(agent, bindings, event, expr, info=""):
    passes_filters = get_trace_filters().passes_filters(agent, bindings, event, expr, info)
    #check to see if we should do the effort of creating the debug string
    if not passes_filters and log_file is None:
        return
    try:
        varvals = variables(bindings, event, expr)
    except:
        errid = NEWPM.displayError()
        varvals = "ERROR PRINTING VARS"
    # kwc: i wrote the print to stdout and file this way so that there is a minimal
    # performance hit.  the shorter way of writing this with just print statement
    # formatting was making the logging horribly slow.
    blevel = bindings_level(bindings)
    try:
        event_str = str(event)
    except:
        errid = NEWPM.displayError()
        event_str = "ERROR PRINTING EVENT"
    term_str = str(expr)
    vars_str = str(varvals)
    print_str = "*"*blevel+' '+event_str+' '+term_str+' BINDINGS: '+vars_str+info

    # trace filtering
    # - we filter stuff printed to stdout.
    # - everything gets logged to the logfile (no filtering)
    if passes_filters:
        print print_str
    
    if log_file is not None:
        log_file.write(print_str+'\n')
        #need to figure out a better way to flush.  flushing at this level of
        #granularity is too much of a performance hit
        #log_file.flush()


def variables(bindings, event, expr):
    if event in END_EVENTS:
        vars = varsBeforeAndHere(expr)[2]
    else:
        vars = varsBeforeAndHere(expr)[0]
        #expr.free_vars() & (expr.used_before() | expr.parameters_bound(bindings))
    return ", ".join(["%s=%s"%(str(var), \
                               optionalGetVariableValueString(bindings, var))\
                      for var in vars])

def optionalGetVariableValueString(bindings, var):
    try:
        return value_str(bindings.getVariableValue(ABSTRACT, var))
    except LowError:
        errid = NEWPM.displayError()
        print "VARIABLE %s WAS NOT BOUND CORRECTLY!!!"%var
        return "???"
    
def basename(x):
    index = x.find("#")
    if index < 0:
        return x
    else:
        return x[:index]

#call the currently defined step/tracing functionx
def step_fn(agent, bindings, event, expr, info=""):
    _step_fn(agent, bindings, event, expr, info)


################################################################

# WARNING: The fact that proceed 
class StepTrace(object):
    __slots__ = (
        "_proceed",
        "_agent",
        )
    def __init__(self, agent):
        self._proceed = False
        self._agent = agent

    def __call__(self, agent, bindings, event, expr, info=""):
        #expect this to happen for now in SPARK IDE unit testing
        #where we are rapidly creating new agents
        if self._agent != agent:
            return
        #if (self._agent != agent): raise AssertionError, \
        #       "The agent in the stepping/tracing controller %s "\
        #       "is different from the agent being stepped/traced %s"\
        #       %(self._agent, agent)

        _trace_fn(agent, bindings, event, expr, info)
        
        # step filtering
        # NOTE:XXX: we may want to figure out a way to only have to do this once per step,
        # instead of once for the trace fn and once for the step
        if not get_trace_filters().passes_filters(agent, bindings, event, expr, info):
            return
        
        self._proceed = False # do this before _callback to avoid race conditions
        wait = self.on_event(agent, bindings, event, expr, info)
        if wait and not self._proceed:
            # Clear something_to_do so we can wait for an event
            agent._something_to_do_event.clear()
            # repeatedly handle tests, but ONLY tests
            while not self._proceed:
                agent.process_tests()
                agent._something_to_do_event.wait()
                agent._something_to_do_event.clear()
            # We may have missed processing something other than a test
            agent._something_to_do_event.set()
            #print "step complete"

    def on_event(self, agent, bindings, event, expr, info):
        # return True if you should wait or False if you should not
        raise Exception("No on_event method defined")

    def proceed(self):
        self._proceed = True
        self._agent._something_to_do_event.set()
        

class StepController(StepTrace):

    def on_event(self, agent, bindings, event, expr, info):
        return True

    def step(self):
        self.proceed()

MONITOR = intern("MONITOR")
IGNORE = intern("IGNORE")

class StepTraceFilters(object):
    __slots__ = (
        #filters is a list of tuples (FILTERTYPE, FILTERSTRING),
        #where FILTERTYPE is either MONITOR or IGNORE
        "_typefilters",
        "_filters"
        )
    
    def __init__(self):
        self._filters = []
        self._typefilters = []        

    def clear(self):
        self._filters = []
        self._typefilters = []        

    def _insert_ignore(self, filterlist, ignore_string):
        #insert the ignores after the monitors
        for i in range(0, len(filterlist)):
            if filterlist[i][0] == IGNORE:
                filterlist.insert(i, (IGNORE, ignore_string))
                break
        else:
            filterlist.append((IGNORE, ignore_string))

    def add_ignore(self, ignore_string):
        self._remove_filter(ignore_string)
        if ignore_string in EVENTS:
            self._insert_ignore(self._typefilters, ignore_string)
        else:
            self._insert_ignore(self._filters, ignore_string)

    def add_monitor(self, monitor_string):
        #always insert monitors at the beginning
        self._remove_filter(monitor_string)
        if monitor_string in EVENTS:
            self._typefilters.insert(0, (MONITOR, monitor_string))
        else:
            self._filters.insert(0, (MONITOR, monitor_string))

    def _remove_filter(self, filter_string):
        for filt in self._typefilters:
            if filt[1] == filter_string:
                self._typefilters.remove(filt)
                break
        else:
            for filt in self._filters:
                if filt[1] == filter_string:
                    self._typefilters.remove(filt)
                    break

    def sub_passes_filter(self, filter, strval):
        """check to see if the step/trace event passes an individual filter.
        this is an internal method"""
        #print "FILTER:FILTER IS (%s,%s)"%(filter[0], filter[1])
        #print "FILTER: MATCH STR[%s]"%str
        idx = strval.find(filter[1])
        retval = False
        if idx > -1:
            return filter[0] == MONITOR
        return filter[0] == IGNORE

    def passes_filters(self, agent, bindings, event, expr, info):
        vars = str(variables(bindings, event, expr))
        strval = "%s %s %s %s"%(event, expr, vars, info)
        if not self.passes_filters_str(self._typefilters, strval):
            return False
        return self.passes_filters_str(self._filters, strval)        

    def passes_filters_str(self, filterlist, strval):
        """return True or False depending on whether or not the
        step/trace event passes the current set of filters."""
        
        # filters are processed in order.  if the first filter
        # is a MONITOR, then the default is to exclude all events.
        # if the first filter is an IGNORE, then the default is the
        # include all events.
        #
        # consecutive MONITORs are disjunctive.  e.g.
        # (MONITOR, "FOO"), (MONITOR, "BAR") is equivalent to
        # MONITOR "FOO" OR "BAR"
        #
        # consecutive IGNOREs are disjunctive.  e.g.
        # (IGNORE, "FOO"), (IGNORE, "BAR") is equivalent to
        # IGNORE "FOO" OR "BAR"
        #
        # a MONITOR followed by an IGNORE (and vice versa)
        # is conjunctive.  e.g.
        # (MONITOR, "FOO"), (IGNORE, "BAR") is equivalent to
        # MONITOR "FOO" AND (NOT "BAR")
        #
        # DeMorgan's Law makes it easy to turn disjunctive
        # IGNOREs into conjunctive logic.  Disjunctive
        # MONITORs are a little bit harder.

        #check to see if we have any filters
        if not len(filterlist):
            return True
        
        mode = filterlist[0][0]
        current_match = False
        #print "FILTER:----------------------------"
        for filterval in filterlist:
            #print "FILTER:current_match is %s"%current_match
            
            # if filter[0] equals the mode, then we are within the same
            # disjunction.  if it is not equal, then we enter into a conjunction
            # with the next set of terms
            if filterval[0] == mode:
                #disjunctive:
                # check to see if any of the terms in the current set matches.
                # current_match will go to True once we have found a match.  once
                # this occurs we don't have to match within this set anymore.
                if current_match:
                    #already matched within this disjunction
                    continue
                else:
                    #check to see if this filter matches
                    current_match = self.sub_passes_filter(filterval, strval)
            else:
                #conjunctive:
                # check the value of current_match.  if it is false, it means that
                # the previous set of terms was false, so we can stop now as
                # we know the conjunction is false.  otherwise, start checking
                # the next set to see if it passes.
                if not current_match:
                    #print "FILTER:previous disjunction failed, does not pass filters"
                    return False
                #start matching within next set
                current_match = self.sub_passes_filter(filterval, strval)
            #update the mode
            mode = filterval[0]
        
        return current_match

#filters handle that the interpreter will access using get_trace_filters()
_trace_filters = StepTraceFilters()

def get_trace_filters():
    return _trace_filters

def test_filters():
    """test the behavior of the filters"""
    f = StepTraceFilters()
    f.add_ignore("forall")    
    f.add_monitor("print")
    f.add_monitor("SUCCEEDED")
    f.add_ignore("FAILED")
    f.add_monitor("plint")    
    f.add_monitor("EXECUTING")
    print "FILTERS: ", f._filters
    print "TYPEFILTERS: ", f._typefilters    
    tests = [ "SUCCEEDED: [do: (foo)]",
              "FAILED: [do: (foo)]",
              "BLAH: [do: (printx)]",
              "BLAH: [do: (plint)]",
              "SUCCEEDED: [do: (plint)]",
              "FAILED: [do: (plint)]",              
              "FAILED: [do: (print foo)]",
              "SUCCEEDED: [forall: (foo)]" ]
    for t in tests:
        print t, f.passes_filters(t)
              


################################################################


class _Tracing:

    def do_try(self, agent, bindings, expr):
        bind = ["%s=%s"%(v, bindings.getVariableValue(agent, v)) \
                for v in varsBeforeAndHere(expr)[0]]
        from spark.internal.debug.trace import PRINT_TRACE
        PRINT_TRACE(agent, bindings, "Try", expr, (", ".join(bind)))
        #print "Try %s: %s"%(expr, ", ".join(bind))
    def do_retry(self, agent, bindings, expr):
        from spark.internal.debug.trace import PRINT_TRACE
        PRINT_TRACE(agent, bindings, "Retry", expr)
        #print "Retry %s"%expr
    def do_fail(self, agent, bindings, expr):
        from spark.internal.debug.trace import PRINT_TRACE
        PRINT_TRACE(agent, bindings, "Fail", expr)
        #print "Fail %s"%expr
    def do_succeed(self, agent, bindings, expr):
        bind = ["%s:=%s"%(v, bindings.getVariableValue(agent, v)) \
                for v in varsBeforeAndHere(expr)[1]]
        from spark.internal.debug.trace import PRINT_TRACE
        PRINT_TRACE(agent, bindings, "Succeed", expr, (", ".join(bind)))
        #print "Succeed %s: %s"%(expr, ", ".join(bind))

TRACING = _Tracing()
