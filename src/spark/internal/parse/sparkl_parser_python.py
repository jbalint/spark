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
import re
from spark.internal.version import *

from spark.internal.parse.source import Source, FileSource
from spark.internal.parse.sparkl_constants import *
#from spark.internal.parse.inttokenizer_common import C, N, E, EOF_DELIMITER
#from spark.internal.parse.inttokenizer_table import *
from spark.internal.parse.inttokenizer import *
from spark.internal.parse.constructor import Constructor
from spark.internal.common import DEBUG
from spark.internal.exception import ParseError

debug = DEBUG(__name__)

################################################################
# SPARKL parser

_escapepattern=re.compile(r'\\.', re.DOTALL)

_crpattern=re.compile('\r')

_escapes={"\\\\":"\\", '\\"':'"', "\\|":"|", "\\n":"\n", \
          "\\r":"\r", "\\t":"\t", "\\\n":""}                

def unquote(string):
    """Take the delimiters off a string and process \-escapes."""
    string1 = _crpattern.sub('',string) # remove carriage return characters
    return _escapepattern.sub(_parsestring_aux, string1[1:-1])

def _parsestring_aux(matchobj):
    "Function to replace an escape sequence in a string"
    thing = matchobj.group(0)
    return _escapes.get(thing,thing) 

SPARKLTABLE = INTTABLE

class SPARKLTokenizer(IntTableTokenStream):
    def __init__(self, source):
        IntTableTokenStream.__init__(self, SPARKLTABLE, source)

PREFIX_OP_SYMNAME = {"`":"`#", ",":",#", "+":"+#", "-":"-#"}

    
def parseSPARKL(sourceText, sourceName, constructor):
    source = Source(sourceName, sourceText)
    tok = SPARKLTokenizer(source)
    parser = SPARKLParser(constructor, tok)
    return parser.terms_and_taggeds(True, EOF_DELIMITER, "end of input")

class SPARKLParser:
    def __init__(self, con, tok):
        self._tok = tok
        self._con = con

    def syntax_or_expecting_error(self, expected):
        if self._tok.type() == ILLEGAL_CHAR:
            return self.syntax_error()
        else:
            return self.expecting_error(expected)
        
    def expecting_error(self, expected):
        "Return an exception for when you expected something else to appear."
        pos = self._tok.start()
        end = self._tok.end()
        expect_msg = "Found %s when expecting %s." \
                     %(token_description(self._tok.type()), expected)
        msg = self._tok.source().msg_string(pos,end,"^",expect_msg)
        return ParseError(msg)

    def syntax_error(self):
        "Return an exception for when you expected something else to appear."
        tok = self._tok
        msg = tok.source().msg_string(tok.start(),tok.end(),"^","Illegal character/syntax")
        return ParseError(msg)

    def at_end(self):
        """Return whether the parser has reached the end of the input"""
        tok = self._tok
        return tok.type() is DELIMITER and tok.string() == EOF_DELIMITER

    def term(self, atomic_only):
        """If the following tokens can be interpreted as a term,
        then return that term, otherwise return None and consume no tokens,
        or if you have consumed tokens, raise an exception.
        If atomic_only is True, then do not allow compound structures."""
        tok = self._tok
        con = self._con
        start = tok.start()
        end = tok.end()
        type = tok.type()
        str = tok.string()
        result = None
        debug("Calling term, next = %r", str)
        if type is NAME:
            tok.next()
            result = con.createSymbol(start, end, str)
