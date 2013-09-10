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
import sys
import re
import string
import types
import __builtin__ 
from pdb import pm

import spark.internal.version
#from spark.internal.version import *

__all__ = ['pm']

def _show(x, display=str):
    def dis(thing, display=display):
        try:
            dstring = display(thing)
            if len(dstring) > 70:
                dstring = dstring[:67]+"..."
        except:
            dstring = "<exception when trying to display>"
        return dstring
    try:
        print 'SHOW:', str(x)
    except:
        print 'SHOW: <str() failed>'
    try:
        print '__repr__() =', repr(x)
    except:
        print '__repr__() <failed>'
    print "type=", type(x)
    try:
        dict = getattr(x, '__dict__', {})
    except AttributeError:
        dict = {}
    dict_keys = dict.keys()             # components in x.__dict__
    dirx = dir(x)                       # components found via dir(x)
    dict_used = []                      # in dirx and dict_keys
    unset = []                    # in dirx, not in dict_keys, not set
    callables = []               # in dirx, not in dict_keys, callable
    other = []               # in dirx, not in dict_keys, not callable
    for k in dirx:
        if k in ('__slots__', '__dict__', '__weakref__'):
            pass
        elif k in dict_keys:
            dict_used.append(k)
        elif not hasattr(x,k):
            unset.append(k)
        elif callable(getattr(x,k)):
            callables.append(k)
        else:
            other.append(k)
    other.sort()
    #callables.sort()
    #print "methods:", " ".join(callables)
    for k in other:
        print " F", k, '=', dis(getattr(x,k))
    unset.sort()
    for k in unset:
        print " U", k
    dict_keys.sort()
    for k in dict_keys:
        if k in dict_used:              # in dirx and dict_keys
            print " D", k, "=", dis(dict[k])
        else:                           # in dict_keys but not dirx
            print " D*", k, "=", dis(dict[k])
    #('__class__','__doc__','__name__','__self__','__file__','__module__','__bases__')
    
class _ShortcutFunction:
    def __init__(self, fn, doc):
        self.__fn = fn
        self._doc = doc
    def __call__(self, arg):
        return self.__fn(arg)
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError, name
        return self.__fn(name)
    def __repr__(self):
        return self._doc
    
def _apropos(x):
    result=[]
    for modname,mod in sys.modules.items():
        for sym in dir(mod):
            if string.find(sym,x) >= 0:
                print sym, "(", modname, ") =", `getattr(mod,sym)`

def _G(x):
    results=[]
    for modname,mod in sys.modules.items():
        if mod is not None and mod.__dict__.has_key(x):
            val = mod.__dict__[x]
            if val not in results:
                results.append(val)
    if len(results) == 1:
        return results[0]
    elif len(results) > 1:
        raise Exception("Ambiguous value for %s- %s"%(x,results))
    else:
        raise Exception("No value for %s"%x)


def _M(modname):
    modname = re.sub('__', '.', modname)
    __import__(modname)
    module = sys.modules[modname]
    #reload(module)
    return module

def _MM(modname):
    spark.internal.version._drop_modules()
    return _M(modname)

class _V:
    """Instances are used as global variables accessible from anywhere"""
    def __init__(self):
        pass
    def __call__(self):
        items = self.__dict__.items()
        sort(items)
        for k_v in items:
            print "%s=%s"%k_v
        return self.__dict__

## Warning - this is pretty dark magic - adding M, MM, APROPOS, and
## SHOW to builtins
__builtin__.__dict__.update( { \
    'M':_ShortcutFunction(_M, '<M>'), \
    'MM':_ShortcutFunction(_MM, '<MM>'), \
    'G':_ShortcutFunction(_G, '<G>'), \
    'V':_V(), \
    'APROPOS':_ShortcutFunction(_apropos, '<APROPOS>'), \
    'SHOW':_show \
    } )
