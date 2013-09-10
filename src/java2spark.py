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
#* "$Revision:: 155                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/java#$" *#
#*****************************************************************************#
import os
import sys
from spark.internal.parse.newparse import must_find_dir, SPARK_SUFFIX
from spark.internal.exception import LowError

template = '{defaction (%s $java_inst%s)\n  imp: (pyAction "+%s" (pyMod "%s" "%s"))}'

def print_usage():
    print """Usage:
\tjava2spark [-options] [Java classname]
Options:
\t-module <module>\tWrite the SPARK-L code to <module>.spark (req'd)
\t-prefix <prefix>\tUse the <prefix> on all action names

Use of the -prefix is highly recommended, as many Java classes have
similar method names. For example, for the ArrayList class you may
wish to use a prefix like 'AL_' so that ArrayList.size() will be the
SPARK action (AL_size).
"""
    
def main(*argv):
    try:
        #need void for type checking
        from java.lang import Void
    except ImportError:
        print "ERROR: cannot import Java classes. java2spark must be run within Jython with the appropriate classpath"
        return -2
    
    if len(argv) <= 1:
        print_usage()
        return -1

    prefix = ''
    class_name = None
    spark_module = None
    i = 1
    while i<len(argv):
        opt = argv[i]
        i = i+1
        if opt == "-prefix":
            if i == len(sys.argv):
                print "Prefix argument is missing"
                return -1
            prefix = argv[i]
            i = i+1
        elif opt == "-module":
            if i == len(sys.argv):
                print "SPARK module argument is missing"
                return -1
            spark_module = argv[i]
            i = i+1
        else:
            if i != len(sys.argv):
                print "Invalid option:", opt
                return -1
            class_name = opt

    if class_name is None:
        print "Please specify a Java classname"
        return -1
    if spark_module is None:
        print "Please specify a SPARK module name using -module <module>"
        return -1

    #Prepare the Java class, make sure it loads
    try:
        __import__(class_name)
        clazz = sys.modules[class_name]
    except ImportError:
        print "ERROR: cannot import %s, please make sure that it is on your classpath. You may have to edit java2spark[.bat]"%class_name
        return -3
    
    meths = clazz.methods

    #Prepare the outputfile
    filename = ''
    try:
        pathbase = must_find_dir(spark_module)
        name = spark_module[spark_module.rfind('.')+1:] + SPARK_SUFFIX
        filename = os.path.expanduser(os.path.join(pathbase, name))
    except LowError, e:
        print "ERROR: cannot determine where to store %s. Directory for module must exist.\n%s"%(spark_module, e)
        return -4

    f = open(filename, 'w')
    f.write('#java2spark auto-generated file\n\n')

    #cache an array of just the method names for making unique symbol names
    meth_names = [m.name for m in meths]

    import StringIO
    buff = StringIO.StringIO()
    f.write('export:')

    #we will be writing export symbols to f and writing the declarations
    #to the stringio buffer
    for m in meths:
        print "EXAMINING: %s"%m
        
        c = 'a'

        #check for methods with the same name, and if so, rename the
        #current action to make it have a unique symbol name
        overrides = [x for x in meths if x.name == m.name]
        name = m.name
        if len(overrides) > 1:
            name = unique_name(m.name + str(overrides.index(m)), meth_names)
            
        #Filter out JavaBean properties, we just want actions
        if m.name[:3] == "set" or m.name[:3] == "get":
            if len(m.name) > 3:
                c = m.name[3]
        elif m.name[:2] == "is":
            if len(m.name) > 2:
                c = m.name[2]
        #DISABLING BEAN FILTERING
        if False and c <= 'Z' and c >= 'A':
            #print "BEAN: ", m, c
            continue

        #template(action, args, sig, class, meth)
        pTypes = m.parameterTypes
        sig = ''.join(['+' for t in pTypes])
        if m.returnType is not Void.TYPE:
            sig = sig+'-'

        #create args
        # - use arguments that denote the type, e.g. $arg_java_util_ArrayList
        argTypeStrs = [("$arg_%s"%type_repr(t)).replace('.','_') for t in pTypes]
        # - append argument number to the argument names to make unique
        args = " ".join(["%s%s"%(argTypeStrs[r], r) for r in range(len(pTypes))])
        # - add leading space if there are arguments        
        if len(args) > 0:
            args = " " + args
        # - add in output parameter if necessary
        if m.returnType is not Void.TYPE:
            args = args + " $retVal_%s"%(type_repr(m.returnType).replace('.','_'))

        #don't use m.name. have to use unique 'name'
        decl = template%(prefix+name, args, sig, class_name, m.name)
        #print symbol name to export: line
        f.write(' '+prefix+name)
        #print decl to buffer
        buff.write(decl+'\n\n')

    f.write('\n\n')
    f.write(buff.getvalue())
    f.close()
    print "Output stored in", filename
    return 0

def unique_name(base, meth_names):
    if base not in meth_names:
        return base
    base = base + '_'
    #shouldn't have anywhere near 2048 tries, just want a large number
    for i in range(0, 2048):
        if base+str(i) not in meth_names:
            return base+str(i)
    raise RuntimeException("cannot make unique symbol name for ", base[:-1])

def class_name_only(n):
    idx = n.rfind('.')
    if idx:
        return n[idx+1:]
    else:
        return n
    
def type_repr(t):
    if t.isArray():
        return "array_"+class_name_only(t.componentType.name)
    return class_name_only(t.name)

if __name__ == "__main__":
    exitcode = main(*sys.argv)
    if exitcode is not 0:
        sys.exit(exitcode)
