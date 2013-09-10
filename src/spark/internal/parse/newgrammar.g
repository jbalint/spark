#*****************************************************************************#
#* Copyright (c) 2004, SRI International.                                    *#
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
import re

from spark.internal.version import *
from spark.internal.repr.newterm import *
from spark.internal.exception import error

### NOTE: cannot have (x | {{ y }})

_escapepattern=re.compile(r'\\.', re.DOTALL)
_crpattern=re.compile('\r')
_escapes={"\\\\":"\\", '\\"':'"', "\\|":"|", "\\n":"\n", "\\r":"\r", "\\t":"\t", "\\\n":""}                
def parsestring(string):
    "Take a string representing a string and return the string it represents"
    string1 = _crpattern.sub('',string) # remove carriage return characters
    return _escapepattern.sub(_parsestring_aux, string1[1:-1])

def _parsestring_aux(matchobj):
    "Function to replace an escape sequence in a string"
    thing = matchobj.group(0)
    return _escapes.get(thing,thing) 
       
%%

parser SPARK:
	option:		"context-insensitive-scanner"

	ignore:		r'\s+'
	ignore:		r'[#][^\n]*\n'
	token END:	r'$'

	token STRING:	r'"([^\\"]+|\\.)*"'
	token FLOAT:	r'[-+]?[0-9]+\.[0-9]+([eE][+|-]?[0-9]+)?'
	token INTEGER:	r'[-+]?[0-9]+'
#	token BAR:	r'\|'
	token TAG:	r'((?!\d)\w+\.)*(?!\d)\w+:'
	token NAME:	r'((?!\d)\w+\.)*((?!\d)\w+|[-+*/%^&@|!?<>=]+)'
	token VARNAME:	r'[$]+(?!\d)\w+'

	token OPEN_BRACKET:	r'\['
	token CLOSE_BRACKET:	r'\]'
	token OPEN_BRACE:	r'\{'
	token CLOSE_BRACE:	r'\}'
	token OPEN_PAREN:	r'\('
	token CLOSE_PAREN:	r'\)'

	token BAD_TOKEN:	r'[^\s#]'
    token BAR_NAME: ""
    token BAR_TAG: ""
    token BACK_QUOTE: ""

rule path:
        ( NAME {{ return PathTerm(_, NAME) }}
        | BAR_NAME {{ return PathTerm(_, parsestring(BAR_NAME)) }}
        )

rule paths:
        {{ r = [] }} ( path {{ r.append(path) }} )* {{ return r }}

rule reqpath:
        ( path {{ return path }}
        | error<<_, "where a path is required">>
        )

rule paren_expr:
        (OPEN_PAREN reqpath terms taggeditems 
            ( CLOSE_PAREN {{ return ParenTerm(_, [reqpath]+terms + taggeditems) }}
            | error<<_, "while parsing a parenthesized term">>
            )
        |   BACK_QUOTE {{ functor = PathTerm(_, "`") }}
            ( term {{ return ParenTerm(_, [functor, term]) }}
            | error<<_, "when expecting a term">>
            )
        )

rule brace_expr:
	OPEN_BRACE reqpath terms taggeditems 
	( CLOSE_BRACE {{ return BraceTerm(_, [reqpath]+terms + taggeditems) }}
	| error<<_, "while parsing a braced term">>
	)

rule bracket_expr:
	OPEN_BRACKET terms taggeditems
	( CLOSE_BRACKET {{ return BracketTerm(_, terms + taggeditems) }}
	| error<<_, "while parsing a list">>
	)

rule tag:
        ( TAG {{ return TagTerm(_, TAG) }}
        | BAR_TAG {{ return TagTerm(_, parsestring(BAR_TAG[:-1])+":") }}
        )

rule term:
	( paren_expr {{ return paren_expr }}
	| bracket_expr {{ return bracket_expr }}
	| brace_expr {{ return brace_expr }}
	| path {{ return path }}
	| STRING {{ return StringTerm(_, parsestring(STRING)) }}
	| INTEGER {{ return IntegerTerm(_, int(INTEGER)) }}
	| FLOAT {{ return FloatTerm(_, float(FLOAT)) }}
	| VARNAME {{ return VariableTerm(_, VARNAME) }}
	)

rule terms:
	{{ r = [] }} ( term {{ r.append(term) }} )* {{ return r }}

rule taggeditem:
        tag terms {{ return TaggedItem(_, [tag]+terms) }}

rule taggeditems:
        {{ r = [] }} ( taggeditem {{ r.append(taggeditem) }} )* {{ return r }}

rule statement:
        ( tag paths {{ return TaggedItem(_, [tag]+paths) }}
        | brace_expr {{ return brace_expr }}
        | paren_expr {{ return paren_expr }}
        )

rule main:
        {{ r = [] }}
        ( statement {{ r.append(statement) }} )*
        end<<"while looking for a statement">>
        {{ return r }}

rule term_end:
        ( term end<<"at the end of the term">> {{ return term }}
        | error<<_,"while looking for a term">>
        )

rule end<<string>>:
	( END
	| error<<_, string>>
	)

rule error<<c, s>>:
	( END {{ error(c, c, s, "end of input") }}
	| STRING {{ error(c, _, s, "a string literal") }}
	| FLOAT {{ error(c, _, s, "a float literal") }}
	| INTEGER {{ error(c, _, s, "an integer literal") }}
	| TAG {{ error(c, _, s, "a tag %s"%TAG) }}
	| NAME {{ error(c, _, s, "a path") }}
	| VARNAME {{ error(c, _, s, "a variable") }}
	| OPEN_BRACKET {{ error(c, _, s, "a list") }}
	| CLOSE_BRACKET {{ error(c, _, s, "a list terminator") }}
	| OPEN_BRACE {{ error(c, _, s, "a braced term") }}
	| CLOSE_BRACE {{ error(c, _, s, "a closing brace") }}
	| OPEN_PAREN {{ error(c, _, s, "a parenthesized term") }}
	| CLOSE_PAREN {{ error(c, _, s, "a closing parenthesis") }}
	| BAD_TOKEN {{ error(c, _, s, "an unrecognized token '%s'"%BAD_TOKEN) }}
	)

%%

