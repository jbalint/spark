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
#* "$Revision:: 460                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
# This file corresponds to the java package com.sri.ai.jspark.values
# and its exports are the equivalent of the Python-related public
# static methods defined in class com.sri.ai.jspark.values.Values

from spark.internal.common import ABSTRACT
from spark.internal.parse.value import Value
from spark.internal.parse.values_common import *
from spark.internal.parse.stringbuffer import StringBuffer
from spark.internal.parse.set_methods import reg_append_value_str, reg_inverse_eval

import re
import thread

################################################################
################################################################
#
# Cached
#
################################################################
################################################################

class _CachedFactory(object):
    __slots__ = (
        "resultClass",                  # class returned by __call__
        "cache",             # dict mapping interned strings to values
        "lock",
        "constructor",                  # constructor
        )

    def __init__(self, resultClass, constructor):
        self.resultClass = resultClass
        self.cache = {}
        self.lock = thread.allocate_lock()
        self.constructor = constructor

    def __call__(self, name):
        if isinstance(name, self.resultClass):
            return name
        name = intern(str(name))
        #print "Acquiring lock for creating", name
        self.lock.acquire()
        try:
            inst = self.cache.get(name)
            if inst is None:
                inst = self.constructor(name)
                self.cache[name] = inst
        finally:
            #print "Releasing lock for creating", name
            self.lock.release()
        return inst
        
    def setSymbol(self, sym):
        self.cache[sym.name] = sym


class _Cached(Value):
    __slots__ = (
        "name",
        )

    def __init__(self, name):
        self.name = name

    def inverse_eval(self):
        from spark.internal.parse.basicvalues import BACKQUOTE_SYMBOL
        return BACKQUOTE_SYMBOL.structure(self)

# Disallow comparison/sorting until the Java side is capable of it
#     def __cmp__(self, other):
#         if isinstance(other, _Cached):
#             return cmp(self.name, other.name) or cmp(self.__class__.__name__, other.__class__.__name__)
#         elif isinstance(other, basestring):
#             return 1

    def __str__(self):
        # Note this uses the name of the object, not its value_str
        return self.name



################################################################
################################################################
#
# Symbols
#
################################################################
################################################################


class _Symbol(_Cached):
    __slots__ = (
        "modname",
        "id",
        )

    def __init__(self, name):
        _Cached.__init__(self, name)
        index = name.rfind(".")
        if index < 0:
            self.modname = None
            self.id = intern(name)
        else:
            self.modname = intern(name[:index])
            self.id = intern(name[index+1:])

    # Since there should only exist one _Symbol object for a Symbol
    # with a given name, we can use object identity for equality
    # rather than doing a string comparison. This also allows us not
    # to redefine __hash__.

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def __lt__(self, other):
        if isinstance(other, _Symbol):
            return self.name < other.name
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, _Symbol):
            return self.name <= other.name
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, _Symbol):
            return self.name > other.name
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, _Symbol):
            return self.name > other.name
        else:
            return NotImplemented

    def append_value_str(self, buf):
        # default value_str: '|' at start and end of the name
        return buf.append("|").append(self.name).append("|")

    def structure(self, *args):
        return _Structure(self, args)

    def isBrace(self):
        return False

    def isTag(self):
        return False

    def isPrefix(self):
        return False

    ################
    # pickling
    
    def __reduce__(self):
        # We use Symbol rather than the class or constructor function,
        # since the persisted object may refer to an object that
        # already exists.
        return (_UNPICKLE_SYMBOL, (self.name,))

_UNPICKLE_SYMBOL = None                   # function to construct a Symbol

_NOQUOTE_PATTERN = re.compile("[_a-zA-Z*/%&@!?<>=][0-9_a-zA-Z*/%&@!?<>=]*(|:|\\{\\})$")

def _constructSymbol(name):
    # Create a new Symbol
    # Test whether the symbol characters need escaping
    if "|" in name or "\\" in name:
        return _EscapedQuotedSymbol(name)
    # Test whether the symbol needs quoting
    matchresult = _NOQUOTE_PATTERN.match(name)
    if not matchresult or matchresult.group() != name:
        return _QuotedSymbol(name)
    # teset whether the symbol is a tag
    if name.endswith(":"):
        return _TagSymbol(name)
    # Test whether the symbol is a brace symbol
    if name.endswith("{}"):
        return _BraceSymbol(name)
    # Ordinary symbol
    return _OrdinarySymbol(name)

