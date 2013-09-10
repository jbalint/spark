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
#* "$Revision:: 129                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

from spark.internal.version import *
from spark.internal.parse.basicvalues import *

################################################################
# Handling SPARK types
# The following has been moved to spark.lang.types
# remove this when everyone has updated to a version of SPARK that includes it

PACKAGE = "spark.lang.types"

S_Integer = Symbol(PACKAGE + ".integer")
S_Boolean = Symbol(PACKAGE + ".boolean")
S_String = Symbol(PACKAGE + ".string")
S_Float = Symbol(PACKAGE + ".float")
S_List = Symbol(PACKAGE + ".list")
S_Variable = Symbol(PACKAGE + ".variable")
S_Symbol = Symbol(PACKAGE + ".symbol")
S_Structure = Symbol(PACKAGE + ".structure")
S_UnknownType = Symbol(PACKAGE + ".unknownType")

def structureInverse(s):
    if isStructure(s):
        return (s.functor, List(s))
    else:
        return None

def sparkTypeOf(x):
    if isInteger(x):
        return S_Integer
    elif isBoolean(x):
        return S_Boolean
    elif isString(x):
        return S_String
    elif isFloat(x):
        return S_Float
    elif isList(x):
        return S_List
    elif isVariable(x):
        return S_Variable
    elif isSymbol(x):
        return S_Symbol
    elif isStructure(x):
        return S_Structure
    else:
        return S_UnknownType
