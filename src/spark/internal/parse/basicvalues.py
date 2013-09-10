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
#* "$Revision:: 197                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.version import *
import types
import re
import threading
from spark.internal.common import NEWPM, DEBUG, ABSTRACT
from spark.internal.exception import LowError
from spark.internal.parse.usagefuns import termEvalErr
from spark.pylang.implementation import Imp, PersistablePredImpInt

debug = DEBUG(__name__)

from spark.internal.parse.set_methods import set_methods
from spark.internal.parse.value import Value

################################################################
# Variable, Symbol, Structure

from spark.internal.parse.values import \
     Symbol, isSymbol, Variable, isVariable, \
     Structure, isStructure, \
     value_str, append_value_str, inverse_eval, \
     VALUE_CONSTRUCTOR

from spark.internal.parse.values_common import \
     List, isList, createList, EMPTY_SPARK_LIST, \
     Boolean, isBoolean, \
     String, isString, \
     Integer, isInteger, Float, isFloat, isNumber
     
################################################################
# Prefix operator symbols
PREFIX_PLUS_SYMBOL = Symbol("+#")
PREFIX_MINUS_SYMBOL = Symbol("-#")
BACKQUOTE_SYMBOL = Symbol("`#")
PREFIX_COMMA_SYMBOL = Symbol(",#")

################################################################
# Defines SPARK basic data types and how to construct/print them

def convertToSparkValueIfNecessary(x):
    "If x is a standard, persistable SPARK value, return None, otherwise, return  the closest similar SPARK value."
    # Check if we have a List
    if isList(x):
        result = None
        for i in range(len(x)):
            new = convertToSparkValueIfNecessary(x[i])
            if new is not None:
                if result is None:
                    result = list(x)
                result[i] = new
        if result is None:
            return None
        else:
            return List(result)
    # Check for an ordinary SPARK value - assume it is persistable
    # i.e., it doesn't have any non-SPARK values nested within it
    if isString(x) or isStructure(x) or isSymbol(x) or isInteger(x) \
           or isFloat(x):
        return None
    # Check if you can coerce it to a list
    try:
        listEquivalent = List(x)
    except TypeError:
        print "WARNING - Cannot coerce to a SPARK value: %r"%(x,)
        return None
    return coerceToSparkValue(listEquivalent)

def coerceToSparkValue(x):
    new = convertToSparkValueIfNecessary(x)
    if new is None:
        return x
    else:
        return new


################
# Unique ID numbers


NEXT_OBJECT_ID_NUM = 1
ID_NUM_LOCK = threading.Lock()

OBJECT_ID_LOG = []
def getNewIdNum():
    global NEXT_OBJECT_ID_NUM
    try:
        ID_NUM_LOCK.acquire()
        id_num = NEXT_OBJECT_ID_NUM
        NEXT_OBJECT_ID_NUM = id_num + 1
    finally:
        ID_NUM_LOCK.release()
    return id_num

def deallocateIdNum(idnum):
    global NEXT_OBJECT_ID_NUM
    try:
        ID_NUM_LOCK.acquire()
        if idnum + 1 == NEXT_OBJECT_ID_NUM: # just allocated
            NEXT_OBJECT_ID_NUM = idnum
            return True
        else:
            return False
    finally:
        ID_NUM_LOCK.release()

################################################################

# TODO: the record of what id numbers you need to keep should be agent specific

