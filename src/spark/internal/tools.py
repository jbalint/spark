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
from spark.internal.version import *
import sys
import types
from sets import Set
try:
    import gc
except ImportError, e:
    print e

currStack = None
prevStack = None
currWeakrefs = None
prevWeakrefs = None

def typecount():
    """note that the typecount() method saves two dictionaries of
    types and integers"""
    counts = {}
    objects = gc.get_objects()
    strcount = 0
    import weakref
    weakrefNames = []
    for obj in objects:
        cl = type(obj)
        if cl == weakref.ReferenceType:
            weakrefNames.append(repr(obj))
        counts[cl] = counts.get(cl, 0) + 1
    items = [ (c,t) for (t,c) in counts.items() ]
    items.sort()
    for k,v in items:
        print k, v
    global prevStack, currStack, currWeakrefs, prevWeakrefs
    prevStack = currStack
    currStack = counts
    prevWeakrefs = currWeakrefs
    currWeakrefs = weakrefNames

def leaks():
    """compute the number of leaked objects by type between the two
    last calls to typecount().
    note that the leaks() method itself increases memory
    usage as it has to save typecounts for the past two typecounts()"""
    counts = {}
    for k in currStack.keys():
        counts[k] = currStack[k]
    for k in prevStack.keys():
        if not counts.has_key(k):
            counts[k] = -1 * prevStack[k]
        else:
            counts[k] = counts[k] - prevStack[k]
    items = [ (c,t) for (t,c) in counts.items() ]
    items.sort()
    print "Approximate memory leakage between last two calls to typecount():"
    for k,v in items:
        if k != 0:
            print k, v

    wrList = currWeakrefs[:]
    for wf in prevWeakrefs:
        try:
            wrList.remove(wf)
        except:
            pass
    wrList.sort()
    for wf in wrList:
        print wf
    
    
def accessible(testfunction):
    "Construct a list of module variable values that satisfy testfunction"
    found = []
    for mod in sys.modules.values():
        if mod is not None:
            for val in mod.__dict__.values():
                if testfunction(val) and val not in found:
                    found.append(val)
    return found

def subclasses(cl):
    cl_list = accessible(lambda x, cl=cl: \
                         (isinstance(x, types.TypeType) or isinstance(x, types.ClassType)) \
                         and issubclass(x, cl))
    print cl_list
    subclasses_aux(cl, None, cl_list, 0)

def subclasses_aux(cl, parent, cl_list, level):
    other_bases = [x.__name__ for x in cl.__bases__ if x is not parent]
    if other_bases:
        print "    "*level, cl.__name__, other_bases
    else:
        print "    "*level, cl.__name__
    for sub in cl_list:
        if cl in sub.__bases__:
            subclasses_aux(sub, cl, cl_list, level + 1)

def inheritance(cl):
    print
    print "%s %s"%(cl.__name__, type(cl))
    try:
        print " __slots__ = %s"% ", ".join(cl.__slots__)
    except AttributeError:
        pass
    oldattrs = Set()
    for base in cl.__bases__:
        oldattrs.union_update(dir(base))
    newattrs = list(Set(dir(cl)).difference(oldattrs))
    newattrs.sort()
    print " dir (new) = %s"%", ".join(newattrs)
    print " __bases__ = %s"%", ".join([x.__name__ for x in cl.__bases__])
    for base in cl.__bases__:
        inheritance(base)
