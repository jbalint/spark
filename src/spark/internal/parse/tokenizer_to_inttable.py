#!/bin/env python
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
Run this script to create inttokenizer_table.py from sparkl_tokenizer_source.py.
"""
import sys
import os.path

# determine where this file is located
try:
    __file__                            # if imported from a file
except NameError:
    __file__ = sys.argv[0]     # if called as python this_file
root = os.path.normpath(os.path.split(os.path.abspath(__file__))[0]) + "/"

sys.path.append(root + "../../..")      # ensure we can find spark.internal.etc.

from spark.internal.parse.generic_tokenizer import _C, _N, _E
from spark.internal.parse.sparkl_tokenizer_source import SPARKLFSMTABLE, Token
from spark.internal.parse.inttokenizer_common import C, N, E

def tokenizerTableToIntTable(table):
    tokens = []
    f = open(root+"tokenizer_to_inttable.header.tmpl.txt", 'r')
    header_tmpl = f.read()
    f.close()

    print "Writing file", root+"inttokenizer_table.py",
    f = open(root+"inttokenizer_table.py", 'w')
    f.write(header_tmpl)

    #generate tokens list first
    for actions in table:
        for (act, next) in actions:
            if act == _C:
                pass
            elif act == _N:
                if next not in tokens:
                    tokens.append(next)
            elif act == _E:
                if next not in tokens:
                    tokens.append(next)
            else:
                raise Error("Unrecognized state for translation"+act)
    #int table cannot handle characters > 256
    tokens.append(Token("ILLEGAL_CHAR", "non-ascii character"))

    #map token names to integer values
    tokTable = {}
    counter = 1
    for tok in tokens:
        tokTable[tok._name] = counter
        counter += 1

    #print token names to value mappings
    f.write('\n\n#TOKENS\n')
    for tok in tokens:
        f.write("%s = %s\n"%(tok._name, tokTable[tok._name]))

    token = tokens[0]
    
    f.write('\ndef token_name(token):'+
            '\n    """return a string name for the token"""'+
            '\n    if token==%s:\n        return "%s"'%(token._name, token._name))
    for tok in tokens[1:]:
        f.write('\n    elif token==%s:\n        return "%s"'%(tok._name, tok._name))
    f.write('\n    return "UNKNOWN"\n')

    f.write('\ndef token_description(token):'+
            '\n    """return a brief string describing the token"""'+
            '\n    if token==%s:\n        return "%s"'%(token._name, token.getText()))
    for tok in tokens:
        f.write('\n    elif token==%s:\n        return "%s"'%(tok._name, tok.getText()))
    f.write('\n    return "UNKNOWN"')

    #write the tokenizer table
    f.write('\n\n#TOKENIZER TABLE\n')
    f.write("INTTABLE = (\n")
    
    for actions in table:
        f.write("    (")
        for (act, next) in actions:
            if act == _C:
                actint = C
                pass
            elif act == _N:
                actint = N
                next = tokTable[next._name]
            elif act == _E:
                actint = E
                next = tokTable[next._name]
            else:
                raise Error("Unrecognized state for translation"+act)
            f.write("%s, "%(actint | next))
        f.write(" ),\n")
    f.write("    )\n") #end of table

    f.write('\n#end auto-generated content\n')
    f.close()

tokenizerTableToIntTable(SPARKLFSMTABLE)