Symbol = _CachedFactory(_Symbol, _constructSymbol)

class _QuotedSymbol(_Symbol):
    __slots__ = ()


class _EscapedQuotedSymbol(_Symbol):
    __slots__ = ("_printstring",
                 )

    def __init__(self, name):
        _Symbol.__init__(self, name)
        self._printstring = "|%s|"%_SYMBOL_ESCAPE.sub(r"\\\1", name)

    def append_value_str(self, buf):
        return buf.append(self._printstring)

_SYMBOL_ESCAPE = re.compile(r"([|\\])")


class _TagSymbol(_Symbol):
    __slots__ = ()

    def isTag(self):
        return True

class _BraceSymbol(_Symbol):
    __slots__ = ()

    def isBrace(self):
        return True

class _OrdinarySymbol(_Symbol):
    __slots__ = ()

    def append_value_str(self, buf):
        return buf.append(self.name)

class _PrefixSymbol(_Symbol):
    __slots__ = ()

    def isPrefix(self):
        return True

################################################################

def isSymbol(x):
    return isinstance(x, _Symbol)


################
# special cases that would not otherwise be handled properly
Symbol.setSymbol(_QuotedSymbol(""))
Symbol.setSymbol(_OrdinarySymbol("+"))
Symbol.setSymbol(_OrdinarySymbol("-"))
Symbol.setSymbol(_PrefixSymbol("+#"))
Symbol.setSymbol(_PrefixSymbol("-#"))
BACKQUOTE_SYMBOL = _PrefixSymbol("`#")
Symbol.setSymbol(BACKQUOTE_SYMBOL)
PREFIX_COMMA_SYMBOL = _PrefixSymbol(",#")
Symbol.setSymbol(PREFIX_COMMA_SYMBOL)


################################################################
################################################################
#
# Variables
#
################################################################
################################################################


class _Variable(_Cached):
    __slots__ = ()

    def __init__(self, name):
        _Cached.__init__(self, name)
    
    def append_value_str(self, buf):
        return buf.append(self.name)
    
    def innerVersion(self):
        return Variable("$"+self.name)
    
    outerVersion = ABSTRACT

    ################
    # pickling
    
    def __reduce__(self):
        # We use Variable rather than the class or constructor function,
        # since the persisted object may refer to an object that
        # already exists.
        return (_UNPICKLE_VARIABLE, (self.name,))

    def isCaptured(self):
        return False

    def isLocal(self):
        return False

_UNPICKLE_VARIABLE = None                   # function to construct a Variable

def _constructVariable(name):
    if name.startswith("$$"):
        return _CapturedVariable(name)
    elif name.startswith("$") and len(name) > 1:
        return _LocalVariable(name)
    else:
        raise ValueError("Invalid variable name: %r"%name)

Variable = _CachedFactory(_Variable, _constructVariable)

class _LocalVariable(_Variable):
    __slots__ = ()

    def outerVersion(self):
        return None

    def isLocal(self):
        return True

class _CapturedVariable(_Variable):
    __slots__ = (
        "_outer",
        )

    def __init__(self, name):
        _Variable.__init__(self, name)
        self._outer = None              # compute & cache when needed

    def outerVersion(self):
        return self._outer or self._computeOuter()

    def _computeOuter(self):
        outer = Variable(self.name[1:])
        self._outer = outer
        return outer

    def isCaptured(self):
        return True

################################################################
    

def isVariable(x):
    return isinstance(x, _Variable)
    
################################################################
# Printing Symbols and structures

"""
Parsing:
  Parentheses create a structure with the functor being the symbol
  following the open parenthesis. The following structure has the
  symbol foo as the functor and arguments x, y, and z:
    (foo x y z)
  The functor name may be quoted with '|' characters (and must be
  quoted if it contains unusual characters):
    (|foo| x y z) -> (foo x y z)
  A tag acts as a functor of a structure whose arguments go until the
  next tag or close delimiter:
    [foo: x y z] -> [(|foo:| x y z)]
  These arguments of the tagged structure cannot therefore use the tag
  syntax and must instead use the quoted functor notation:
    [foo: x bar: 1 z] -> [(|foo:| x)  (|bar:| 1 z)]
    [foo: x (|bar:| 1) z] -> [(|foo:| x (|bar:| 1) z)]
  Braces construct a structure with a modified functor name:
    {foo x y z} -> (|foo{}| x y z)
  Some characters ('+', '-', '`', and ',') act as unary prefix
  operators. When used as such the structure generated has a modified
  functor name:
    +foo -> (|+#| foo)
"""




