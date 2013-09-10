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
#* "$Revision:: 131                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
import types
from spark.internal.version import *
from spark.internal.common import NEWPM, NoStackMixin

# Class hierarchy:
# Exception
#   StandardError
#   StopIteration
#   SystemExit
#   SPARKException
#     LocatedError - An error with location information attached
#       CapturedError
#     UnlocatedError - An error with no location attached


################################################################
# Exceptions that are caught should be handled in one of the following ways:

# If there is a very specific exception that is expected (e.g.,
# IndexError), you may catch that exception and continue execution.


# You may capture an exception, display the exception and then not use
# the exception. The traceback is kept in a fixed length log of
# recorded exceptions, and referenced by the exception number. These
# recorded exceptions can drop off the log if many more exceptions are
# recorded. If you intend to raise some new exception, you might want
# to keep a reference to the id number (errid) so that when debugging
# the new exception, you can enter the debugger on the old exception
# (NEWPM(errid)).

# except AnyException:
#     errid = NEWPM.displayError()

# When executing an Expr, you may catch something other than a
# LocatedError, wrap that in a CapturedError and raise that new
# error. In general you would not print the error at this time, but
# rather let the handler for the CapturedError print the
# message. First you record the error in the log. Then you raise a
# CapturedError. When using the debugger on the new error, you can
# enter the dubugger using the error id.

# except NotLocatedError:
#     errid = NEWPM.recordError()
#     raise CapturedError(expr, errid)

class SPARKException(Exception):
    """General class of exceptions for SPARK"""
    __slots__ = ()
#     def __repr__(self):
#         try:
#             return "<%s: %s>"%(self.__class__.__name__, self.args)
#         except AnyException:
#             return Exception.__repr__(self)
        
#     def __str__(self):
#         return self.__repr__()
    
    def class_name(self):               # for spark.tests.meta_test
        return self.__class__.__name__

class LocatedError(SPARKException, NoStackMixin):
    """An error that occured during execution of an expression."""
    __slots__ = (
        "expr",
        )

    def __init__(self, expr, message):
        SPARKException.__init__(self, message)
        self.expr = expr

    def fullString(self):
        try:
            return self.expr.getLocationString(self[0])
        except:
            print "ERROR GETTING THE LOCATION STRING OF THE ERROR"
            import traceback
            traceback.print_exc()
            print 
            from spark.internal.parse.basicvalues import value_str
            return "- %s\n%s"%(self[0], value_str(self.expr))

    def __str__(self):
        return self.fullString()

class CapturedError(LocatedError):
    __slots__ = (
        "errid"
        "usage"
        )

    def __init__(self, expr, errid, usage):
        self.errid = errid
        self.usage = usage
        errinfo = NEWPM[errid]
        LocatedError.__init__(self, expr, str(NEWPM[errid]))

    def pm(self):
        NEWPM(self.errid)


class UnlocatedError(SPARKException):
    """An error that cannot be associated with the execution of any
    particular expr."""
    __slots__ = ()
    def get_display_string(self):
        return str(self)                # don't include the class name

class ParseError(UnlocatedError):
    """An error associated with parsing SPARKL source."""
    __slots__ = ()

class ProcessingError(UnlocatedError):
    """An error associated with processing SPARKL source."""
    __slots__ = ()

# Collection of classes that include everything that is not LocatedError
NotLocatedError = (StandardError, UnlocatedError)

#signifies an internal error.
#use if you don't have access to zexpr or term that is
#executing the code.
class LowError(UnlocatedError):
    __slots__ = ()
    def __init__(self, format, *args):
        message = format%args
        UnlocatedError.__init__(self, message)

    def error(self, expr, errid):
        return CapturedError(expr, errid, expr.usage)

# class SPARKError(SPARKException):
#     """Error"""

class InternalException(UnlocatedError):
    """Normally indicates that something is wrong with the SPARK implementation
    or user additions to the implementation."""

class RuntimeException(UnlocatedError):
    """Exceptions raised at runtime.
    These are semantic exceptions that the semantic analysis is not
    able to pick up before run-time."""

class RuntimeModeException(RuntimeException):
    pass

class RuntimeArgumentsException(RuntimeException):
    pass
    