class StandardIdSave(object):
    """When the use of the object is to be saved, record it in idNumObject"""
    __slots__ = (
        "_idNumObject",        # map id_num to object if object is used
        "_resume_id_map",                # map old id to new id
        )

    def __init__(self):
        self._idNumObject = {}
        self._resume_id_map = None
    
    def set_resuming(self, isResumingBoolean):
        if isResumingBoolean:
            self._resume_id_map = {}
        else:
            self._resume_id_map = None
            
    def is_resuming(self):
        return self._resume_id_map != None

    def recordIdUsed(self, idnum, obj):
        """Called when object is used"""
        recordedObj = self._idNumObject.get(idnum, None)
        if recordedObj is None:
            self._idNumObject[idnum] = obj
        else:
            if not (recordedObj is obj): raise AssertionError, \
               "Duplicate entry for id %s in object table"%idnum
    def constructIdObject(self, ignore_agent, id_num, *constructor_info):
        if not (self.is_resuming()): raise AssertionError, \
           "constructIdObject is being called while not resuming"
        #val = self._idNumObject.get(id_num, None)
        val = self._resume_id_map.get(id_num, None)
        if not (val is None): raise AssertionError, \
               "Trying to construct an object that already exists: %d" % id_num
        if not (constructor_info): raise AssertionError, \
           "No constructor info given for %d"%id_num
        constructor_name = constructor_info[0]
        cl = CONSTRUCTOR_NAME_CLASS.get(constructor_name, None)
        if not (cl): raise AssertionError, \
           "The constructor %s is not registered"%constructor_name
        args = constructor_info[1:]
        mode = cl.constructor_mode
        if (len(args) != len(mode)): raise AssertionError, \
               "Expecting %d parameters for %s"%(len(mode), constructor_name)
        # print "RESTORING",
        val = cl(*args)
        #val.setObjectId(id_num)
        self._resume_id_map[id_num] = val
        #print "Setting self._resume_id_map[%d]->%d"%(id_num, val.objectId())
        return val

    def idGetObject(self, ignore_agent, id_num):
        if self.is_resuming():
            if id_num == 8809:
                print "DEBUG INFO FOR 8809"
                print self._resume_id_map.has_key(id_num), self._resume_id_map[id_num], self._resume_id_map.get(id_num, None)
            return self._resume_id_map.get(id_num, None)
            #if (real_id_num == None): raise AssertionError, \
            #    "Cannot map id_num %d when resuming"%id_num
        else:
            return self._idNumObject.get(id_num, None)

STANDARD_ID_SAVE = StandardIdSave()

_ID_SAVE = STANDARD_ID_SAVE

def set_id_save(id_save_obj):
    global _ID_SAVE
    ID_NUM_LOCK.acquire()
    old_id_save = _ID_SAVE
    _ID_SAVE = id_save_obj
    ID_NUM_LOCK.release()
    return old_id_save
    
class PersistIdSave(object):
    __slots__ = (
        "_info", # dict mapping idnum to object
        "_existsIEFacts", # list of ObjectExists facts for recorded objects
        "_stateIEFacts", # list of ObjectState facts for recorded objects
        )

    def __init__(self):
        self._info = {}
        self._existsIEFacts = []
        self._stateIEFacts = []
        
    def clear(self):
        self._info.clear()
        del self._existsIEFacts[:]
        del self._stateIEFacts[:]
        
    def recordedObjects(self):
        return self._info.values()        

    def recordIdUsed(self, id, obj):
        """Called when object is used"""
        if not self._info.has_key(id):
            # make sure that we don't loop when getting state info
            self._info[id] = None
            # get exists and state info
            # this will call recordIdUsed for anything obj references
            cl_name = obj.__class__.__name__
            if not (CONSTRUCTOR_NAME_CLASS.has_key(cl_name)):
                print "ERROR: No constructor has been installed for %s"%cl_name
            try:
                existIEArgs = [inverse_eval(x) for x in obj.constructor_args()]
                existIEArgs.insert(0, cl_name)
                self._existsIEFacts.append((id, List(existIEArgs)))
            except:
                errid = NEWPM.displayError()
                print
                print "ERROR finding constructor_args() for instance %d of %s" \
                      % (id, cl_name)
                print
            try:
                state_args = obj.state_args()
                if state_args:
                    stateIEArgs = [inverse_eval(x) for x in state_args]
                    self._stateIEFacts.append((id, List(stateIEArgs)))
            except:
                errid = NEWPM.displayError()
                print
                print "ERROR finding state_args() for instance %d of %s" \
                      % (id, cl_name)
                print
            self._info[id] = obj
            
    def existsIEFacts(self):
        """Return a set of facts for ObjectExists"""
        iefacts = self._existsIEFacts
        #iefacts.sort()
        #TODO: cleanup (CALOYRIV-284)
        d = {}
        for iefact in iefacts:
            d[iefact[0]] = iefact
        keys = list(d.keys())
        keys.sort()
        newiefacts = [d[k] for k in keys]
        return newiefacts
        #return iefacts

    def stateIEFacts(self):
        """Return a set of facts for ObjectState"""
        iefacts = self._stateIEFacts
        iefacts.sort()
        return iefacts

    def nextIdIEFacts(self):
        """Return a set of facts for ObjectNextId"""
        return [[NEXT_OBJECT_ID_NUM]] 


