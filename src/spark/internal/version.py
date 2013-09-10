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
#* "$Revision:: 147                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
# Add builtin names that don't appear in Python 2.1

import types
import sys

__all__ = ['MARK_THIS_MODULE_TO_DROP', 'AnyException', 'isJython', 'isPython']

VERSION = "1.0.0-JBALINT"

isJython = False
isPython = False

try:
    #test Java imports to see if we are inside of Java
    import java.util.ArrayList
    isJython = True
except ImportError:
    isPython = True

# In Jython, java.lang.
try:
    from java.lang import Exception as _JavaException
    AnyException = (Exception, _JavaException)
except ImportError:
    AnyException = Exception

try:
    bool
except Exception:
    True = 1
    False = 0
    def bool(x):
        if x:                           # interpret x as boolean
            return True
        else:
            return False
    def dict(x=None):
        if x is None:
            return {}
        if isinstance(x, types.DictType):
            return x.copy()
        else:
            d = {}
            for elt in x:
                d[elt[0]] = elt[1]
            return d
    # This overrides <java function object> in Jython 2.2a0
    class object:
        pass
    __all__ = __all__ + ['object', 'True', 'False', 'bool', 'dict']

# Test for jython22a0 WeakValueDictionary bug
try:
    import weakref
    weakref.WeakValueDictionary()[None]=lambda x: x
except TypeError:
    # Horrendous hack
    print "Using workaround for WeakValueDictionary bug"
    weakref.WeakValueDictionary = dict
del weakref
try:
    import weakref
    weakref.WeakKeyDictionary()
except TypeError:
    # Horrendous hack
    weakref.WeakKeyDictionary = dict
del weakref

# Test for pickling bug
import cPickle
try:
    cPickle.dumps(int, -1)
except:
    print """
    ################################################################
    # WARNING - You are using an old version of jython.jar
    # When using persistence you will get an error:
    # TypeError: descriptor '__reduce__' of 'object' object needs an argument
    # An up-to-date version exists in CVS as lib/jython.jar
    ################################################################"""

# Test for str subclass bug in pre 2.2beta1 versions of jython
if isJython:
    try:
        class _S(str):
            pass
        bool(_S("a"))
    except:                                 # stack overflow
        print "YOUR JYTHON INSTALLATION IS OUT OF DATE AND CONTAINS A STRING SUBCLASSING BUG"
        print "CVS USERS: AN UP-TO-DATE JYTHON IS AVAILABLE IN lib/spark_jython.zip"
        print "PLEASE UPDATE THIS FILE OR CONTACT spark-support@ai.sri.com"
        #import sys
        #sys.exit(2)
    del _S
    
# # Pickling of Sets doesn't work under jython
# # Use same workaround in Jython and CPython
# import sets, copy_reg
# copy_reg.pickle(sets.Set, lambda self: (sets.Set, (tuple(self),)))
# copy_reg.pickle(sets.ImmutableSet, lambda self: (sets.ImmutableSet, (tuple(self),)))
# del copy_reg


MARK_THIS_MODULE_TO_DROP = None

def _drop_modules():
    """Delete all modules that have imported DROP__MARKER from this module, either as DROP__MARKER__ or _DROP__MARKER__."""
    for (mname, m) in sys.modules.items():
        if m and m.__dict__.has_key('MARK_THIS_MODULE_TO_DROP') and \
               hasattr(m, '__file__'):  # don't delete builtins like __main__
            print "Deleting Python module:", m.__name__
            del sys.modules[mname]
