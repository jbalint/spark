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
#* "$Revision:: 128                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.parse.tokenizer import TokenStream
from spark.internal.parse.inttokenizer_common import *
from spark.internal.parse.inttokenizer_table import *

class IntTableTokenStream(TokenStream):
    def __init__(self, table, source):
        self._table = table
        self._source = source
        self._instring = source.string()
        self._index = 0
        self._start = 0
        self._prev_end = 0
        self._type = None
        self.next()

    def source(self):
        return self._source
    
    def type(self):
        return self._type

    def start(self):
        return self._start

    def end(self):
        return self._index

    def string(self):
        return self._instring[self._start:self._index]

    def prev_end(self):
        return self._prev_end

    def next(self):
        """set self.(start, end, type, token)"""
        instring = self._instring
        index = self._index                    # index into input string
        table = self._table          # local var provide faster access
        stateNum = 0                   # current state
        start = index # The index of the first consumed char for current token
        while True:                     # Loop until explicit break
            try:
                char = instring[index]
                charNum = ord(char)
            except IndexError:
                #char = None             # for debugging
                charNum = EOF_NUM

            #this won't happen if we are reading in ascii mode
            if charNum > EOF_NUM:
                action = E|ILLEGAL_CHAR
            else:
                action = table[stateNum][charNum]
            actionArg = action & ACTION_ARG_MASK
            action = action & ACTION_TYPE_MASK;
            #print "%s FOUND %r action %r actionarg %r"%(stateNum, char, {C:"C", N:"N", E:"E"}[action], actionArg)

            if action == C:
                stateNum = actionArg
                index += 1
                if actionArg == 0: # reset start when in init state
                    start = index
            elif action == E:
                index += 1
                break
            elif action == N:
                break
            else:
                raise Exception("Invalid action")
        #print "TOKEN", actionArg, repr(instring[start:index])
        # Keep a record of the end of the last token
        self._prev_end = self._index
        # Record the values for the new token
        self._index = index
        self._start = start
        self._type = actionArg
        return
