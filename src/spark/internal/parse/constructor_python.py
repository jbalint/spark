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

class Constructor(object):
    """Construct something, using information from tok as necessary"""
    __slots__ = ()
    def createSymbol(self, start, end, string):
        raise ConstructorValueException("Unimplemented")
    def createVariable(self, start, end, string):
        raise ConstructorValueException("Unimplemented")
    def createStructure(self, start, end, functor_string, args):
        raise ConstructorValueException("Unimplemented")
    def createList(self, start, end, elements):
        raise ConstructorValueException("Unimplemented")
    def createString(self, start, end, string):
        raise ConstructorValueException("Unimplemented")
    def createInteger(self, start, end, integer):
        raise ConstructorValueException("Unimplemented")
    def createBigInteger(self, start, end, integer):
        raise ConstructorValueException("Unimplemented")
    def createFloat(self, start, end, float):
        raise ConstructorValueException("Unimplemented")
    # deconstructors
    SYMBOL = intern("SYMBOL")
    VARIABLE = intern("VARIABLE")
    INTEGER = intern("INTEGER")
    BIGINTEGER = intern("BIGINTEGER")
    FLOAT = intern("FLOAT")
    STRING = intern("STRING")
    STRUCTURE = intern("STRUCTURE")
    LIST = intern("LIST")
    def start(self, obj):
        raise ConstructorValueException("Unimplemented")
    def end(self, obj):
        raise ConstructorValueException("Unimplemented")
    def asValue(self, obj):
        raise Exception("deprecated")
    def asFloat(self, obj):
        "Return the value of a FLOAT, raise a ValueError otherwise"
        raise ConstructorValueException("Unimplemented")
    def asInteger(self, obj):
        "Return the value of an INTEGER raise a ValueError otherwise"
        raise ConstructorValueException("Unimplemented")
    def category(self, obj):
        "Returns one of SYMBOL, VARIABLE, INTEGER, FLOAT, STRING, SYMBOL, STRUCTURE, LIST. Raises a ValueError if obj is not appropriate."
        raise ConstructorValueException("Unimplemented")
    def functor(self, obj):
        "Functor string for structure, None for anything else"
        raise ConstructorValueException("Unimplemented")
    def asString(self, obj):
        "Return the string name of a VARIABLE, SYMBOL, or STRING"
        raise ConstructorValueException("Unimplemented")
    def components(self, obj):
        "Iterator for components of a compound structure, None if not."
        raise ConstructorValueException("Unimplemented")

    def coerce(self, pcon, obj):
        if self == pcon:
            return obj
        cat = pcon.category(obj)
        start = pcon.start(obj)
        end = pcon.end(obj)
        if cat == pcon.SYMBOL:
            return self.createSymbol(start, end, pcon.asString(obj))
        elif cat == pcon.VARIABLE:
            return self.createVariable(start, end, pcon.asString(obj))
        elif cat == pcon.STRUCTURE:
            return self.createStructure(start, end, \
                                        pcon.functor(obj), \
                                        [self.coerce(pcon, x) for x in pcon.components(obj)])
        elif cat == pcon.FLOAT:
            return self.createFloat(start, end, pcon.asFloat(obj))
        elif cat == pcon.INTEGER:
            return self.createInteger(start, end, pcon.asInteger(obj))
        elif cat == pcon.BIGINTEGER:
            return self.createBigInteger(start, end, pcon.asBigInteger(obj))
        elif cat == pcon.STRING:
            return self.createString(start, end, pcon.asString(obj))
        elif cat == pcon.LIST:
            return self.createList(start, end, \
                                   [self.coerce(pcon, x) for x in pcon.components(obj)])
        else:
            raise ConstructorValueException("Invalid category %r"%cat)
        
            
        
class ConstructorValueException(Exception):
    def __init__(self, message):
        return Exception(message)
