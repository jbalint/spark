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
from spark.internal.parse.pickleable_object import PickleableObject
from spark.internal.parse.searchindex import recursiveBinarySearch

#VALID_LOCATION_TYPES = (type(None), Expr)

class ErrorMsg(PickleableObject):
    __stateslots__ = ("_indexOffset",
                      "_dict",
                      )
    __slots__ = __stateslots__
    level = None
    format = "error"

    def __init__(self, expr, *args):
        # TODO: on pickling we will need to deal with expr
        #assert isinstance(expr, VALID_LOCATION_TYPES)
        if len(self.argnames) != len(args):
            raise AssertionError("Invalid argument list")
        self.setExpr(expr)
        _dict = {}
        for (argname, arg) in zip(self.argnames, args):
            _dict[argname] = arg
        self._dict = _dict

    def setExpr(self, expr):
        if expr is None:
            self._indexOffset = None
        else:
            exprIndex = expr.index
            spuIndex = expr.getSPU().index
            self._indexOffset = exprIndex - spuIndex
        
    def getExpr(self, spu):
        if self._indexOffset is None:
            return None
        else:
            spuIndex = spu.index
            return recursiveBinarySearch(spu, spuIndex + self._indexOffset)

    def getErrString(self):
        return self.__class__.__name__[:4] + ":" + (self.format % self._dict)

    def __cmp__(self, other):
        self_indexOffset = self._indexOffset
        other_indexOffset = other._indexOffset
        if self_indexOffset is not None:
            if other_indexOffset is not None:
                return self_indexOffset.__cmp__(other_indexOffset)
            else:
                return -1
        else:
            if other_indexOffset is not None:
                return 1
            else:
                return 0
    
################################################################
# processing stages


################################################################
RAW = -1
NOT_RAW = F0 = 00                          # fatal to reading and parsing the SPU
#PROCESSING0 = 03
OK0 = 05                                # successfully set exprs

F1 = 10             # fatal to getting the declarations/imports/exports
OK1 = 15            # have (or getting) decls/imports/exports/requires

F2 = 20           # fatal to generating a valid cache file
PROCESSING2 = 23
OK2 = 25                 # Successfully completed stage1/2a processing

F3 = 30                     # Error in accumulating package decls/etc.
PROCESSING3 = 33
OK3 = 35                 # Successfully accumulated package decls/etc.

F4 = 40                             # linkage failure, should not load
PROCESSING4 = 43
OK4 = 45                          # Successfully linked with other SPUS

WARN = None                             # A warning
