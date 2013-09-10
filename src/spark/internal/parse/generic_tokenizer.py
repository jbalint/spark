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
from spark.internal.version import *
from spark.internal.parse.tokenizer import *
from spark.internal.parse.source import *

################################################################
# Generic tokenizer
# - The generic tokenizer is no longer used as an actual
#   tokenizer. Instead, the table generation tools are used
#   to auto-generate the code for the int-table-based tokenizer
#
# Other SPARK files SHOULD NOT import values from this file
################################################################


_NUMCHARS = 256                  # number of different values of ord(x)
_EOF = ("EOF",)                  # Marker distinguishable from a string
_EOF_NUM = _NUMCHARS                     # value to be used for ord(EOF)

DEBUG = False                # Whether to print out debugging messages

# for java/python unit testing
def enableGenericTokenizerDebug():
    DEBUG = True

_C = intern("Consume") # Consume char (part of a token) and go to state ARG
_E = intern("Emit") # Consume char, emit token ARG, and go to start state
_N = intern("NonConsumingEmit") # Ditto but don't consume char first


# for java/python unit test table comparison
def tokenizerTableToString(fsm_spec):
    retval = constructTokenizerTable(fsm_spec)
    str = ""
    i = 0
    for actions in retval:
        aidx = 0
        for act in actions:
            str = str+"tokenizerTable[%s][%s]:%s\n"%(i, aidx, act)
            aidx = aidx + 1
        i = i + 1
    return str
    
def constructTokenizerTable(fsm_spec):
    # fsm_spec is a tuple of (<statename>, <spec>, <spec>, ...)
    # where <spec> is a tuple (<chars>, <response>, <arg>)
    # <statename> is a string that names a state
    #   The name of a token is the name of the state it was emitted from
    # <chars> is either:
    #   a string containing characters to repond to,
    #   EOF to indicate end of input, or
    #   None for this response to apply to all remaining characters
    # <response> is one of the constants C, N, or E (see above)
    # <arg> is either:
    #   for response=C, the string name of the next state to enter, or
    #   for response=N or E, the token type to return
    # The first listed state is the start state.
    # Earlier <spec>s in a <fsm_spec> take precedence over later ones.

    # Construct mappings from state names to state numbers
    state_names = [spec[0] for spec in fsm_spec] # 
    name_to_num = {}
    for state_num in range(len(state_names)):
        name_to_num[state_names[state_num]] = state_num
    # construct the table entries for each state
    return [process_spec(spec, name_to_num) for spec in fsm_spec]

def process_spec(state_spec, name_to_num):
    "Construct a list, being the action to perform for each character"
    # The action for character x is given by the ord(x)'th entry
    # The action for EOF is the last entry
    name = state_spec[0]
    char_acts=[None]*(_NUMCHARS+1)
    default_is_set = False
    for (chars, action, action_arg) in state_spec[1:]:
        # Work out the destination state
        if action is _C:
            try:
                new_state_num = name_to_num[action_arg]
                act = (action, new_state_num)
            except KeyError:
                raise Exception("The state %s is not defined"%action_arg)
        elif action in (_N, _E):
            act = (action, action_arg)
        # Set the action for every relevant char
        if chars is None:
            default_is_set = True
            for i in range(_NUMCHARS+1):
                if char_acts[i] is None:
                    char_acts[i] = act
        elif chars is _EOF:
            if not (char_acts[_EOF_NUM] is None): raise AssertionError, \
                   "In state %s, EOF is already defined"%(name,)
            char_acts[_EOF_NUM] = act
        else:
            for char in chars:
                i = ord(char)
                if char_acts[i] is None:
                    char_acts[i] = act
    if not (default_is_set): raise AssertionError, \
       "No default action is set for state %s" % name
    if not (char_acts[_EOF_NUM][0] in (_N,_E)): raise AssertionError, \
           "State %s must have a N or E action on EOF" % name
    return char_acts


class TableTokenStream(TokenStream):
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
        state_num = 0                   # current state
        start = index # The index of the first consumed char for current token
        while True:                     # Loop until explicit break
            try:
                char = instring[index]
                char_num = ord(char)
            except IndexError:
                char = "<EOF>" # only used for debugging, when DEBUG is true
                char_num = _EOF_NUM

            #this won't happen if we are reading in ascii mode
            if char_num > _EOF_NUM:
                action = _C
                action_arg = Token("ILLEGAL_CHAR", "non ascii character")
            else:
                (action, action_arg) = table[state_num][char_num]

            if action is _C:
                if DEBUG:
                    if state_num == action_arg:
                        print "<Take %s>\n"%char,
                    else:
                        print "<Take %s->%s>\n"%(char, action_arg),
                state_num = action_arg
                index = index + 1
                if action_arg is 0: # reset start when in init state
                    start = index
            elif action is _E:
                if DEBUG:
                    print "<ENewTok %s:%s>\n"%(state_num, action_arg),
                index = index + 1
                break
            elif action is _N:
                if DEBUG:
                    print "<NewTok %s:%s>\n"%(state_num, action_arg),
                break
            else:
                raise Exception("Invalid action")
        # Keep a record of the end of the last token
        self._prev_end = self._index
        # Record the values for the new token
        self._index = index
        self._start = start
        self._type = action_arg
        return
