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
#* "$Revision:: 327                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
import string
from spark.internal.version import *
from spark.internal.debug.debugger import *
from spark.internal.exception import SPARKException
from spark.internal.parse.basicvalues import Symbol, value_str
from spark.lang.builtin import requiredargnames, restargnames
from spark.internal.common import SUCCESS, NEWPM
from spark.util.pyconsole import runPyConsole

# exported values
__all__ = ['process_command', \
           'print_version', 'print_help', \
           # for spark.main
           'PRINT_TRACE', 'StepController', 'execute_spark_main', 'dispose'  
           ]

def process_command(agent, next):
    """Process a command in the interpreter loop. Return True if interpreter should
    exit, False otherwise"""
    #NOTE: updates to the commands in this list need to be mirrored in print_help()
    try:
        # Things that can be done whether we are stepping or not
        if next.startswith("module "):        # change module
            text = next[6:].strip()
            if (len(text)):     
                load_module(agent, text)
            else:
                print 'Please enter in a module name, e.g. "module spark.lang.builtin"'
        elif next == "trace":
            print "Turning tracing on."
            enable_tracing()
        elif next == "notrace":
            print "Turning tracing off."
            disable_tracing()
        elif next == "persist":
            print "Persisting SPARK agent knowledge base"
            user_directed_persist(agent)
        elif next == "step" or next == "pause":
            print "Turning stepping on."
            enable_stepping()
        elif next == "nostep" or next == "resume":
            print "Turning stepping off."
            disable_stepping()
        elif next.startswith("monitor "):
            text = next[8:].strip()
            if (len(text)):     
                add_trace_monitor(text)
            else:
                print 'Please type in a string to ignore during tracing, e.g. "ignore EXECUTING"'                    
        elif next.startswith("ignore "):
            text = next[7:].strip()
            if (len(text)):                
                add_trace_ignore(text)
            else:
                print 'Please type in a string to monitor for during tracing, e.g. "monitor FAILED"'
        elif next == "exit":
            print "exiting SPARK interpreter"
            return True
        elif next == "help":
            print_help()
        elif next == "clear all":      # essentially undoes everything from this session
            print "removing all new facts and intentions..."
            clear_all(agent)
            print "session refreshed"
        elif next == "clear filters":
            clear_filters()
            print "step/trace filters cleared"

        elif next.startswith("get "):
            if next == "get intentions":    # just prints intention ID #s
                #XXX: get rid of java calls (kwc)
                print "Root Objectives:"
                print "--------------------"
                intentions = agent.get_intentions()
                for intent in intentions:
                    print " ", intent
                
                try:
                    from com.sri.ai.spark.model.task import IntentionStructure
                    from com.sri.ai.spark.model.util import TextModel
                    print ""
                    print "Task structure:"
                    print "--------------------"
                    structure = IntentionStructure(agent, agent._intention_structure)
                    print TextModel.getIntentionStructureModel(structure)
                except ImportError:
                    pass

            #XXX:TODO:there is an excessive number of e_d_m_l calls here.
            #talk to dm to see if this is necessary
            elif next == "get predicates":
                ensure_default_module_loaded(agent)
                names = get_local_predicates(agent)
                _print_sym_list(agent, "displaying local predicates", names)
            elif next == "get functions":
                ensure_default_module_loaded(agent)
                names = get_local_functions(agent)
                _print_sym_list(agent, "displaying local functions", names) 
            elif next == "get tasks":
                ensure_default_module_loaded(agent)
                names = get_local_tasks(agent)
                _print_sym_list(agent, "displaying actions", names)
            elif next == "get all predicates":
                ensure_default_module_loaded(agent)
                names = get_all_predicates(agent)
                _print_sym_list(agent, "displaying all predicates", names)
            elif next == "get all functions":
                ensure_default_module_loaded(agent)
                names = get_all_functions(agent)
                _print_sym_list(agent, "displaying all functions", names)
            elif next == "get all tasks":
                ensure_default_module_loaded(agent)
                names = get_all_tasks(agent)
                _print_sym_list(agent, "displaying actions", names)
            else:
                print "Invalid command: don't know how to get '%s'"%next[4:]

        elif next.startswith("debugon "):
        	if next == "debugon oaa":
				M.spark__io__oaa.debug.on()
	        elif next == "debugon pubsub":
				M.iris__events.debug.on()
	        elif next == "debugon tir":
				M.task_manager__tir.debug.on()
	        else:
				print "Invalid command: don't know how to debugon '%s'"%next[8:]
        elif next.startswith("debugoff "):
        	if next == "debugoff oaa":
				M.spark__io__oaa.debug.off()
	        elif next == "debugoff pubsub":
				M.iris__events.debug.off()
	        elif next == "debugoff tir":
				M.task_manager__tir.debug.off()
	        else:
				print "Invalid command: don't know how to debugoff '%s'"%next[9:]
        elif next.startswith("debug"):
            debug_arg = next[5:].strip()
            id_num = None
            if debug_arg != "":
                try:
                    id_num = string.atoi(debug_arg)
                except AnyException:
                    errid = NEWPM.displayError()
            NEWPM.pm(id_num)
        elif next == "python":
            runPyConsole()
        elif next == "" and get_step_controller().step():
            pass
        elif next == "":
            print "ignoring blank input line"
        # Remaining commands require the kb lock (don't block!)
        else:
            # We have the KB lock
            if next.startswith("test "):
                agent.test(next[4:], get_modname())
            elif next.startswith("eval ") or next.startswith("evaluate "):
                term = next[5:]
                if next.startswith("evaluate "):
                    term = term[4:]
                result = agent.eval(term, get_modname())
                print "->", value_str(result)
            elif next.startswith("run "):
                term = next[4:]
                print "synchronously running command"
                ext = agent.run(term, get_modname())
                ext.thread_event.wait()
                if ext.result is SUCCESS:
                    print "SUCCEEDED"
                else:
                    print "FAILED", ext.result
            elif next.startswith("addfact "):
                print "adding fact to KB"
                agent.run("[conclude: " + next[7:] + "]", get_modname())
            elif next.startswith("removefact "):
                print "adding fact to KB"
                agent.run("[retract: " + next[10:] + "]", get_modname())
            elif next.startswith("unload "): # drop module
                modname = next[6:].strip()
                agent.unload_modpath(Symbol(modname))
            elif next.startswith("["):
                print "running command"
                agent.run(next, get_modname())
            else:
                print "ignoring unrecognized request:", next
    except AnyException:
        errid = NEWPM.displayError()
    return False