# class SemanticException(UnlocatedError):
#     """Exception raised during semantic processing.
#     The user has entered invalid code."""

class InvalidArgument(UnlocatedError):
    """Invalid argument passed to a function"""

# class ModuleError(SPARKError):
#     """A problem occurred during the loading of a module."""
#     def __init__(self, modname, message):
#         SPARKError.__init__(self)
#         self.modname = modname
#         self.message = message
#     def __str__(self):
#         return "For SPARK module %s - %s"%(self.modname, self.message)

################################################################

class Unimplemented(UnlocatedError):
    """Method should be defined in subclass"""

################################################################
# Errors and error printing routines

def find_line(string, index):
    """For the index into string, return the line number (0-based)
    character within line (0-based), and the line itself (no newline)."""
    line_start_index = string.rfind('\n',0,index)+1
    line_end_index = string.find('\n',index)
    if line_end_index < 0:
        line_end_index = len(string)
    lineindex = string.count('\n',0,index)
    line = string[line_start_index:line_end_index]
    charindex = index - line_start_index
    return (lineindex, charindex, line)

def expandtabs(charindex, line):
    """Expand the tabs in line. Return the equivalent character
    index to charindex and the expanded line."""
    expandedline = line.expandtabs()
    prefix = line[:charindex].expandtabs()
    expandedcharindex = len(prefix)
    return (expandedcharindex, expandedline)

def error_location_string(string, context_index, error_index, marker):
    """Return a string describing the location of an error."""
    (clinenum, ccharnum, cline) = find_line(string, context_index)
    (elinenum, echarnum, eline) = find_line(string, error_index)
    (coffset, cmodline) = expandtabs(ccharnum, cline)
    (eoffset, emodline) = expandtabs(echarnum, eline)
    if context_index == error_index:
        return "%3d| %s\n     %s%s"%(elinenum+1, emodline," "*eoffset, marker)
    elif clinenum == elinenum:
        mark = " "*coffset + "-"*(eoffset-coffset)
        return "%3d| %s\n     %s%s"%(elinenum+1, emodline, mark, marker)
    else:
        mark1 = " "*coffset + "-"*(len(cmodline)-coffset)
        mark2 = "-"*eoffset
        if clinenum + 1 == elinenum:
            format = "%3d| %s\n     %s\n%3d| %s\n     %s%s"
        else:
            format = "%3d| %s\n     %s...\n%3d| %s\n  ...%s%s"
        return  format % (clinenum+1, cmodline, mark1,
                          elinenum+1, emodline, mark2, marker)

# class Error(SPARKError, NoStackMixin):
#     """Exception raised when parsing fails."""
#     marker = "^HERE"
#     def __init__(self, filename, istring, newindex, errstring, oldindex):
#         SPARKError.__init__(self)        
#         (linenum, charnum, _line) = find_line(istring, newindex)
#         loc_string = error_location_string(istring, oldindex, newindex, \
#                                            self.marker)
#         self.msg = "Line %d, char %d of %s:\n%s\n%s" \
#                    % (linenum+1, charnum+1, filename, loc_string, errstring)
#         Exception.__init__(self, self.msg)

#     def __str__(self):
#         return self.msg

# class TermErrorIndex(Error):
#     marker = "^HERE"
#     def __init__(self, term, msg, index):
#         Error.__init__(self, term.get_sparkl_unit().get_filename(), term.get_text(),
#                        index, msg, term.start)

# class TermError(TermErrorIndex):
#     marker = "-"
#     def __init__(self, term, format, *args):
#         if args:
#             msg = format%args
#         else:
#             msg = format
#         TermErrorIndex.__init__(self, term, msg, term.end - 1)

# class ContextError(Error):
#     def __init__(self, newcontext, errstring, oldindex=None):
#         if newcontext:
#             if oldindex is None:
#                 oldindex = newcontext.startindex()
#             istring = newcontext.inputstring()
#             filename = newcontext.info().get_filename()
#             newindex = newcontext.lastindex() # start of last token
#         Error.__init__(self, filename, istring, newindex, errstring, oldindex)

# class SyntaxContextError(ContextError):
#     """Syntax error - input does not match base BNF"""

# class ModuleContextError(ContextError):
#     def __init__(self, context, module_error):
#         ContextError.__init__(self, context, str(module_error))