#             if str.startswith(CIRCUMFLEX):
#                 result = con.createReference(start, end, str)
#             else:
#                 result = con.createSymbol(start, end, str)
        elif type is BAR_NAME:
            tok.next()
            result = con.createSymbol(start, end, unquote(str))
        elif type is STRING:
            tok.next()
            result = con.createString(start, end, unquote(str))
        elif type is INTEGER:
            tok.next()
            try:
                val = int(str)
            except ValueError:          # needed for Python 2.2 and below
                val = long(str)
            result = con.createInteger(start, end, val)
        elif type is VARIABLE:
            tok.next()
            result = con.createVariable(start, end, str)
        elif type is FLOAT:
            tok.next()
            result = con.createFloat(start, end, float(str))
        elif atomic_only and not (type is DELIMITER and str == "["):
            return None
        elif type is PREFIX_OP:
            symname = PREFIX_OP_SYMNAME[str]
            tok.next()
            arg = self.term(False)
            if arg is None:
                raise self.expecting_error("a term as an argument for the operator")
            result = con.createStructure(start, tok.prev_end(), symname, [arg])
        elif type is DELIMITER:
            if str == "(":
                tok.next()
                ftype = tok.type()
                if ftype is NAME:
                    name = tok.string()
                elif ftype is BAR_NAME:
                    name = unquote(tok.string())
                else:
                    raise self.expecting_error("a symbol or quoted symbol as functor")
                tok.next()
                args = self.terms_and_taggeds(False, ")", "')'")
                result = con.createStructure(start,tok.prev_end(),name,args)
            elif str == "{":
                tok.next()
                ftype = tok.type()
                if ftype is NAME:
                    name = tok.string()+"{}"
                    tok.next()
                    args = self.terms_and_taggeds(False, "}", "'}'")
                    result = con.createStructure(start, tok.prev_end(), name, args)
                else:
                    raise self.expecting_error("an unquoted symbol as functor")
            elif str == "[":
                tok.next()
                elements = self.terms_and_taggeds(atomic_only, "]", "']'")
                result = con.createList(start, tok.prev_end(), elements)
            else:
                debug("Unknown delimiter, returning None: %r", str)
                return None
        else:
            debug("Unknown type, returning None: %r", str)
            return None
        #while tok.type() is DOT_OP:
        #    functor = con.createSymbol(tok.start(), tok.end(), tok.string())
        #    tok.next()
        #    if tok.type() is not NAME:
        #        raise self.expecting_error("an unquoted symbol as attribute name")
        #    end1 = tok.end()
        #    sym = con.createSymbol(tok.start(), end1, tok.string())
        #    result = con.createStructure(start, end1, functor, (result, sym))
        #    tok.next()
        debug("term returning value")
        return result

    def tagged(self, atomic_only):
        """If the following tokens can be interpreted as a tag
        followed by term, then return a structure with that tag as
        functor and the terms as arguments, otherwise return None and
        consume no tokens, or if you have consumed tokens, raise an
        exception.  If atomic_only is True, then do not allow compound
        terms arguments."""
        tok = self._tok
        if tok.type() is TAG:
            start = tok.start()
            name = tok.string()
            tok.next()
            args = []
            arg = self.term(atomic_only)
            while arg is not None:
                args.append(arg)
                arg = self.term(atomic_only)
            return self._con.createStructure(start, tok.prev_end(), name, args)
        else:
            return None

    def terms_and_taggeds(self, atomic_only, delimiter_string, message):
        """Collect terms and taggeds up to and including terminator.
        If atomic_only is True, only allow atomic arguments in the taggeds.
        Compound terms are always allowed at the top level."""
        args = []
        arg = self.term(False)
        if arg is None:
            arg = self.tagged(atomic_only)
        while arg is not None:
            args.append(arg)
            arg = self.term(False)
            if arg is None:
                arg = self.tagged(atomic_only)
        tok = self._tok
        if tok.type() != DELIMITER or tok.string() != delimiter_string:
            raise self.syntax_or_expecting_error(message)
        tok.next()
        return args
            

################################################################

class PythonConstructor(Constructor):
    """Example constructor that constructs native Python objects"""
    def createSymbol(self, start, end, string):
        return "@"+string
#     def createReference(self, start, end, string):
#         return string
    def createVariable(self, start, end, string):
        return string
    def createStructure(self, start, end, functor, args):
        return (functor,) + tuple(args)
    def createList(self, start, end, elements):
        return list(elements)
    def createString(self, start, end, string):
        return string
    def createInteger(self, start, end, integer):
        return integer
    def createBigInteger(self, start, end, integer):
        return integer
    def createFloat(self, start, end, float):
        return float

