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
import unittest
import cPickle
from spark.internal.parse.basicvalues import *
from spark.internal.parse.constructor import coerceConstructor

class SymbolsTestCase(unittest.TestCase):

    def testVariable(self):
        assert Variable("$a") is Variable("$a")
        va = Variable("$a")
        vva = Variable("$$a")
        assert isVariable(va)
        assert va.isLocal()
        assert not va.isCaptured()
        assert vva.isCaptured()
        assert not vva.isLocal()
        self.assertEqual(va.innerVersion(), vva)
        self.assertEqual(va.outerVersion(), None)
        self.assertEqual(vva.innerVersion(), Variable("$$$a"))
        self.assertEqual(vva.outerVersion(), va)
        self.hasVS(va, "$a")
        self.hasVS(vva, "$$a")
        self.assertEqual(str(va), "$a")

    def testOrdinary(self):
        a = Symbol("a")
        assert a is Symbol("a")
        assert isSymbol(a)
        assert not a.isTag()
        assert not a.isBrace()
        assert not a.isPrefix()
        self.assertEqual(str(a), "a")
        self.assertEqual(value_str(a), "a")

    def testParts(self):
        a = Symbol("a")
        self.assertEqual(a.id, "a")
        self.assertEqual(a.modname, None)
        a_b_c_d = Symbol("a.b.c.d")
        self.assertEqual(a_b_c_d.id, "d")
        self.assertEqual(a_b_c_d.modname, "a.b.c")


    def testTag(self):
        b = Symbol("b:")
        assert b.isTag()
        assert not b.isBrace()
        assert not b.isPrefix()
        self.assertEqual(str(b), "b:")
        self.assertEqual(value_str(b), "|b:|")

    def testBrace(self):
        c = Symbol("c{}")
        assert not c.isTag()
        assert c.isBrace()
        assert not c.isPrefix()
        self.assertEqual(str(c), "c{}")
        self.assertEqual(value_str(c), "|c{}|")

    def testPrefix(self):
        c = Symbol(",#")
        assert not c.isTag()
        assert not c.isBrace()
        assert c.isPrefix()
        self.assertEqual(str(c), ",#")
        self.assertEqual(value_str(c), "|,#|")

    def testQuoted(self):
        c = Symbol("x y")
        assert not c.isTag()
        assert not c.isBrace()
        assert not c.isPrefix()
        self.assertEqual(str(c), "x y")
        self.assertEqual(value_str(c), "|x y|")
        c = Symbol("$x")
        assert not c.isTag()
        assert not c.isBrace()
        assert not c.isPrefix()
        self.assertEqual(str(c), "$x")
        self.assertEqual(value_str(c), "|$x|")

    def testEscapedQuoted(self):
        c = Symbol("x|\\y")
        assert not c.isTag()
        assert not c.isBrace()
        assert not c.isPrefix()
        self.assertEqual(str(c), "x|\\y")
        self.assertEqual(value_str(c), "|x\\|\\\\y|")

    def testNotSpecial(self):
        c = Symbol("x y:")
        assert not c.isTag()
        assert not c.isBrace()
        assert not c.isPrefix()
        c = Symbol("x y{}")
        assert not c.isTag()
        assert not c.isBrace()
        assert not c.isPrefix()

    def testStruct(self):
        self.assertEqual(f(1), f(1))
        self.hasVS(f(), "(f)")
        self.hasVS(f(1), "(f 1)")
        self.hasVS(f(1, 2, 3), "(f 1 2 3)")
        self.hasVS(t(1, 2, 3), "(|t:| 1 2 3)")
        self.hasVS(b(1, 2, 3), "{b 1 2 3}")
        self.hasVS(p(1, 2, 3), "(|+#| 1 2 3)")
        self.hasVS(p(1), "+ 1")
        self.hasVS(f(1, t(2, 3), t()), "(f 1 t: 2 3 t:)")
        self.hasVS(b(1, t(2, 3), t()), "{b 1 t: 2 3 t:}")
        mystruct = f(0,1, 2, 3, 4)
        self.assertEqual(mystruct.functor, Symbol("f"))
        self.assertEqual(mystruct[0], 0)
        self.assertEqual(mystruct[4], 4)
        self.assertEqual(mystruct[-1], 4)
        self.assertEqual(mystruct[1:3], createList(1, 2))
        
    def testInverseEval(self):
        self.hasIEVS(1, '1')
        self.hasIEVS("x", '"x"')
        self.hasIEVS(1.0, '1.0')
        abc = Symbol("abc")
        self.hasIEVS(abc, '`abc')
        self.hasIEVS(l(1, abc), '[1 `abc]')
        self.hasIEVS(f(1, abc), '`(f 1 abc)')
        self.hasIEVS(f(1, l(abc)), '`(f 1 ,[`abc])')

    def hasIEVS(self, x, s):
        self.assertEqual(value_str(inverse_eval(x)), s)
        

    def testList(self):
        self.assertEqual(l(1), l(1))
        self.hasVS(l(), "[]")
        self.hasVS(l(1), "[1]")
        self.hasVS(l(1, 2), "[1 2]")
        self.hasVS(l(1, t(2, 3), t()), "[1 t: 2 3 t:]")
        
    def hasVS(self, x, y):
        self.assertEqual(value_str(x), y)

    def testPickle(self):
        self.pickleTest(1,
                        'K\x01.')
        self.pickleTest(Symbol("abc"),
                        'cspark.internal.parse.values\n__Symbol\nq\x01(U\x03abcq\x02tq\x03Rq\x04.')
        self.pickleTest(f("abc", "def", f()),
                        'cspark.internal.parse.values\n__Structure\nq\x01(cspark.internal.parse.values\n__Symbol\nq\x02(U\x01fq\x03tq\x04Rq\x05(U\x03abcq\x06U\x03defq\x07h\x01(h\x05)tq\bRq\ttq\ntq\x0BRq\f.')
        self.pickleTest(l("aaa", "bbb", "ccc"),
                        '(U\x03aaaq\x01U\x03bbbq\x02U\x03cccq\x03tq\x04.')
        self.pickleTest(Variable("$x"),
                        'cspark.internal.parse.values\n__Variable\nq\x01(U\x02$xq\x02tq\x03Rq\x04.')
        
    def pickleTest(self, obj, pstring):
        print "Pickling", value_str(obj)
        s = cPickle.dumps(obj, -1)
        print " string=%r"%s
        y = cPickle.loads(s)
        self.assertEqual(obj, y)
        if not s.startswith('\x80\x02'):
            # Java pickling
            self.assertEqual(s, pstring)
        
    def testValueConversion(self):
        # Convert between values using two different constructors
        self.mainConversion(PVC)
        self.capturedVariableConversion(PVC)

    def testExprConversion(self):
        from spark.internal.parse.expr import EXPR_CONSTRUCTOR
        self.mainConversion(EXPR_CONSTRUCTOR)
        self.capturedVariableConversion(EXPR_CONSTRUCTOR)

    def testICLConversion(self):
        try:
            from com.sri.oaa2.icl import IclTerm
        except ImportError:
            print "Cannot find the OAA libraries, so we will skip the ICL tests"
            return
        from spark.io.oaa import ICL_CONSTRUCTOR
        self.mainConversion(ICL_CONSTRUCTOR)

        
    def mainConversion(self, pcon):
        VC = VALUE_CONSTRUCTOR
        self.auxConversion(VC, pcon, 1)
        self.auxConversion(VC, pcon, 1.0)
        self.auxConversion(VC, pcon, "1")
        self.auxConversion(VC, pcon, A)
        self.auxConversion(VC, pcon, VA)
        self.auxConversion(VC, pcon, f(1, 1.0, "1", A, VA))
        self.auxConversion(VC, pcon, l())
        self.auxConversion(VC, pcon, l(1, 1.0, "1", A, VA))
        # The unambiguous mapping of variables is very hard going between SPARK and ICL
        self.auxConversion(VC, pcon, Variable("$A"))
        self.auxConversion(VC, pcon, Variable("$a"))
        self.auxConversion(VC, pcon, Variable("$0"))
        self.auxConversion(VC, pcon, Variable("$_"))
        self.auxConversion(VC, pcon, Variable("$_A"))
        self.auxConversion(VC, pcon, Variable("$_a"))
        self.auxConversion(VC, pcon, Variable("$_0"))

    def capturedVariableConversion(self, pcon):
        VC = VALUE_CONSTRUCTOR
        self.auxConversion(VC, pcon, Variable("$$A"))
        self.auxConversion(VC, pcon, Variable("$$a"))
        self.auxConversion(VC, pcon, Variable("$$0"))
        self.auxConversion(VC, pcon, Variable("$$_1"))

    def auxConversion(self, fromCon, toCon, value):
        newval = coerceConstructor(toCon, fromCon, value)
        newnewval = coerceConstructor(fromCon, toCon, newval)
        self.assertEqual(value, newnewval)