# def error(oldcontext, newcontext, cstring, ostring):
#     err =  SyntaxContextError(newcontext, \
#                        "Found %s %s."%(ostring, cstring), \
#                        oldcontext.startindex())
#     raise err


################################################################
# The following are exceptions that include the TFrame where they arose

_FAILURE_CLASSES = {}                    # maps name to class

def installFailure(cl):
    _FAILURE_CLASSES[cl.__name__] = cl

def constructFailure(class_name_string, tframe, arg):
    try:
        cl = _FAILURE_CLASSES[class_name_string]
    except KeyError:
        raise LowError("Unknown Failure class %r", class_name_string)
    return cl(tframe, arg)

def deconstructFailure(failure):
    name = failure.__class__.__name__
    if not (_FAILURE_CLASSES.has_key(name)): raise AssertionError, \
           "The Failure class %s has not been registered"%name
    return (name, ) + failure.args
    
class Failure(SPARKException):
    """Failure of a task expression"""
    __slots__ = (
        )
    valueClass = None
    def __init__(self, ignore_tframe, arg):
        # TDOD: Remove the tframe argument from all Failure constructors
        # Should not include the tframe in the Failure object - it leads to circular refs
        # SPARKException.__init__(self, tframe,arg)
        SPARKException.__init__(self, 0 ,arg)
        # DNM - remove this check for when the tframe argument is
        # really a solver_target, not a tframe.
        #from spark.internal.repr.taskexpr import TFrame
        #if not (isinstance(tframe, TFrame)): raise AssertionError
        if self.valueClass is not None:
            if not (isinstance(arg, self.valueClass)): raise AssertionError, \
                   "Expecting an instance of %r as the Failure argument"%self.valueClass

#     def getFailureTFrame(self):
#         return self.args[0]

    def getFailureValue(self):
        return self.args[1]
    
    def __lt__(self, ignore_other):
        raise TypeError("Ordering of Failures is not valid")
    
    def __le__(self, ignore_other):
        raise TypeError("Ordering of Failures is not valid")
    
    def __gt__(self, ignore_other):
        raise TypeError("Ordering of Failures is not valid")
    
    def __ge__(self, ignore_other):
        raise TypeError("Ordering of Failures is not valid")
    
    def __eq__(self, other):
        return (self is other) \
               or (type(self) == type(other) and self.args == other.args)
        
    def __ne__(self, other):
        return (self is not other) \
               and  (type(self) != type(other) or self.args != other.args)

    def __hash__(self):
        return hash(self.args)


class FailFailure(Failure):
    """Failure caused by an explicit fail: task.
    Value is any SPARK value,"""
installFailure(FailFailure)

class TestFailure(Failure):
    """Failure caused by a test (e.g., a context) being false.
    Value is a reason string."""
    valueClass = basestring
installFailure(TestFailure)

class MessageFailure(Failure):
    """Failure with some associated message - usually from special TFrame code.
    Value is a reason string."""
    valueClass = basestring
installFailure(MessageFailure)

class NoGoalResponseFailure(Failure):
    """Failure caused by there not being any response to a goal.
    Value should be an event."""
    # valueClass = Event # don't want such a low level module importing Event
installFailure(NoGoalResponseFailure)

class NoProcedureFailure(Failure):
    """NO LONGER IN USE - Failure caused by there being no procedure for a goal.
    Value is the goal event."""
installFailure(NoProcedureFailure)
        
class SignalFailure(Failure):
    """Failure caused by an external signal.
    Value is the signal."""
installFailure(SignalFailure)


class ExceptionFailure(Failure):
    """Failure caused by raising an exception"""
    __slots__ = (
        "_exception",
        "_errid",
        )
    def __init__(self, tframe, exception, errid=None):
        from spark.internal.parse.basicvalues import String, isString
        self._errid = errid
        self._exception = exception
        if isString(exception): # restoring from persist
            # Cannot save real Exception, just using the string
            errstring = exception
        else:
            errstring = "[%d] %s"%(errid, exception)
        Failure.__init__(self, tframe, errstring)

    def pm(self):
        if self._errid:
            NEWPM.pm(self._errid)
        else:
            print "CANNOT perform post-mortem on a Failure restored from persisted state"
installFailure(ExceptionFailure)
