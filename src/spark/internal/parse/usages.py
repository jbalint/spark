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

################################################################
# usage of expressions      

STAGE_ONE_KIND = "1"
TERM_EVAL = "+"
TERM_MATCH = "-"
PRED_SOLVE = "s"
PRED_UPDATE = "u"
PRED_RETRACTALL = "r"
PRED_ACHIEVE = "a"
ACTION_DO = "d"
TASK_EXECUTE = "x"
#STATEMENT = "z"
QUOTED_EVAL = "q"
QUOTED_MATCH = "k"
ENTITY = "j"                            # like q but must be declared
#NULL_KIND = " "
VARLIST = "v"                           # variable or list of variables
CUE_LIST = "l"
CUE = "c"
#SIGNATURE = "v"
FORMALS = "f"
FORMAL = "g"

LOADTIME = "L"
RUNTIME = "R"

DECLARATION = "D"

WEAKSYM = "%"
REQSYM = "="
REPSYM = "*"
KEYSYM = ":"
ENDSYM = "/"

SEPARATORS = (WEAKSYM, REQSYM, REPSYM, KEYSYM, ENDSYM)

_REQ_USAGE_PRINTABLE_NAME = {TERM_EVAL:("an evaluable term", "an evaluable function"),
                         TERM_MATCH:("a matchable term","a matchable function"),
                         PRED_SOLVE:("a solvable logical expression","a solvable predicate"),
                         PRED_UPDATE:("an updatable logical expression","an updatable predicate"),
                         PRED_RETRACTALL:("a retractable logical expression","a retractable predicate"),
                         PRED_ACHIEVE:("an achievable logical expression","an achievable predicate"),
                         ACTION_DO:("an action","an action"),
                         TASK_EXECUTE:("a task network expression", "???"),
                         #STATEMENT:"a valid statement",
                         QUOTED_EVAL:("an evaluable quoted term", "???"),
                         QUOTED_MATCH:("a matchable quoted term", "???"),
                         ENTITY:("an id", "???"),
                         VARLIST:("a variable or list of variables", "???"),
                         STAGE_ONE_KIND:("a statement", "???"),
                         CUE_LIST:("a list that can be used as a cue", "???"),
                         CUE:("a cue element", "???"),
                         FORMALS:("a formal parameters specification", "a declared entity"),
                         FORMAL:("a single formal parameter specification", "???"),
                         LOADTIME:("executed at load time", "???"),
                         RUNTIME:("executed at run time", "???"),
                         DECLARATION:("a declaration template", "???")
                            }
def reqUsagePrintableName(x):
    return _REQ_USAGE_PRINTABLE_NAME[x][0]

def reqUsagePrintableFunctorName(x):
    return _REQ_USAGE_PRINTABLE_NAME[x][1]


_WEAKER_USAGES_DICT = {STAGE_ONE_KIND:(PRED_UPDATE, PRED_RETRACTALL),
                       TERM_EVAL:(TERM_MATCH,),
                       QUOTED_EVAL:(QUOTED_MATCH,),
                       PRED_UPDATE:(PRED_RETRACTALL,)}

def usageIsWeakerOrSame(usage1, usage2):
    "usage1 is satisfied by anything that satisfies usage2"
    # If a term is evaluable, then you can always match it
    return (usage1 == usage2) or usage1 in _WEAKER_USAGES_DICT.get(usage2, "")