################

################################################################
# Structures

def hash_combine(h1,h2):
    return int((h1*37L+h2)%0x7fffffff)

class _Structure(Value):
    __slots__ = (
        "functor",                      # Functor symbol
        "_args",                         # tuple of arguments
        "_hash",
        )

    def __init__(self, symbol, args):
        if not (isSymbol(symbol)): raise AssertionError
        self.functor = symbol
        self._args = tuple(args)
        self._hash = None

    def append_value_str(self, buf):
        functor = self.functor
        args = self._args
        if functor.isBrace():           # use {foo ...} notation
            buf.append("{")
            buf.append(functor.name[:-2])
            _append_args(buf, args)
            return buf.append("}")
        if functor.isPrefix() and len(args) == 1:
            # Use <prefix><arg> notation
            arg = args[0]
            buf.append(functor.name[:-1])
            if _isNumber(arg) and functor.name[0] in "+-" and arg >= 0:
                buf.append("+")
            return append_value_str(arg, buf)
        # use (foo ...) notation
        buf.append("(")
        functor.append_value_str(buf)
        _append_args(buf, args, True, True)
        return buf.append(")")

    def inverse_eval(self):
        if None in self:                # NULL ELEMENT
            from spark.lang.builtin import inversePartial, PARTIAL_SYMBOL
            (full, nullvalue) = inversePartial(self)
            return PARTIAL_SYMBOL.structure(inverse_eval(full), inverse_eval(nullvalue))
        def switch(arg):
            ie = inverse_eval(arg)
            if isStructure(ie):
                if ie.functor == BACKQUOTE_SYMBOL:
                    return ie[0]
            elif isinstance(ie, int) or isinstance(ie, float) \
                 or isinstance(ie, basestring): # should use Integer, etc.
                return ie
            # otherwise
            return PREFIX_COMMA_SYMBOL.structure(ie)
        args = [switch(arg) for arg in self._args]
        return BACKQUOTE_SYMBOL.structure(_Structure(self.functor, args))

    def __getitem__(self, index):
        return self._args[index]
        # Should ensure that a SPARK List is returned if index is a slice.
        # However, self._args is a tuple and SPARK List == tuple so this is okay

    def __len__(self):
        return len(self._args)

    def __nonzero__(self):
        return True

    def __hash__(self):
        if self._hash is None:
            h = hash_combine(hash(self.functor), 7) # hash(f())!=hash(f)
            for a in self._args:
                h = hash_combine(h, hash(a))
            self._hash = h
        return self._hash

    def __ne__(self, other):
        #print "inEquality testing", self, other
        if self is other:
            return False
        if not isStructure(other) or \
               hash(self) != hash(other) or \
               self.functor != other.functor:
            return True
        sargs = self._args
        oargs = other._args
        if len(sargs) != len(oargs):
            return False
        length = len(sargs)
        i = 0
        while i<length:
            if sargs[i] != oargs[i]:
                return True
            i += 1
        return False

    def __eq__(self, other):
        #print "Equality testing", self, other
        return (self is other) or not self.__ne__(other)

    def __add__(self, other):
        return Structure(self.functor, self._args + tuple(other))

    def __mult__(self, other):
        return Structure(self.functor, self._args * int(other))

    ################
    # pickling

    def __reduce__(self):
        return (_UNPICKLE_STRUCTURE, (self.functor, self._args))


_UNPICKLE_STRUCTURE = None                   # function to construct a Structure

_INT_OR_LONG_OR_FLOAT = (int, long, float)
def _isNumber(x):
    return isinstance(x, _INT_OR_LONG_OR_FLOAT)



def isStructure(x):
    return isinstance(x, _Structure)

Structure = _Structure

################################################################
################################################################
#
#
#
################################################################
################################################################

def value_str(x):
    return str(append_value_str(x, StringBuffer()))

_STRING_ESCAPE = re.compile(r'(["\\])')
_NUMBER_TYPES = (int, long, float)

def append_value_str(x, buf):
    if isinstance(x, Value):
        rbuf = x.append_value_str(buf)
        if rbuf != buf: raise AssertionError, \
           "append_value_str is not returning the original buffer"
        return buf
    elif isinstance(x, basestring):
        buf.append('"' + _STRING_ESCAPE.sub(r"\\\1", x) + '"')
        return buf
    elif isinstance(x, _NUMBER_TYPES):
        buf.append(str(x))
        return buf
    elif isinstance(x, tuple):
        buf.append("[")
        _append_args(buf, x, False, True)
        return buf.append("]")
    else:
        reg_append_value_str(x, buf)
        return buf

