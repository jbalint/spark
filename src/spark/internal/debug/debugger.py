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
#* "$Revision:: 344                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
import sys
import threading

from spark.internal.common import NEWPM, re_raise
from spark.internal.version import *
from spark.internal.exception import LowError, SPARKException, LocatedError, Failure

from spark.internal.parse.usages import ACTION_DO, TERM_EVAL, PRED_SOLVE

from spark.internal.parse.processing import getPackageDecls, ensure_modpath_installed
from spark.internal.persist import remove_persisted_files
from spark.internal.instrument import report_instrumentation_point, \
     PRE_USER_MODULE_LOAD, POST_USER_MODULE_LOAD, USER_PERSIST_COMMAND

from spark.internal.debug.trace import *

from spark.internal.parse.basicvalues import Symbol
from spark.internal.parse.processing import set_default_module, get_default_module

from spark.internal.engine.agent import Agent
from spark.internal.engine.find_module import find_install_module, clear_all_modules
from spark.pylang.implementation import PredImpInt, ActImpInt, FunImpInt

import time
#exitcodes
EC_ARGS_ERROR = 1 #invalid arguments to program
EC_LOAD_ERROR = 2 #error loading arguments
EC_DONE = 3 #nothing left to do


# Last agent created
# Can be accessed from the python debugger as G._AGENT
_AGENT = None 

def load_module(agent, modname):
    chron = time.time()
    succeeds = 1
    try:
        #PERSIST:INSTRUMENT        
        report_instrumentation_point(agent, PRE_USER_MODULE_LOAD)
        mod = ensure_modpath_installed(Symbol(modname))
        if not mod:
            print "=== COULD NOT INSTALL MODULE %s ==="%modname
            succeeds = 0
        currMod = get_default_module()
        #check for equality here because we are reporting instrumentation points
        if mod is not currMod:
            set_default_module(mod) 
            if not ensure_default_module_loaded(agent):
                print "=== COULD NOT LOAD MODULE %s ==="%modname
                succeeds = 0
            #PERSIST:INSTRUMENT        
            report_instrumentation_point(agent, POST_USER_MODULE_LOAD)
    except SPARKException:
        errid = NEWPM.displayError()
    chron = time.time() - chron
    print "Total Loading Time: %3.4f seconds."%chron
    #-*-*-*-*-*-* This is a hack to remove the logs from the console. A better solution is needed later.
    from spark.util.logger import get_sdl
    get_sdl().log("Default Module: %s", modname)
    return succeeds
    

def user_directed_persist(agent):
    #PERSIST:INSTRUMENT
    report_instrumentation_point(agent, USER_PERSIST_COMMAND)    

def get_modname():
    """helper function to hide the internal workings of the shifting module API"""
    mod = get_default_module()
    if mod is None:
        return "spark.lang.builtin"
    else:
        return mod.get_modpath().name

def ensure_default_module_loaded(agent):
    # quite a hack
    #TODO: REPLACE WITH INTERNAL
    return agent.eval('1', get_modname())

def new_agent(currentAgent, stepInitFn=None, traceFn=None):
    """initialize a new agent. if the step init functions are passed in, the debugger will also be initialized."""
    if currentAgent is not None:
        currentAgent.stop_executor()
        get_step_controller().step() #to break the step lock
    agent = Agent("A")
    # Keep a reference to this agent for ease of debugging
    global _AGENT
    _AGENT = agent
    
    agent.start_executor()
    if stepInitFn and traceFn:
        init_trace(agent, stepInitFn, traceFn)
    else:
        if not (not stepInitFn and not traceFn): raise AssertionError, \
           "new_agent: Either zero or both of stepInitFn and traceFn must be specified"
    return agent

def dispose(agent):
    if agent is not None:
        agent.stop_executor()
    #clean up the tracing so that the agent thread can terminate properly
    if get_step_controller() is not None:
        get_trace_filters().clear()
        disable_stepping()
        get_step_controller().step() #to break any step lock

def debugger_cleanup():
    """prepare resources for exit"""
    trace_cleanup()

def reset(agent):
    dispose(agent)
    clear_all_modules()
                
def clear_all(agent):
    # clear everything about the agent state
    disable_stepping()
    disable_tracing()
    agent.stop_executor()
    while agent._executor_thread:
        import time
        print "Waiting for executor to die"
        time.sleep(1)
        
    agent.reInit()
    clear_all_modules()     # clear out cached modules
    agent.start_executor()

def clear_filters():
    get_trace_filters().clear()
    
def add_trace_monitor(monitor_str):
    get_trace_filters().add_monitor(monitor_str)

def add_trace_ignore(ignore_str):
    get_trace_filters().add_ignore(ignore_str)

#
# It would be more efficient to combine the get_local_foo(agent) methods
# into a single generic method, but this implementation makes it easier for the
# SPARK IDE to make calls
#

def get_local_predicates(agent):
    return _collect_symbols_sorted(agent, PRED_SOLVE, False)

def get_local_functions(agent):
    return _collect_symbols_sorted(agent, TERM_EVAL, False)
    
def get_local_tasks(agent):
    return _collect_symbols_sorted(agent, ACTION_DO, False)

def get_all_predicates(agent):
    return _collect_symbols_sorted(agent, PRED_SOLVE, True)

def get_all_functions(agent):
    return _collect_symbols_sorted(agent, TERM_EVAL, True)
    
def get_all_tasks(agent):
    return _collect_symbols_sorted(agent, ACTION_DO, True)

def _collect_symbols(agent, usage, collectAll):
    #ensure_default_module_loaded(agent)
    if collectAll:  
        syms = agent.getDeclaredSymbols()
        decls = [agent.getDecl(n) for n in syms]
        names = [decl.asSymbol() for decl in decls \
                 if decl is not None and decl.optMode(usage)]
    else:
        mod = get_default_module()
        if mod is None:
            raise LowError("Default module is not loaded")
        decls = getPackageDecls(agent, mod.filename)
        names = [decl.asSymbol() for decl in decls \
                 if decl is not None and decl.optMode(usage)]
    return names

def _collect_symbols_sorted(agent, usage, collectAll):
    names = _collect_symbols(agent, usage, collectAll)
    names.sort()
    return names

def execute_spark_main(agent, module_args):
    """module_args must be in an evaluable/string representation"""
    mod = get_default_module()
    if mod is None:
        print "WARNING - NO DEFAULT MODULE SO MAIN IS NOT BEING RUN"
        return None
    from spark.internal.parse.processing import OK4
    if not mod.atLeast(OK4):
        # TODO: Clean this up - it is ugly
        from spark.internal.parse.processing import FILENAME_SPU
        FILENAME_SPU.get4(mod.filename)
        if not mod.atLeast(OK4):
            print "WARNING - MODULE NOT OK4 AND SO MAIN IS NOT BEING RUN", mod
            return None
    main = mod.main_name
    if main is None:
        return None
    try:
        ext = agent.run("[do: (%s [%s])]"%(main, " ".join(module_args)), get_modname())
        x = ext.wait_result()
    except Failure, e:
        print "The main action of file %s failed"%mod.filename
        return e
    except AnyException, e:             # TODO: need to be updated to new core
        print "The main action of file %s failed"%mod.filename
        return e
