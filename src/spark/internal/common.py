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
#* "$Revision:: 385                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
import string
import sys

from spark.internal.version import *
from spark.util.pyconsole import runPyDebugger

#the weakdict tables for SparkEvent and TFrame don't appear to be performing
#properly in Python, nor are they even possible w/ Java, so this
#flag will disable them. The tables are necessary for some meta-predicates
#used by sketch, so turning them off does break stuff, though it also
#prevents a gigantic memory leak.
USE_WEAKDICT_NAME_TABLES = False

# if paranoid: check correct binding status and be careful about unbinding
paranoid = True

def console(print_message, *args):
    """use to print a message to the SPARK console (don't use python print function directly)"""
    #TODO: REPLACE WITH A SETTABLE PRINT STREAM (must be compatible with Java)
    print print_message%args

def console_debug(print_message, *args):
    print "DEBUG:", print_message%args

def console_warning(print_message, *args):
    print "WARNING:", print_message%args

def console_error(print_message, *args):
    print "ERROR:", print_message%args
    
################################################################

# def delete_if_not(list, function):
#     """Destructively modify list so that it no longer contains any elements
#     for which function returns false. """
#     j = 0
#     for i in range(len(list)):
#         if function(list[i]):
#             list[j]=list[i]
#             j = j+1
#     del list[j:]

def delete_all(list, element):
    """Destructively modify list so that it no longer contains any elements
    which equal element. """
    j = 0
    for i in range(len(list)):
        if list[i] != element:
            list[j]=list[i]
            j = j+1
    del list[j:]


def delete_repetitions(list):
    """Destructively modify list so that it no longer contains
    contiguous repetitions of the same element. """
    length = len(list)
    j = 1
    if length <= 1:
        return
    previous = list[0]
    for i in range(1, length):
        if list[i] != previous:
            previous = list[i]
            list[j]=previous
            j = j+1
    del list[j:]
    

################################################################

def tuple_repr(tuple):
    return string.join(map(repr, tuple), '')

################################################################


#ALL_PMS = []

class NoStackMixin:
    pass



class ExceptionInfo(object):
    __slots__ = (
        "__weakref__",
        "_exctype",
        "_value",
        "_tb",
        "count",
        )
    def __init__(self, count):
        (self._exctype, self._value, self._tb) = sys.exc_info()
        self.count = count

    def pm(self):
#         print "START python post_mortem for %s" % (self,)
        runPyDebugger((self._exctype, self._value, self._tb))
#         import pdb
#         self.print_exception()
#         pdb.post_mortem(self._tb)
#         print "END python post_mortem for %s" % self

    def print_exception(self):
        import traceback
        traceback.print_exception(self._exctype, self._value, self._tb)

    def format_exception(self):
        import traceback
        return "".join(traceback.format_exception(self._exctype, self._value, self._tb))

    def __str__(self):
        if hasattr(self._value, "getDisplayString"):
            return "[%d] %s" % (self.count, self._value.getDisplayString())
        else:
            return "[%d] %s: %s" % (self.count, self._exctype.__name__, self._value)


class RecordedLocation(Exception):
    __slots__ = ()

class _PM(object):
    __slots__ = (
        "next_count",
        "log",
        "maxLogLength",
        )

    def __init__(self, maxLogLength):
        self.maxLogLength = maxLogLength
        self.log = [None] * maxLogLength
        self.next_count = 0

    def _createExceptionInfo(self):
        count = self.next_count
        self.next_count += 1
        result = ExceptionInfo(count)
        from spark.util.logger import get_sdl
        if get_sdl() is not None:
            get_sdl().logger.error(result.format_exception())
        self.log[count % self.maxLogLength] = result
        return result

    def recordLocation(self, message):
        try:
            raise RecordedLocation(message)
        except RecordedLocation:
            return self._createExceptionInfo().count

    def displayError(self):
        exceptionInfo = self._createExceptionInfo()
        print str(exceptionInfo)
        return exceptionInfo.count

    def recordError(self):
        exceptionInfo = self._createExceptionInfo()
        return exceptionInfo.count

    def __getitem__(self, id_num):
        recordedException = self.log[id_num % self.maxLogLength]
        if recordedException and recordedException.count == id_num:
            return recordedException
        else:
            raise IndexError("cannot find recorded exception %s"%id_num)

    def pm(self, id_num=None):
        if id_num is None:
            id_num = self.next_count - 1
        self[id_num].pm()


MAX_LOG_LENGTH = 100
NEWPM = _PM(MAX_LOG_LENGTH)

try:
    raise Exception("Exception to allow the debugger to run")
except:
    NEWPM.recordError()


def breakpoint(**args):
    print "BREAKPOINT"
    for (k,v) in args.items():
        print "%s=%r"%(k,v)
    try:
        raise KeyError
    except AnyException:
        import pdb, sys
        i2 = sys.exc_info()[2]
        print "i2=", i2
        terminate = False
        pdb.post_mortem(i2)
        if terminate:
            from spark.internal.exception import LowError
            raise LowError("Terminated")
        print "CONTINUING"

################################################################
import inspect

