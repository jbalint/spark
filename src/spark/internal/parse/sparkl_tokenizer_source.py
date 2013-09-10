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
"""
Source table for tokenizing SPARK-L process models. This
is used as input to the auto-int-tokenizer generator (via
the generic tokenizer).

After modifying this file run the scripts
tokenizer_to_inttable.py
and
tokenizer_to_java.py
"""

from spark.internal.parse.sparkl_constants import SYM, CIRCUMFLEX, DOT, PREOP, BACKSLASH, \
     BAR, HASH, DQUOTE, COLON, DOLLAR

from spark.internal.parse.generic_tokenizer import tokenizerTableToString, constructTokenizerTable, _EOF, _C, _N, _E



###
# These differ in value from the inttokenizer_common constants.
# Do not import these. We rename them for convenience.
##

EOF = _EOF
C = _C
N = _N
E = _E

################################################################
# SPARKL tokens

class Token:
    def __init__(self, name, text):
        self._name = name
        self._text = text
    def __str__(self):
        return "<%s>"%self._name
    def __repr__(self):
        return self.__str__()
    def getText(self):
        return self._text
        
PREFIX_OP = Token("PREFIX_OP", "a prefix operator")
#DOT_OP = Token("DOT", "the . operator")
DELIMITER = Token("DELIMITER", "a delimiter")
UNEXPECTED_EOF = Token("UNEXPECTED_EOF", "a unexpected end of input")
BAD_TOKEN = Token("BAD_TOKEN", "a invalid token")
BAD_TOKEN_END = Token("BAD_TOKEN_END", "an incorrectly terminated token")
STRING = Token("STRING", "a string")
BAR_NAME = Token("BAR_NAME", "a quoted symbol")
TAG = Token("TAG", "a tag")
NAME = Token("NAME", "a symbol")
VARIABLE = Token("VARIABLE", "a variable")
INTEGER = Token("INTEGER", "an integer")
FLOAT = Token("FLOAT", "a float")

EOF_DELIMITER = ""

################################################################
# SPARKL tokenizer


# Characters that are ignored
WHITESPACE = " \n\t\r\f"
SIGN = "+-"
PREOP = "`,"
DIGIT = "0123456789"
OPEN = "([{"
CLOSE = ")]}"
TERM_START = DQUOTE+SIGN+DIGIT+SYM+BAR+PREOP+OPEN+DOLLAR # the start of a term
def tableSource():
    return \
    (
    ("ignore_space",
        (EOF, N, DELIMITER),            # EOF = DELIMITER ''
        (WHITESPACE, C, "ignore_space"),
        (HASH, C, "ignore_eol"),
        (DQUOTE, C, "double_quote"),
        (SIGN, C, "sign"),
        (DIGIT, C, "integer"),
        (SYM, C, "name"),
        (CIRCUMFLEX, C, "name"),
        (DOT, C, "name"),
        #(DOT, E, DOT_OP),
        (DOLLAR, C, "variable"),
        (BAR, C, "bar_name"),
        (PREOP, E, PREFIX_OP),
        (OPEN+CLOSE, E, DELIMITER),
        (None, E, BAD_TOKEN)), # character cannot start a term or space
    ("prefix_op",
        (TERM_START, N, PREFIX_OP),     # prefix
        (None, N, BAD_TOKEN_END)),      # next character cannot start a term
    ("ignore_eol",
        ("\n", C, "ignore_space"),
        (EOF, N, UNEXPECTED_EOF),       # in comment
        (None, C, "ignore_eol")),
    # string processing
    ("double_quote",
        ('"', E, STRING),
        (BACKSLASH, C, "double_quote_escape"),
        (EOF, N, UNEXPECTED_EOF),       # in string
        (None, C, "double_quote")),
    ("double_quote_escape",
        (EOF, N, UNEXPECTED_EOF),       # in string
        (None, C, "double_quote")),
    # bar tag processing
    ("bar_name",
        (BAR, E, BAR_NAME),
        (BACKSLASH, C, "bar_name_escape"),
        (EOF, N, UNEXPECTED_EOF),       # in bar name
        (None, C, "bar_name")),
    ("bar_name_escape",
        (EOF, N, UNEXPECTED_EOF),       # in bar name
        (None, C, "bar_name")),
    # number processing
    ("sign", # [+-]
        (DIGIT, C, "integer"),          # signed number
        #(COLON, E, TAG),
        (TERM_START, N, PREFIX_OP),     # prefix
        (WHITESPACE, N, NAME),          # symbol
        (None, N, BAD_TOKEN_END)),
    ("integer", # [+-]? DIGIT+
        (DIGIT, C, "integer"),
        (".", C, "frac1"),
        ("eE", C, "exp1"),
        (SYM+SIGN, N, BAD_TOKEN_END),
        (None, N, INTEGER)),
    ("frac1", # [+-]? DIGIT+ [.]
        (DIGIT, C, "frac"),
        (None, N, BAD_TOKEN_END)),
    ("frac", # [+-]? DIGIT+ [.] DIGIT
        (DIGIT, C, "frac"),
        ("eE", C, "exp1"),
        (SYM+SIGN, N, BAD_TOKEN_END),
        (None, N, FLOAT)),
    ("exp1", # [+-]? DIGIT+ ( [.] DIGIT+ )? [eE]
        (SIGN, C, "exp2"),
        (DIGIT, C, "float"),
        (None, N, BAD_TOKEN_END)),          # incomplete number
    ("exp2", # [+-]? DIGIT+ ( [.] DIGIT+ )? [eE][+-]
        (DIGIT, C, "float"),
        (None, N, BAD_TOKEN_END)),          # incomplete number
    ("float", # [+-]? DIGIT+ ([.]DIGIT+|[eE]DIGIT|[.]DIGIT+[eE]DIGIT)
        (DIGIT, C, "float"),
        (SYM+SIGN, N, BAD_TOKEN_END),
        (None, N, FLOAT)),
    # symbol/tag processing
    ("name",
        (SYM, C, "name"),
        (DOT, C, "name"),
        (SIGN, C, "name"),              # take a + or - within a name as okay
        (COLON, E, TAG),
        (None, N, NAME)),
    # variable processing
    # for now allow any combination of $ and symbol characters
    ("variable",
        (DOLLAR, C, "variable"),
        (SYM, C, "variable"),
        (None, N, VARIABLE),)
    )

SPARKLFSMTABLE = constructTokenizerTable(tableSource())

# for java/python unit test table comparison
# XXX: this is redundant table definition here
def sparklTableToString():
    return tokenizerTableToString(tableSource())
