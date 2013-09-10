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
#* "$Revision:: 408                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

import sys
import traceback
import os

from spark.internal.version import VERSION
from spark.internal.standard import *
from spark.internal.init import init_spark
from spark.internal.exception import SPARKException, LocatedError

from spark.internal.engine.agent import Agent, TestTestExpr, IntentionStructure

from spark.internal.parse.basicvalues import Symbol
from spark.internal.parse.processing import set_default_module, get_default_module

from spark.pylang.implementation import PredImpInt, ActImpInt, FunImpInt

#have to expose methods in these modules to SparkDebugEngine.java
from spark.internal.debug.debugger import *
from spark.internal.debug.interpreter import process_command
from spark.internal.debug.tracejava import *
from spark.internal.debug.trace import get_trace_filters

from threading import currentThread

#
# Java Imports
#

from com.sri.ai.spark.debugger import SparkDebuggerPyCallback
from com.sri.ai.spark.errors import TermErrorWrapper

#
# javadebugger.py
# This python file implements the API used by the Java-based
# SPARK debugger to communicate with the SPARK (python)
# interpreter.  It mostly wraps API calls in debugger to make
# parameter passing easier.
#
# NOTE: this particular implementation assumes a single SPARK agent


testagent = None

def jd_process_command(next):
    """process console input command, return True if exit command received"""
    return process_command(testagent, next)
    
def jd_get_task_descriptor_string(task):
    from spark.internal.repr.task_py_aux import task_py
    return "%s"%task_py(testagent, task)

def jd_load_module(modulename):
    load_module(testagent, modulename)
    
def jd_get_intention_structure():
    return testagent._intention_structure
    
def jd_get_tframes():
    return testagent.get_intentions()

def jd_get_local_predicates():
    return [s.name for s in get_local_predicates(testagent)]

def jd_get_local_functions():
    return [s.name for s in get_local_functions(testagent)]
    
def jd_get_local_tasks():
    return [s.name for s in get_local_tasks(testagent)]

def jd_get_all_predicates():
    return [s.name for s in get_all_predicates(testagent)]

def jd_get_all_functions():
    return [s.name for s in get_all_functions(testagent)]
    
def jd_get_all_tasks():
    return [s.name for s in get_all_tasks(testagent)]

def jd_test(to_test, **varvalues):
    from java.lang import String
    from java.util import ArrayList
    try:
        test = TestTestExpr(to_test, Symbol(get_modname()), varvalues)
        testagent.add_test(test)
        result = test.wait_result(1)     # should not wait too long
        if (result is None): raise AssertionError
        sols = ArrayList()
        for sol in test.result:
            solList = ArrayList()
            for val in sol:
                solList.add(String(value_str(val)))
            sols.add(solList)
        varids = ArrayList()
        for varid in test.outvarids:
            varids.add(String(varid))
        res = ArrayList()
        res.add(varids)
        res.add(sols)
        return res
    except LocatedError, err:
        return err
    
def jd_eval(to_eval):
    try: 
        #we're inconsistent here: test() returns a TestTestExpr, eval just runs the internal agent eval
        return testagent.eval(to_eval, get_modname())
    except LocatedError, err:
        return err
        
def jd_execute(to_exec):
    try:
        testagent.run(to_exec, get_modname())
        return None
    except LocatedError, err:
        return err
 
def jd_clear_all():
    clear_all(testagent)

def jd_get_agent():
    return testagent
    
def jd_new_agent():
    global testagent
    testagent = new_agent(testagent, jd_step_init, jd_trace)

def jd_execute_spark_main(module_args=[]):
	execute_spark_main(testagent, module_args)
	
def jd_stop_debugger():
    dispose(testagent)

def jd_start_debugger(defaultModule, initParams=None):
    print ""
    print "Welcome to the Java debugger for SPARK v%s"%VERSION
    print ""
    if initParams is None:
        initParams = {}
        initParams['persist']=False
        initParams['resume']=False
    else:
        if initParams.get('unbuffered') is not None:
            from spark.main import nobuffer
            sys.stdout=nobuffer(sys.stdout)
            print "Output is unbuffered"
            del initParams['unbuffered']
        elif initParams.get('python') is not None:
            import code
            code.interact()
            del initParams['python']
        elif initParams.get('coverage'):
            import coverage
            coverage.start()
            del initParams['coverage']
            
        p = {}
        keys = initParams.keys()
        for key in keys:
            p[key] = initParams.get(key)
        initParams = p
        
    try:
        init_spark(**initParams)
        jd_new_agent()
        print "test agent initialized"
        load_module(testagent, defaultModule)
        return None
    except LocatedError, err:
        return TermErrorWrapper(err)
    except AnyException:
        import traceback
        traceback.print_exc()
        raise