class TestConstructor(Constructor):
    """Test constructor for comparing execution trace with Java implementation"""
    buff = ""
    
    def createSymbol(self, start, end, string):
        self.buff = self.buff + "createSymbol(%s,%s,%s)\n"%(start, end, string)
        return string
    def createStructure(self, start, end, functor_str, args):
        self.buff = self.buff + "createStructure(%s,%s)\n"%(start, end)
        return functor_sym
    def createList(self, start, end, elements):
        self.buff = self.buff + "createList(%s,%s,%s)\n"%(start, end, len(elements))
        return elements
    def createString(self, start, end, string):
        self.buff = self.buff + "createString(%s,%s,%s)\n"%(start, end, string)
        return string
    def createInteger(self, start, end, integer):
        self.buff = self.buff + "createInteger(%s,%s,%s)\n"%(start, end, integer)
        return integer
    def createBigInteger(self, start, end, integer):
        self.buff = self.buff + "createBigInteger(%s,%s,%s)\n"%(start, end, integer)
        return integer
    def createFloat(self, start, end, float):
        self.buff = self.buff + "createFloat(%s,%s,%s)\n"%(start, end, float)
        return float

PYTHON_CONSTRUCTOR = PythonConstructor()

################################################################
# JAVA UNIT TESTING ADDITIONAL METHODS

TEST_CONSTRUCTOR = TestConstructor()

#for java unit testing
def getTestConstructorDebug():
    return TEST_CONSTRUCTOR.buff
#for java unit testing
def clearTestConstructorDebug():
    TEST_CONSTRUCTOR.buff = ""

def testRunStringExample(sparkl_src):
    source = Source("string", sparkl_src) 
    tok = SPARKLTokenizer(source)
    parser = SPARKLParser(TEST_CONSTRUCTOR, SPARKLTokenizer(source))
    return parser.terms_and_taggeds(True, EOF_DELIMITER, "end of input")

def testRunFileExample(sparkl_src):
    source = FileSource(sparkl_src)
    tok = SPARKLTokenizer(source)
    parser = SPARKLParser(TEST_CONSTRUCTOR, SPARKLTokenizer(source))
    return parser.terms_and_taggeds(True, EOF_DELIMITER, "end of input")
    
################################################################
    
def main():
    filename = "/Users/morley/aic/spark/beta/src/spark/lang/builtin.spark"
    #filename = r"c:\projects\spark\src\spark\lang\builtin.spark"
    string = 'a: b (c d 1 "2") {e [3.0] f: +g}'
    source = Source("string", string)
    tok = SPARKLTokenizer(source)
    #con = PYTHON_CONSTRUCTOR
    con = TEST_CONSTRUCTOR
    parser = SPARKLParser(con, SPARKLTokenizer(source))
    retval = parser.terms_and_taggeds(True, EOF_DELIMITER, "end of input")

    from spark.internal.parse.basicvalues import VALUE_CONSTRUCTOR
    parser = SPARKLParser(VALUE_CONSTRUCTOR, SPARKLTokenizer(source))
    retval = parser.terms_and_taggeds(True, EOF_DELIMITER, "end of input")

    print "parsing builtin.spark"
    parser = SPARKLParser(con, SPARKLTokenizer(FileSource(filename)))
    retval = parser.terms_and_taggeds(True, EOF_DELIMITER, "end of input")
    print "done with sparkl_parser.main()"    

if __name__ == "__main__":
    main()
    
def parse(x):                           # seems to be unused
    from spark.internal.parse.basicvalues import VALUE_CONSTRUCTOR
    parser = SPARKLParser(VALUE_CONSTRUCTOR, SPARKLTokenizer(Source("string", x)))
    return parser.terms_and_taggeds(True, EOF_DELIMITER, "end of input")