INVALID_SYMBOL = Symbol("INVALID")

def inverse_eval(x):
    if isinstance(x, Value):
        result = x.inverse_eval()
    elif isinstance(x, basestring) or  isinstance(x, _NUMBER_TYPES):
        result = x
    elif isinstance(x, tuple):
        if None in x:                # NULL ELEMENT
            (full, nullvalue) = inversePartial(self)
            result = PARTIAL_SYMBOL.structure(inverse_eval(full), inverse_eval(nullvalue))
        else:
            elts = [inverse_eval(elt) for elt in x]
            if None in elts:
                result = None # if we allow inverse_eval to return None
            else:
                result = tuple(elts)
    else:
        result = reg_inverse_eval(x)
    if result is None:
        try:
            info = str(x)
        except:
            info = "object of type %r"%type(x)
        msg = "Cannot run inverse_eval on "+info
        print "WARNING:", msg
        return INVALID_SYMBOL.structure(msg)
    else:
        return result

################################################################
################################################################

def _isTagStructure(x):
    return isStructure(x) and x.functor.isTag()


def _append_args(buf, args, initial_space=True, allow_tags=True):
    nargs = len(args)
    lim = nargs - 1
    if allow_tags:
        while lim >= 0 and _isTagStructure(args[lim]):
            lim = lim - 1
    for j in range(0, nargs):
        if j > 0 or initial_space:
            buf.append(' ')
        arg = args[j]
        if arg is None:                 # NULL ELEMENT
            buf.append('()')
        elif j <= lim:
            append_value_str(arg, buf)
        else:
            buf.append(arg.functor.name)
            _append_args(buf, arg._args, True, False)
        

################################################################

_List = tuple                           # List is defined in basicvalues
createStructure = _Structure

def setUnpickleFunctions(unpickle_variable, unpickle_symbol, unpickle_structure):
    global _UNPICKLE_VARIABLE
    _UNPICKLE_VARIABLE = unpickle_variable
    global _UNPICKLE_SYMBOL
    _UNPICKLE_SYMBOL = unpickle_symbol
    global _UNPICKLE_STRUCTURE
    _UNPICKLE_STRUCTURE = unpickle_structure    

################################################################
# Constructing these values using sparkl_parser
from spark.internal.parse.constructor import Constructor, INTEGER, STRING, FLOAT, VARIABLE, SYMBOL, STRUCTURE, LIST

class ValueConstructor(Constructor):
    def createSymbol(self, start, end, string):
        return Symbol(string)
    def createVariable(self, start, end, string):
        return Variable(string)
    def createStructure(self, start, end, functor_name, args):
        return Structure(Symbol(functor_name), args)
    def createList(self, start, end, elements):
        return List(elements)
    def createString(self, start, end, string):
        return String(string)
    def createInteger(self, start, end, integer):
        return Integer(integer)
    def createFloat(self, start, end, float):
        return Float(float)
    def start(self, obj):
        return -1
    def end(self, obj):
        return -1
    def asFloat(self, obj):
        if isFloat(obj):
            return obj
        else:
            raise ValueError("Not a float: %r"%obj)

    def asInteger(self, obj):
        if isInteger(obj):
            return obj
        else:
            raise ValueError("Not an integer: %r"%obj)

    def category(self, object):
        if isString(object):
            return STRING
        elif isInteger(object):
            return INTEGER
        elif isFloat(object):
            return FLOAT
        elif isSymbol(object):
            return SYMBOL
        elif isStructure(object):
            return STRUCTURE
        elif isList(object):
            return LIST
        elif isVariable(object):
            return VARIABLE
        else:
            raise ValueError("Not a valid object")

    def functor(self, obj):
        if isStructure(obj):
            return obj.functor.name
        else:
            return None

    def asString(self, obj):
        if isString(obj):
            return obj
        elif isVariable(obj):
            return obj.name
        elif isSymbol(obj):
            return obj.name
        else:
            return None
    
    def components(self, obj):
        if isList(obj):
            return obj
        elif isStructure(obj):
            return obj._args
        else:
            return None

VALUE_CONSTRUCTOR = ValueConstructor()
