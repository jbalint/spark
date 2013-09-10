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
#* "$Revision:: 129                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.version import *
import sys
import os
import types

from spark.pylang.implementation import PersistablePredImpInt
from spark.internal.debug.debugger import get_all_predicates
from spark.internal.source_locator import get_dir_locator, SPARK_SUFFIX
from spark.internal.exception import LowError, Failure
from spark.internal.parse.basicvalues import inverse_eval, value_str

#
# Convert internal knowledge base facts into SPARK-L text representations
# for saving to .spark files.
#
# author conley
#

def save_predicates(agent, modname, predicates):
    predimpls = []
    #dict{modname->list[predicate ids]}
    imports = {}
                   
    filename = ''
    try:
        pathbase = get_dir_locator()(modname)
        name = modname[modname.rfind('.')+1:] + SPARK_SUFFIX
        filename = os.path.expanduser(os.path.join(pathbase, name))
    except AnyException, e:
        #XXX: NEED A BETTER EXCEPTION CLASS HERE
        raise Exception("ERROR: cannot determine where to store %s. Directory for module must exist.\n%s"%(modname, e))
    
    #collect list of applicable predicates (must be basepreds) and imports
    for pred in predicates:
        impl = agent.getImp(pred)
        if impl is None:
            continue

        if isinstance(impl, PersistablePredImpInt):
            predimpls.append(impl)
            if imports.has_key(pred.modname):
                list = imports[pred.modname]
            else:
                list = []
            imports[pred.modname] = list
            list.append(pred.id)
        else:
            #XXX: suppress
            #print "Save predicates currently only supports basic fact-based predicates, information for %s will not be saved"%pred
            pass

    output = open(filename, 'w')

    #print imports
    for module in imports.keys():
        list = imports[module]
        ids = " ".join([id for id in list])
        output.write("importfrom: %s %s\n"%(module, ids))
        #print "importfrom: %s%s"%(module, ids)
        
    output.write('\n\n#This is a SPARK-generated dump of facts in the SPARK knowledge base.\n#It is highly recommended that you do NOT modify this file\n#as it may be automatically overwritten.\n')
    
    #print predicate definitions
    #NOTE: this doesn't not use the (obsolete) write_persist_repr() method in the
    #PersistablePredImpInt impl as we want something more akin to a spark-l repr
    for impl in predimpls:
        fact_tmpl = "(%s%%s)"%impl.symbol.id
        for fact in agent.factslist0(impl.symbol):
            try:
                fstr = " " + " ".join([_strrep(f) for f in fact])
                output.write(fact_tmpl%fstr+'\n')
            except AnyException, f:
                #XXX: suppress                
                print f, ":", impl.symbol.name, "will not be saved"
    output.close()
    #all done

def _strrep(spark_data):
    term = inverse_eval(spark_data)
    if term is None:
        #XXX: NEED BETTER EXCEPTION CLASS HERE
        raise Exception("ERROR: cannot create SPARK-L representation for %s type, value is %s"%(type(spark_data), spark_data))        
    return value_str(term)