def _print_sym_list(agent, title, list):
    print title
    for sym in list:
        reqArgs = requiredargnames(agent, sym)
        if reqArgs is not None:
            args = ' '.join([("$"+str(x)) for x in reqArgs])
        else:
            args = ''
        restargs = restargnames(agent, sym)
        if restargs is not None:
            args = args+' rest: '+ " ".join([str(x) for x in restargs])
        print " ", sym.name, args
    
def print_version():
    print "SPARK Interpreter Version %s"%VERSION

def print_help():
    print """Usage:
     help                print these directions
     module <mod_name>   change default module to <mod_name>
     unload <mod_name>   unload the declaration of module <mod_name>
     trace               turn tracing on
     notrace             turn tracing off
     step                turn stepping on
     monitor <text>      step/trace on events that contain <text>
     ignore <text>       ignore step/trace events that match <text>
     clear filters       remove trace filters (monitor/ignore)
     clear all           remove all new facts and intentions
     debug [<n>]         drop into the python debugger (looking at exception n)
     <empty input>       execute the next step if in stepping mode
     nostep              turn stepping off

     get intentions      prints ID #s of all current intentions
     get functions       see listing of the local functions
     get predicates      see listing of the local predicates 
     get tasks           see listing of the local tasks
     
     get all functions   see listing of all known functions
     get all predicates  see listing of all known predicates
     get all tasks       see listing of all known actions

     test <expr>         print solutions for predicate expression
     eval <expr>         evaluate expression
     addfact <expr>      add predicate expression <expr> to KB
     removefact <expr>   remove predicate expression <expr> from KB
     persist             persist SPARK agent knowledge base
     <spark_command>     run <spark_command>

     exit                   leave SPARK interpreter
"""