def l(*args):
    return List(args)

def f(*args):
    return Symbol("f").structure(*args)

def t(*args):
    return Symbol("t:").structure(*args)

def b(*args):
    return Symbol("b{}").structure(*args)

def bq(x):
    return Symbol("`#").structure(x)
def comma(x):
    return Symbol(",#").structure(x)
def p(*args):
    return Symbol("+#").structure(*args)

A = Symbol("a")
VA = Variable("$a")

#CLASSPATH="../lib/spark.jar" PYTHONPATH=. ~/jython/jython spark/internal/parse/basicvalues_test.py

################################################################
# Constructing these values using sparkl_parser
from spark.internal.parse.constructor import Constructor, INTEGER, STRING, FLOAT, VARIABLE, SYMBOL, STRUCTURE, LIST

class _ValueConstructor(Constructor):
    def createSymbol(self, start, end, string):
        return Symbol(string)
    def createVariable(self, start, end, string):
        return Variable(string)
    def createStructure(self, start, end, functor_name, args):
        return Structure(Symbol(functor_name), args)
    def createList(self, start, end, elements):
        return List(elements)
    def createString(self, start, end, string):
        return String(string)
    def createInteger(self, start, end, integer):
        return Integer(integer)
    def createFloat(self, start, end, float):
        return Float(float)
    def start(self, obj):
        return -1
    def end(self, obj):
        return -1
    def asFloat(self, obj):
        if isFloat(obj):
            return obj
        else:
            raise ValueError("Not a float: %r"%obj)

    def asInteger(self, obj):
        if isInteger(obj):
            return obj
        else:
            raise ValueError("Not an integer: %r"%obj)

    def category(self, object):
        if isString(object):
            return STRING
        elif isInteger(object):
            return INTEGER
        elif isFloat(object):
            return FLOAT
        elif isSymbol(object):
            return SYMBOL
        elif isStructure(object):
            return STRUCTURE
        elif isList(object):
            return LIST
        elif isVariable(object):
            return VARIABLE
        else:
            raise ValueError("Not a valid object")

    def functor(self, obj):
        if isStructure(obj):
            return obj.functor.name
        else:
            return None

    def asString(self, obj):
        if isString(obj):
            return obj
        elif isVariable(obj):
            return obj.name
        elif isSymbol(obj):
            return obj.name
        else:
            return None
    
    def components(self, obj):
        if isList(obj):
            return obj
        elif isStructure(obj):
            return tuple(obj)
        else:
            return None

PVC = _ValueConstructor()

################################################################

if __name__ == "__main__":
    unittest.main()
    

################################################################
# For running with the ICL tests
# java -Dpython.home="/Users/morley/aic/jython/trunk/jython/dist" -classpath "../lib/spark.jar:/Users/morley/aic/jython/trunk/jython/dist/jython.jar" -Djava.ext.dirs="../lib/oaa2.3.1" org.python.util.jython spark/internal/parse/basicvalues_test.py
# in the src directory of SPARK
