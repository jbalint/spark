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
"""This Python module provides the ability to take values and
interpret them as variable-free value expressions to be evaluated with
respect to the builtin module."""

from spark.internal.version import *

from spark.internal.parse.basicvalues import String, isString, List, isList, Integer, isInteger, Float, isFloat, Symbol, isSymbol, Structure, isStructure, BACKQUOTE_SYMBOL, PREFIX_COMMA_SYMBOL
from spark.internal.repr.varbindings import valuesBZ
from spark.internal.common import BUILTIN_PACKAGE_NAME
#from spark.pylang.implementation import FunImpInt

# TODO: replace this with BUILTIN_EVAL_BINDINGS

def builtin_evaluate(agent, value):
    if (isSymbol(value)): raise AssertionError, \
           "A naked symbol is not evaluable"
    if isString(value):
        return value
    elif isList(value):
        elements = [builtin_evaluate(agent, v) for v in value]
        return List(elements)
    elif isInteger(value):
        return value
    elif isFloat(value):
        return value
    elif isStructure(value):
        sym = value.functor
        if sym == BACKQUOTE_SYMBOL:
            return builtin_quoted(agent, value[0])
        else:
            argvalues = [builtin_evaluate(agent, v) for v in value]
            fullsym = Symbol(BUILTIN_PACKAGE_NAME + "." + sym.id)
            imp = agent.getImp(fullsym)
            #if not (isinstance(imp, FunImpInt)): raise AssertionError, \
            #    "Not a function: %s"%sym
            b, z = valuesBZ(argvalues)
            result = imp.call(agent, b, z)
            return result
    else:
        return value

# TODO: replace this with BUILTIN_QUOTED_BINDINGS
def builtin_quoted(agent, value):
    if isList(value):
        elements = [builtin_quoted(agent, v) for v in value]
        return List(elements)
    elif isStructure(value):
        sym = value.functor
        if sym == PREFIX_COMMA_SYMBOL:
            return builtin_evaluate(agent, value[0])
        else:
            argvalues = [builtin_quoted(agent, v) for v in value]
            return Structure(sym, argvalues)
    else:
        return value