PERSIST_ID_SAVE = PersistIdSave()
        

CONSTRUCTOR_NAME_CLASS = {}  # map name to class

def objectId(obj):
    if not (isinstance(obj, ConstructibleValue)): raise AssertionError, \
           "Cannot get id of anything other than a constructible value"
    return obj.objectId()

SYM_idObject = Symbol("idObject")
def idObject(agent, idnum):
    val = _ID_SAVE.idGetObject(agent, idnum)
    if val is None:
        raise LowError("No record of object %d", idnum)
    return val

def get_object_id(agent, obj, idnum):
    if obj == None:
        if idnum == None:
            raise LowError("At least one argument needs to be bound")
        else:
            return (idObject(agent, idnum), idnum)
    else:
        if idnum == None:
            return (obj, objectId(obj))
        else:
            return objectId(obj) == idnum
        
            

def installConstructor(cv_class):
    if hasattr(cv_class, "__init__") \
           and not hasattr(cv_class, "constructor_mode"):
        raise LowError("Class %s has no constructor_mode attribute"%cv_class.__name__)
    CONSTRUCTOR_NAME_CLASS[cv_class.__name__] = cv_class

class ObjectExists(Imp, PersistablePredImpInt):
    __slots__ = (
        )

    #def retractall(self, agent, bindings, zexpr):
    #def find_solutions(self, agent, bindings, zexpr):
    #def conclude(self, agent, bindings, zexpr, kbResume=False):

    #PERSIST
    def persist_arity_or_facts(self, agent):
        # The ObjectExists facts are handled separately
        return ()
    
    def resume_conclude(self, agent, bindings, zexpr):
        if (len(zexpr) != 2): raise AssertionError
        num = termEvalErr(agent, bindings, zexpr[0])
        args = termEvalErr(agent, bindings, zexpr[1])
        try:
            _ID_SAVE.constructIdObject(agent, num, *args)
        except:
            errid = NEWPM.displayError()
            raise LowError("Error recreating object %s %s [%s]"%(num, value_str(args), errid))

class ObjectNextId(Imp, PersistablePredImpInt):
    __slots__ = (
        )

    #def retractall(self, agent, bindings, zexpr):
    #def find_solutions(self, agent, bindings, zexpr):
    #def conclude(self, agent, bindings, zexpr, kbResume=False):

    #PERSIST
    def persist_arity_or_facts(self, ignore_agent):
        # The ObjectNextId facts are handled separately
        return ()
        #return [[NEXT_OBJECT_ID_NUM]]
    
    def resume_conclude(self, agent, bindings, zexpr):
        global NEXT_OBJECT_ID_NUM
        newnum = termEvalErr(agent, bindings, zexpr[0])
        if STANDARD_ID_SAVE.is_resuming():
            print "NOTE: OBJECT ID NUMBERS WILL CHANGE ON RESUMING"
            #print "CHANGING NEXT_OBJECT_ID_NUM %d->%d"%(NEXT_OBJECT_ID_NUM,newnum)
        NEXT_OBJECT_ID_NUM = newnum

