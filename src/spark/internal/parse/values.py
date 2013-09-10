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
from spark.internal.parse.javamode import javaMode
# Defines 

if javaMode():
    # Java implementation
    from com.sri.ai.jspark.values import SVariable as _Variable
    isVariable = _Variable.isa
    Variable = _Variable.coerce

    from com.sri.ai.jspark.values import SSymbol as _Symbol
    isSymbol = _Symbol.isa
    Symbol = _Symbol.coerce

    from com.sri.ai.jspark.values import SStructure as _Structure
    isStructure = _Structure.isa
    Structure = _Structure.coerce

    from com.sri.ai.jspark.values import Values as _Values
    value_str = _Values.value_str
    append_value_str = _Values.append_value_str
    inverse_eval = _Values.inverse_eval
    setUnpickleFunctions = _Values.setUnpickleFunctions
    VALUE_CONSTRUCTOR = _Values.VALUE_CONSTRUCTOR
    # Set the reg_append_value_str and reg_inverse_eval functions
    import spark.internal.parse.set_methods as _sm
    _Values.setRegFunctions(_sm.reg_append_value_str, _sm.reg_inverse_eval)
    # set the methods for Python instances of Value
    from spark.internal.parse.value import Value as _Value
    def _Value_append_value_str(x, buf):
        return x.append_value_str(buf)
    def _Value_inverse_eval(x):
        return x.inverse_eval()
    _sm.set_methods(_Value, _Value_append_value_str, _Value_inverse_eval)
else:
    # Python implementation
    from spark.internal.parse.values_python import \
         Symbol, isSymbol, Variable, isVariable, Structure, isStructure, \
         value_str, append_value_str, inverse_eval, \
         setUnpickleFunctions, VALUE_CONSTRUCTOR



################################################################
# Specify functions for unpickling types that are not standard Python
# These all have to be top level functions for pickling to work.
# For pickling to be compatible across implementations,
# these functions have to be defined in the same module across implementations.

def __Variable(x):
    return Variable(x)

def __Symbol(x):
    return Symbol(x)

def __Structure(f, args):
    return Structure(f, args)

import copy_reg
copy_reg.constructor(__Symbol)
copy_reg.constructor(__Variable)
copy_reg.constructor(__Structure)

setUnpickleFunctions(__Variable, __Symbol, __Structure)
