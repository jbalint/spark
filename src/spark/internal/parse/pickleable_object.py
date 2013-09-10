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
"""
This is a hack to work around problems with Jython pickling new-style classs.
Jython 2.2b1 raises an exception when:
(1) trying to pickle a new-style class or a function
(2) trying to unpickle something whose __reduce__ method returned a state as a third element
"""
import copy_reg
import sys
from spark.internal.common import NEWPM
USE_CPICKLE = True
if USE_CPICKLE:
    import cPickle as common_pickle
else:
    import pickle as common_pickle

class PickleableObject(object):
    """An object which can be pickled easily

    The __stateslots__ for a PickleableObject subclass MyClass is a
    subset of __slots__ list of slots. The __stateslots__ indicates
    the slots whose values should be recorded when pickling the
    object. A common idiom is:

    __stateslots__ = (...)
    __slots__ = __stateslots__ + (...)

    When unpickling an object of class MyClass, the MyClass.__new__
    method is called, bypassing the MyClass.__init__ method, and the
    slots specified by the __stateslots__ of MyClass and its parent
    classes are set using the persisted values. Finally the
    MyClass.__restore__ method is called in the new instance.
    """
    __slots__ = ()
    __stateslots__ = ()
    def __reduce__(self):
        slots = getClassStateSlots(self.__class__)
        statevalues = [getattr(self, slot, None) for slot in slots]
        return (_constructObject1, tuple(statevalues))

    def __restore__(self):
        pass

# Map from class to list of slots to be saved as state
_CLASS_STATE_SLOTS = {PickleableObject:("__class__",)}

def getClassStateSlots(cls):
    slots = _CLASS_STATE_SLOTS.get(cls)
    if slots is None:
        parentCls = cls.__bases__[0]
        parentSlots = getClassStateSlots(parentCls)
        if cls.__stateslots__ == parentCls.__stateslots__:
            slots = parentSlots
        else:
            slots = parentSlots + cls.__stateslots__
        _CLASS_STATE_SLOTS[cls] = slots
    return slots

def _constructObject1(*statevalues):
    #print "EXTRACTING %s, args are %s"%(name, str(args))
    for (i,value) in enumerate(statevalues):
        if i == 0:
            new = value.__new__(value)
            stateslots = getClassStateSlots(value)
        else:
            setattr(new, stateslots[i], value)
    new.__restore__()
    return new

copy_reg.constructor(_constructObject1)
# def _constructObject(cls, *args):
#     #print "EXTRACTING %s, args are %s"%(name, str(args))
#     new = cls.__new__(cls)
#     new.__setstate__(args)
#     return new

# copy_reg.constructor(_constructObject)
