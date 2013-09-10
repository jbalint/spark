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

if javaMode():
    # Use SConstructorP as a base for subclassing as it handles Python
    # values better.
    from com.sri.ai.jspark.values import SConstructorP as Constructor
    from com.sri.ai.jspark.values import ConstructorValueException
    from com.sri.ai.jspark.values import ConstructorUtil as _ConstructorUtil
    coerceConstructor = _ConstructorUtil.coerce
    
    # Although SConstructor implements SConstructorInterface you
    # cannot access the public static constants of
    # SConstructorInterface via SConstructorP. You can't even access
    # them directly from SConstructorInterface :-(
else:
    from spark.internal.parse.constructor_python import Constructor, ConstructorValueException
    def coerceConstructor(fromcon, tocon, obj):
        return fromcon.coerce(tocon, obj)

INTEGER = intern("INTEGER")
BIGINTEGER = intern("BIGINTEGER")
FLOAT = intern("FLOAT")
STRING = intern("STRING")
SYMBOL = intern("SYMBOL")
STRUCTURE = intern("STRUCTURE")
LIST = intern("LIST")
VARIABLE = intern("VARIABLE")