class DEBUG(object):
    """Object for assisting with the optional printing of diagnostics.

    A DEBUG object is used as a function to print out a formatted
    diagnostic message. Each DEBUG object has a boolean state
    (initially False/off) that can be switched using the on() and
    off() methods. When off, the calling the object as a function does
    nothing. When on, calling the object with a format string and
    optional arguments will result in the formatted message being
    displayed to the console.

    A significant advantage of using DEBUG over passing a formatted
    string to a logging method is that if diagnostic messages are not
    wanted, there is no overhead involved in accessing and formatting
    the values.

    Generally, each file would create its own instance of DEBUG to be
    called debug:
    
    debug = DEBUG(__name__)

    Where a diagnostic message is desired, the debug object would be
    used as a function, passing in a format string as the first
    argument. There are two modes of operation.

    (1) If additional positional arguments are supplied to the call,
    then these are treated as positional arguments to the format
    string.

    e.g., debug("a=%s, b=%r", a, b)

    (2) Alternatively, variable names and limited forms of expressions
    can be embedded in the conversion specifiers, and these will be
    evaluated (with respect to the locals and globals where debug was
    called) and used as values to format.

    e.g., debug("a=%(a)s, b=%(b)r")
    e.g., debug("The value is %(x.veryExpensiveprocessing())s")
    """

    __slots__ = (
        "_name",
        "_shortname",
        "_enabled",
        )

    def __init__(self, name):
        self._name = name
        self._enabled = False
        try:
            self._shortname = name[name.rindex(".")+1:]
        except ValueError:
            self._shortname = name
            
    def on(self):
        self._enabled = True
        return self

    def off(self):
        self._enabled = False
        return self

    def __call__(self, format, *args):
        if self._enabled:
            if args:
                msg = format%args
            elif '%' in format:
                msg = format%EvalDict(inspect.currentframe().f_back)
            else:
                msg = format
            sys.stderr.write("DEBUG %s: %s\n"%(self._shortname, msg))
            sys.stderr.flush()

    def __nonzero__(self):
        return self._enabled

_NOTHING = ["NOTHING"]                  # Dummy value

_VALUE_STR_PREFIX = "!" # prefix character for conversion to SPARK value string

class EvalDict(object):
    """A dict-like object where self[x] return the string x evaluated
    with respect to the given frame.
    """

    __slots__ = ("frame",
                 )

    def __init__(self, frame):
        self.frame = frame

    def __getitem__(self, key):
        frame = self.frame
        if key.startswith(_VALUE_STR_PREFIX):
            expr = key[1:]
            from spark.internal.parse.basicvalues import value_str
            fun = value_str
        else:
            expr = key
            fun = _identity
        val = frame.f_locals.get(expr, _NOTHING)
        if val is _NOTHING:
            val = frame.f_globals.get(expr, _NOTHING)
            if val is _NOTHING:
                try:
                    val = eval(expr, frame.f_locals, frame.f_globals)
                except:
                    return _INVALID # Cannot use a string if formatted using %r
        return fun(val)

class _Invalid:
    "An object whose representation is always <INVALID>"
    def __str__(self):
        return "<INVALID>"
    def __repr__(self):
        return "<INVALID>"
_INVALID = _Invalid()

def _identity(x):
    return x

    

################################################################

def re_raise():
    exc_info = sys.exc_info()
    raise exc_info[0], exc_info[1], exc_info[2]

################################################################

def pair_up(list):
    i = 0
    result = []
    length = len(list)
    while i < length:
        if i+1 == length:
            result.append((list[i],None))
        else:
            result.append((list[i], list[i+1]))
        i = i + 2
    return result

NOCHANGE = intern("NOCHANGE")

################################################################

# Marker to identify a class attribute that needs to be overriden by subclasses

_SPECIAL_METHODS = ("__call__",)

class _Abstract(object):
    __slots__ = ()
    def __str__(self):
        return "ABSTRACT"
    def __repr__(self):
        return "<ABSTRACT>"
    def __getattr__(self, attr):
        if attr.startswith("__") and attr not in _SPECIAL_METHODS:
            raise AttributeError(attr)
        else:
            raise Exception("ABSTRACT class attribute was used")

ABSTRACT = _Abstract()

################################################################
def mybreak(**args):
    try:
        raise Exception("mybreak")
    except AnyException:
        import pdb
        import sys
        pdb.post_mortem(sys.exc_info()[2])
        
def plural(number, zero, one, many):
    "Return a string appropriate for the number: zero, one, or <number> many."
    if number == 0:
        return zero
    elif number == 1:
        return one
    else:
        return "%s %s"%(number, many)

################################################################
POSITIVE = True
NEGATIVE = False

# These are values that can be yielded by solutions
SOLVED = intern("SOLVED")
INCOMPLETE = intern("INCOMPLETE")

# This and SOLVED are values that can be returned by solution
NOT_SOLVED = False

ONE_SOLUTION = (SOLVED,)    # like an iterator that returns one solution
NO_SOLUTIONS = ()          # like an iterator that returns no solutions

def solutions(boolean):
    if boolean:
        return ONE_SOLUTION
    else:
        return NO_SOLUTIONS

def solution(boolean):
    if boolean:
        return SOLVED
    else:
        return NOT_SOLVED
    
SUCCESS = intern('SUCCESS')

BUILTIN_PACKAGE_NAME = "spark.lang.builtin"

LOCAL_ID_PREFIX = "_" 