class ObjectState(Imp, PersistablePredImpInt):
    __slots__ = (
        )

    #def retractall(self, agent, bindings, zexpr):
    #def find_solutions(self, agent, bindings, zexpr):
    #def conclude(self, agent, bindings, zexpr, kbResume=False):

    #PERSIST
    def persist_arity_or_facts(self, agent):
        # The ObjectState facts are handled separately
        return ()
    
    def resume_conclude(self, agent, bindings, zexpr):
        if (len(zexpr) != 2): raise AssertionError
        num = termEvalErr(agent, bindings, zexpr[0])
        args = termEvalErr(agent, bindings, zexpr[1])
        obj = _ID_SAVE.idGetObject(agent, num)
        if obj is None:
            raise LowError("Cannot find object with id %s"%num)
        obj.set_state(agent, *args)


################################################################ A
# ConstructibleValue is an object with identity and state that can be
# saved and resumed from a persisted state.

# To create a subclass of this class:

# Define constructor_args() to return a Python List of arguments that
# will be supplied to the __init__() method when the object is
# reconstructed on a resume.  These values should be
# ConstructibleValues or core SPARK values (i.e., something we can
# persist).  This may require tweaking the __init__ method a bit (for
# example the "!" modes in spark.io.file.FileWrapper).

# Define a state_args() method to return a Python tuple of values
# describing the state.  Again, these values should be
# ConstructibleValues or core SPARK values.

# Define a set_state() method taking an agent and an additional
# parameter for each element of the tuple returned above, that sets
# the state of the object.

# You also have to set a class variable constructor_mode to a string
# that has as many characters as there are arguments in the __init__()
# method.  The contents used to have meaning, now only the length is
# used.

# You can also set a class variable cvcategory to a short string to be
# used when displaying the object (and not using persistence)

# After defining the class, call installConstructor(<the class>)

class ConstructibleValue(Value):
    __stateslots__ = (
        "_idnum",
        )
    __slots__ = __stateslots__ + (
        "__weakref__",
        )

    cvcategory = "CV"
    def cvname(self):
        return None

    def __init__(self):
        Value.__init__(self)
        self._idnum = getNewIdNum()
        # print "Creating", self._idnum, type(self)
        
    def constructor_args(self):
        "Return a list of values that are used as arguments to constructor"
        return []

    def state_args(self):
        "Return a tuple of values that are used as arguments to set_state"
        return ()

    def set_state(self, agent, *args):
        raise Exception("set_state has not been defined for " \
                        % self.__class__.__name__)

    def objectId(self):
        """Get the id of the object, with no need to record it"""
        return self._idnum

    def objectIdSave(self):
        """Get the id of the object, but ensure we have a record of it"""
        idnum = self._idnum
        _ID_SAVE.recordIdUsed(idnum, self)
        return idnum

    def setObjectId(self, idnum):
        """Change the id to idnum, potentially allow reuse of the old id"""
        oldnum = self._idnum
        deallocateIdNum(oldnum)
        self._idnum = idnum
        
    def append_value_str(self, buf):
        idnum = self.objectIdSave()
        #NEWPM.recordLocation("Calling value_str")
        from spark.internal.init import is_persist_state
        if is_persist_state():
            return buf.append(",(idObject %d)" % idnum)
        return buf.append("<%s:%s:%d>" % (self.cvcategory, \
                               (self.cvname() or self.__class__.__name__), \
                               idnum))

    def inverse_eval(self):
        idnum = self.objectIdSave()
        return SYM_idObject.structure(idnum)

################################################################
# Failures

from spark.internal.exception import Failure, deconstructFailure

def failure_append_value_str(failure, buf):
    buf.append(",")
    append_value_str(failure_inverse_eval(failure), buf)
    return buf

def failure_inverse_eval(failure):
    return Structure(Symbol("failure"), [inverse_eval(x) for x in deconstructFailure(failure)])

set_methods(Failure, append_value_str=failure_append_value_str, inverse_eval=failure_inverse_eval)


###############################################################
