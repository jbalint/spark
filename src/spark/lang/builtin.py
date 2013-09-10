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
#* "$Revision:: 244                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from __future__ import generators
"""This Python module declares the SPInternal ARK module spark.builtin.
It contains all the standard language symbols (and, or, not, etc.).
This SPARK module is always imported.
"""
from spark.internal.version import *
from spark.internal.exception import ProcessingError
from spark.internal.parse.processing import Imp
from spark.internal.common import tuple_repr, DEBUG, SOLVED, NOT_SOLVED, ONE_SOLUTION, NO_SOLUTIONS, POSITIVE, NEWPM
from spark.internal.parse.basicvalues import *
from spark.internal.parse.expr import ExprString, ExprSymbol, ExprInteger, ExprList, ExprVariable, ExprStructure, ExprCompound
from spark.internal.parse.usagefuns import *
from spark.internal.parse.usages import *
from spark.internal.repr.varbindings import valuesBZ
from spark.internal.exception import NoProcedureFailure, UnlocatedError
from spark.internal.repr.common_symbols import *
from spark.pylang.simpleimp import *
from spark.internal.engine.find_module import ensure_modpath_installed
from spark.internal.debug.trace import TRACING

debug = DEBUG(__name__)
################################################################
class TermIf(Imp):
    __slots__ = ()

    def call(self, agent, bindings, zexpr):
        if predSolve1(agent, bindings, zexpr[0]):
            return termEvalErr(agent, bindings, zexpr[1])
        else:
            return termEvalErr(agent, bindings, zexpr[2])

    def match_inverse(self, agent, bindings, zexpr, obj):
        if predSolve1(agent, bindings, zexpr[0]):
            return termMatch(agent, bindings, zexpr[1], obj)
        else:
            return termMatch(agent, bindings, zexpr[2], obj)


# class Solutions(Imp):
#     __slots__ = ()

#     def call(self, agent, bindings, zexpr):
#         solutions = []
#         for x in predSolve(agent, bindings, zexpr[1]):
#             if x:
#                 solutions.append(termEvalErr(agent, bindings, zexpr[0]))
#         #solutions.sort()
#         #delete_repetitions(solutions)
#         return List(solutions)

#     def match(self, agent, bindings, zexpr, obj):
#         return self.call(agent, bindings, zexpr) == obj

        
class SolutionsPat(Imp):
    __slots__ = ()

    def call(self, agent, bindings, zexpr):
        solutions = []
        for x in predSolve(agent, bindings, zexpr[1]):
            if x:
                solutions.append(termEvalErr(agent, bindings, zexpr[2]))
        return List(solutions)

    def match_inverse(self, agent, bindings, zexpr, obj):
        return self.call(agent, bindings, zexpr) == obj
        
        
class ExtensionSolutionsCollector(Imp):
    __slots__ = (
        "_solutions",
        )

    def __init__(self, solutions):
        self._solutions = solutions
    #XXX:TODO:PERSIST NEED TO MAKE THIS PERSISTABLE
    
    def pred_imp(self, agent):
        return self

    def solutions(self, agent, bindings, zexpr):
        #possibly not-optimal as it iterates through
        #our internal list of solutions, one-by-one, rather
        #than cleverly indexing.  would be bad if
        #there is a large solution set.  I'm not sure
        #yet what the common case is (large vs. small)
        for soln in self._solutions:
            #print "checking: ", soln
            i = 0
            for x in soln:
                if termMatch(agent, bindings, zexpr[i], x):
                    i = i + 1
                else:
                    break
            else:
                #print "found solution: ", soln
                yield SOLVED

    def conclude(self, agent, bindings, zexpr): # TODO: check this DNM
        return False

    def retractall(self, agent, bindings, zexpr): # TODO: check this DNM
        return False

# TODO: following is not updated to new implementation
class SolutionsPred(Imp):
    __slots__ = ()

    def call(self, agent, bindings, expr):
        solutions = []
        for x in predSolve(agent, bindings, expr[0]):
            if x:
                solutions.append(termEvalErr(agent, bindings, expr[1]))
        #solutions.sort()
        #delete_repetitions(solutions)
        return ExtensionSolutionsCollector(solutions)
        

################################################################

class Equality(Imp, PredImpInt):
    __slots__ = ()

    def solution(self, agent, bindings, zexpr):
        arg0 = termEvalOpt(agent, bindings, zexpr[0])
        if arg0 is None:
            arg1 = termEvalErr(agent, bindings, zexpr[1])
            if termMatch(agent, bindings, zexpr[0], arg1):
                return SOLVED
            else:
                return NOT_SOLVED
        else:
            if termMatch(agent, bindings, zexpr[1], arg0):
                return SOLVED
            else:
                return NOT_SOLVED

################
# truth

class PredTrue(Imp):
    __slots__ = ()

    def solution(self, agent, bindings, zexpr):
        return SOLVED

    def solutions(self, agent, bindings, zexpr):
        return ONE_SOLUTION
    

class PredFalse(Imp):
    __slots__ = ()

    def solution(self, agent, bindings, zexpr):
        return NOT_SOLVED

    def solutions(self, agent, bindings, zexpr):
        return NO_SOLUTIONS
    


class funTrue(Imp):
    __slots__ = ()

    def call(self, agent, bindings, zexpr):
        return True

    def match_inverse(self, agent, bindings, zexpr, obj):
        return obj == True
    

class funFalse(Imp):
    __slots__ = ()

    def call(self, agent, bindings, zexpr):
        return False

    def match_inverse(self, agent, bindings, zexpr, obj):
        return obj == False

################################################################
# Conjunction

class And(Imp):
    __slots__ = ()

    def solutions(self, agent, bindings, zexpr):
        return self.solutions_aux(agent, bindings, zexpr, 0)

    def solutions_aux(self, agent, bindings, zexpr, index):
        l = len(zexpr)
        if index < l - 1:
            return self.solutions_gen(agent, bindings, zexpr, index)
        elif index == l:
            return ONE_SOLUTION
        else:                           # index == l - 1:
            return predSolve(agent, bindings, zexpr[index])

    def solutions_gen(self, agent, bindings, zexpr, index):
        for x in predSolve(agent, bindings, zexpr[index]):
            if x:
                for y in self.solutions_aux(agent, bindings, zexpr, index+1):
                    yield y

    def solution(self, agent, bindings, zexpr):
        return self.solution_aux(agent, bindings, zexpr, 0)

    def solution_aux(self, agent, bindings, zexpr, index):
        l = len(zexpr)
        if index < l - 1:
            return self.solution_test(agent, bindings, zexpr, index)
        elif index == l:
            return SOLVED
        else:                           # index == l - 1:
            return predSolve1(agent, bindings, zexpr[index])

    def solution_test(self, agent, bindings, zexpr, index):
        for x in predSolve(agent, bindings, zexpr[index]):
            if x == SOLVED and self.solution_aux(agent, bindings, zexpr, index+1):
                return SOLVED
        return NOT_SOLVED

    def conclude(self, agent, bindings, zexpr):
        for zitem in zexpr:
            predUpdate(agent, bindings,  zitem)

################################################################
# Diagnostic tracing predicate

class PTrace(Imp):
    __slots__ = ()
        
    def solution(self, agent, bindings, zexpr):
        print "PTRACE STARTING: %s" % termEvalErr(agent, bindings, zexpr[0])
        predexpr = zexpr[1]
        TRACING.do_try(agent, bindings, predexpr)
        if predSolve1(agent, bindings, predexpr):
            TRACING.do_succeed(agent, bindings, predexpr)

    def solutions(self, agent, bindings, zexpr):
        print "PTRACE STARTING: %s" % termEvalErr(agent, bindings, zexpr[0])
        predexpr = zexpr[1]
        TRACING.do_try(agent, bindings, predexpr)
        for x in predSolve(agent, bindings, predexpr):
            if x:
                TRACING.do_succeed(agent, bindings, predexpr)
                yield x
                TRACING.do_retry(agent, bindings, predexpr)
        TRACING.do_fail(agent, bindings, predexpr)


class Once(Imp):
    __slots__ = ()

    def solution(self, agent, bindings, zexpr):
        return predSolve1(agent, bindings, zexpr[0])

    def solutions(self, agent, bindings, zexpr):
        if predSolve1(agent, bindings, zexpr[0]):
            return ONE_SOLUTION
        else:
            return NO_SOLUTIONS
            

################################################################
# Disjunction

class Or(Imp):
    __slots__ = ()

    def solution(self, agent, bindings, zexpr):
        for zitem in zexpr:
            if predSolve1(agent, bindings, zitem):
                return SOLVED
        return NOT_SOLVED

    def solutions(self, agent, bindings, zexpr):
        for zitem in zexpr:
            for x in predSolve(agent, bindings, zitem):
                yield x

    # WE COULD RETRACT A DISJUNCTION PRETTY EASILY, BUT IGNORE IT FOR NOW
    
################################################################
# Negation as failure to prove
    
class Not(Imp):
    __slots__ = ()

    def solution(self, agent, bindings, zexpr):
        if not predSolve1(agent, bindings, zexpr[0]):
            return SOLVED
        else:
            return NOT_SOLVED

    def solutions(self, agent, bindings, zexpr):
        if predSolve1(agent, bindings, zexpr[0]):
            return NO_SOLUTIONS
        else:
            return ONE_SOLUTION

    def conclude(self, agent, bindings, zexpr):
        predRetractall(agent, bindings, zexpr[0])


################################################################

class Exists(Imp):
    __slots__ = ()

    def solution(self, agent, bindings, zexpr):
        return predSolve1(agent, bindings, zexpr[1])

    def solutions(self, agent, bindings, zexpr):
        return predSolve(agent, bindings, zexpr[1])

    def retractall(self, agent, bindings, zexpr):
        return predRetractall(agent, bindings, zexpr[1])

################################################################

STRING_SYNTAX = "T"
SYMBOL_SYNTAX = "Y"
FORCE_SYMBOL_SYNTAX = "y"       # for old style procedure declarations
INTEGER_SYNTAX = "I"
IGNORE_SYNTAX = "."
LIST_STRING_SYNTAX = "L"

def syntaxEval(spu, zitem, syntax):
    if zitem is None:
        return None
    required = None
    if syntax == STRING_SYNTAX:
        if not isinstance(zitem, ExprString):
            required = "string"
    elif syntax == SYMBOL_SYNTAX:
        if not isinstance(zitem, ExprSymbol):
            required = "symbol"
    elif syntax == INTEGER_SYNTAX:
        if not isinstance(zitem, ExprInteger):
            required = "integer"
    elif syntax == LIST_STRING_SYNTAX:
        required = "list of strings"    # assume bad
        if isinstance(zitem, ExprList):
            for elt in zitem:
                if not isinstance(elt, ExprString):
                    break
            else:                        # looped through without breaking
                required = None
    elif syntax == FORCE_SYMBOL_SYNTAX:
        if isinstance(zitem, ExprString):
            return Symbol("_"+zitem.asString())
        if not isinstance(zitem, ExprSymbol):
            required = "symbol"
    else:
        raise ProcessingError("Unknown syntax character %r in declaration of functor"%syntax)
    if required:
        #breakpoint(expecting=required)
        raise ProcessingError("Expecting %s"%required)
    else:
        return zitem.asValue()
    

def modesym(arg):
    if isinstance(arg, ExprVariable):
        return "-"
    elif isinstance(arg, ExprStructure):
        f = arg.functor
        if len(arg) != 1:
            pass
        elif f == PREFIX_PLUS_SYMBOL:
            return "+"
        elif f == PREFIX_MINUS_SYMBOL:
            return "-"
        raise ProcessingError("Invalid functor in declaration argument %s"%f)
    raise ProcessingError("Invalid declaration argument %s %r"%(type(arg), arg))
    
REST_COLON_SYMBOL = Symbol("rest:")

def processDecl(decl):
    "Return functor name string, mode string, +mode string, and -mode string"
    fname = str(decl.functor)
    length = len(decl)
    mode = ""
    emode = ""
    mmode = ""
    fmode = ""
    for i in range(length - 1):
        mode = mode + modesym(decl[i])
    if len(decl) > 0:
        arg = decl[-1]
        if isinstance(arg, ExprStructure) and arg.functor == REST_COLON_SYMBOL \
           and len(arg) == 1:
            mode = mode + REPSYM + modesym(arg[0])
            emode = "+" * (length - 1) + "*+"
            mmode = "-" * (length - 1) + "*-"
            fmode = "g" * (length -1) + "*g"
        else:
            mode = mode + modesym(arg)
            emode = "+" * length
            mmode = "-" * length
            fmode = "g" * length
    return (fname, mode, emode, mmode, fmode)

def getArgNames(agent, bindings, expr):
    if isinstance(expr, ExprCompound):
        argnames = []
        def addArgName(expr):
            if isinstance(expr, ExprVariable):
                argnames.append(expr.asString()[1:])
            elif isinstance(expr, ExprCompound):
                addArgName(expr[0])
        for arg in expr:
            addArgName(arg)
        return List(argnames)
    else:
        return None

# To avoid needing multiple inheritance for defprocedure{} and
# defadvice{} we make ALL definitions subclasses of
# ClosureImp. However, we can only evaluate (and hence create a real
# closure from) those subclasses which supply a value for the
# evaluate_class attribute.

from spark.internal.repr.closure import ClosureImp
class DefStandard(ClosureImp):
    __slots__ = ()
    USEIMP = True
    def conclude(self, agent, bindings, zexpr):
        # only works for zexpr = expr
        sym = entity(agent, bindings, zexpr[0])
        if not (sym): raise AssertionError
        #print "*** Concluding info for %s"%sym
        def concludeComponent(predsym, keyword, evaluatorfn):
            if isinstance(keyword, int):
                valexpr = zexpr[keyword]
            else:
                valexpr = zexpr.keyget0(keyword)
            if valexpr is not None:
                value = evaluatorfn(agent, bindings, valexpr)
                if value is not None:
                    #print "*** (%s %s %s)"%(predsym, sym, value)
                    imp = agent.getImp(predsym)
                    b, z = valuesBZ((sym, value))
                    imp.conclude(agent, b, z)
        concludeComponent(P_Doc, "doc:", termEvalErr)
        concludeComponent(P_Features, "features:", termEvalErr)
        concludeComponent(P_Properties, "properties:", termEvalErr)
        concludeComponent(P_ArgTypes, "argtypes:", termEvalErr)
        concludeComponent(P_Roles, "roles:", quotedEval)
        concludeComponent(P_ArgNames, 0, getArgNames)
        concludeComponent(P_ArgNames, "argnames:", termEvalErr)
        self.concludeImp(agent, bindings, zexpr)

    def concludeImp(self, agent, bindings, zexpr):
        "Set the implementation for the defined symbol"
        # This has been separated out for use in resuming a persisted state.
        # imp: is treated almost the same, but the value is applied to the
        # symbol declaration before being asserted
        if self.USEIMP:
            valexpr = zexpr.keyget0("imp:")
            if valexpr is not None:
                sym = entity(agent, bindings, zexpr[0])
                decl = agent.getDecl(sym)
                value = termEvalErr(agent, bindings, valexpr)(decl)
                imp = agent.getImp(P_Implementation)
                b, z = valuesBZ((sym, value))
                imp.conclude(agent, b, z)
                

class DeclareBrace(DefStandard):
    __slots__ = ()
    USEIMP = False
    def stageOne(self, spu, zexpr):
        idsym = syntaxEval(spu, zexpr[0], FORCE_SYMBOL_SYNTAX)
        modes = syntaxEval(spu, zexpr.keyget0("modes:"), LIST_STRING_SYNTAX)
        keys = syntaxEval(spu, zexpr.keyget0("keys:"), LIST_STRING_SYNTAX)
        keysRequired = syntaxEval(spu, zexpr.keyget0("keysRequired:"), LIST_STRING_SYNTAX)
        imp = syntaxEval(spu, zexpr.keyget0("imp:"), STRING_SYNTAX)
        combiner = syntaxEval(spu, zexpr.keyget0("combiner:"), STRING_SYNTAX)
        spu.setDecl(zexpr, str(idsym), modes, keys, keysRequired, imp, combiner)
        

#     def conclude(self, agent, bindings, zexpr):
#         # only works for zexpr = expr
#         sym = entity(agent, bindings, zexpr[0])

#         def concludeComponent(predsym, keyword, evaluatorfn):
#             if isinstance(keyword, int):
#                 valexpr = zexpr[keyword]
#             else:
#                 valexpr = zexpr.keyget0(keyword)
#             if valexpr is not None:
#                 value = evaluatorfn(agent, bindings, valexpr)
#                 if value is not None:
#                     imp = agent.getImp(predsym)
#                     zb = ValueZB((sym, value))
#                     imp.conclude(agent, zb, zb)
#         concludeComponent(P_Doc, "doc:", termEvalErr)
#         concludeComponent(P_Features, "features:", termEvalErr)
#         concludeComponent(P_Properties, "properties:", termEvalErr)
#         concludeComponent(P_ArgTypes, "argtypes:", termEvalErr)
#         concludeComponent(P_Roles, "roles:", quotedEval)
#         concludeComponent(P_ArgNames, "argnames:", termEvalErr)


class DefactionBrace(DefStandard):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        (fname, mode, emode, mmode, fmode) = processDecl(zexpr[0])
        modes = [ACTION_DO + REQSYM + mode, FORMALS + REQSYM + fmode]
        spu.setDecl(zexpr, fname, modes)


class DeffunctionBrace(DefStandard):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        (fname, mode, emode, mmode, fmode) = processDecl(zexpr[0])
        modes = [TERM_MATCH + REQSYM + mode, TERM_EVAL + REQSYM + emode]
        spu.setDecl(zexpr, fname, modes)

class DefpredicateBrace(DefStandard):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        (fname, mode, emode, mmode, fmode) = processDecl(zexpr[0])
        modes = [PRED_SOLVE + REQSYM + mode,
                                 PRED_RETRACTALL + REQSYM + mode,
                                 PRED_UPDATE + REQSYM + emode,
                                 PRED_ACHIEVE + REQSYM + mode,
                                FORMALS + REQSYM + fmode]
        spu.setDecl(zexpr, fname, modes)

from spark.internal.repr.procedure import ProcedureValue

class DefprocedureBrace(DefStandard):
    """Structure internal to a Procedure """
    __slots__ = ()
    evaluate_class = ProcedureValue
    def stageOne(self, spu, zexpr):
        idsym = syntaxEval(spu, zexpr[0], FORCE_SYMBOL_SYNTAX)
        spu.setConstantDecl(zexpr, str(idsym))

    def conclude(self, agent, bindings, zexpr):
        DefStandard.conclude(self, agent, bindings, zexpr)
        name = entity(agent, bindings, zexpr[0])
        cueexpr = zexpr.keyget0("cue:")[0]
        cuePredsym = bindings.bImp(agent, cueexpr).predsym
        cuePredImp = agent.getImp(cuePredsym)
        ent = entity(agent, bindings, cueexpr[0])
        procedure = self.call(agent, bindings, zexpr)
        b, z = valuesBZ((ent, procedure, name))
        cuePredImp.conclude(agent, b, z)
        
from spark.internal.repr.procedure import AdviceClosureValue
class DefadviceBrace(DefStandard, ClosureImp):
    __slots__ = ()
    evaluate_class = AdviceClosureValue
    def stageOne(self, spu, zexpr):
        idsym = syntaxEval(spu, zexpr[0], FORCE_SYMBOL_SYNTAX)
        spu.setConstantDecl(zexpr, str(idsym))

    def conclude(self, agent, bindings, zexpr):
        DefStandard.conclude(self, agent, bindings, zexpr)
        name = entity(agent, bindings, zexpr[0])
        kind = termEvalErr(agent, bindings, zexpr[1])
        docExpr = zexpr.keyget0("doc:")
        if docExpr:
            doc = termEvalErr(agent, bindings, docExpr)
        else:
            doc = ""
        adviceClosureValue = self.call(agent, bindings, zexpr)
        advicePredImp = agent.getImp(ADVICE)
        b, z = valuesBZ((name, kind, adviceClosureValue, doc))
        # TODO: consider calling advicePredImp.conclude(agent, bindings, (?(zexpr[0]), zexpr[1], zexpr, ?(sexpr.keyget0("doc:")))
        advicePredImp.conclude(agent, b, z)


class DefconsultBrace(DefStandard):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        idsym = syntaxEval(spu, zexpr[0], FORCE_SYMBOL_SYNTAX)
        spu.setConstantDecl(zexpr, str(idsym))

class DefconstantBrace(DefStandard):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        idsym = syntaxEval(spu, zexpr[0], FORCE_SYMBOL_SYNTAX)
        spu.setConstantDecl(zexpr, str(idsym))

class NullConcludeImp(Imp):
    __slots__ = (
        )
    def conclude(self, agent, bindings, zexpr, kbResume=False):
        pass

class MainColon(NullConcludeImp):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        idsym = syntaxEval(spu, zexpr[0], FORCE_SYMBOL_SYNTAX)
        spu.setMain(zexpr, idsym)

class ImportfromColon(NullConcludeImp):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        syms = [str(syntaxEval(spu, zitem, SYMBOL_SYNTAX)) for zitem in zexpr]
        fromPackage = syms[0]
        ids = syms[1:]
        if ids:
            for id in ids:
                spu.setImportOne(zexpr, id, fromPackage, id)
        else:
            spu.setImportAll(zexpr, fromPackage)

class Special(NullConcludeImp):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        package = str(syntaxEval(spu, zexpr[0], SYMBOL_SYNTAX))
        spu.setSpecial(zexpr, package)

class ImportallColon(NullConcludeImp):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        fromPackage = syntaxEval(spu, zexpr[0], SYMBOL_SYNTAX)
        spu.setImportAll(zexpr, fromPackage)

class ImportColon(NullConcludeImp):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        packageids = [syntaxEval(spu, zitem, SYMBOL_SYNTAX) for zitem in zexpr]
        spu.recordErrorW(zexpr, "The import: statement is deprecated")
        for pid in packageids:
            spu.setImportOne(zexpr, pid.id, pid.modname, pid.id)

class ExportColon(NullConcludeImp):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        ids = [syntaxEval(spu, zitem, SYMBOL_SYNTAX) for zitem in zexpr]
        for id in ids:
            spu.setExport(zexpr, str(id))

class ExportallColon(NullConcludeImp):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        spu.setExport(zexpr, None)


class RequiresColon(NullConcludeImp):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        rsym = syntaxEval(spu, zexpr[0], SYMBOL_SYNTAX)
        spu.setRequires(zexpr, str(rsym))


class ModuleColon(NullConcludeImp):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        psym = syntaxEval(spu, zexpr[0], SYMBOL_SYNTAX)
        spu.setPackage(zexpr, str(psym))


class Static(Imp):
    __slots__ = ()
    VALUE = Symbol("static").structure()
    def call(self, agent, bindings, zitems):
        return self.VALUE

    def match_inverse(self, agent, bindings, zexpr, obj):
        return obj == self.VALUE

class PyFunction(Imp):
    __slots__ = ()
    def call(self, agent, bindings, zitems):
        mode = termEvalErr(agent, bindings, zitems[0])
        fun = termEvalErr(agent, bindings, zitems[1])
        return BasicFun(mode, fun)


class PyMod(Imp):
    __slots__ = ()
    def call(self, agent, bindings, zitems):
        modname = termEvalErr(agent, bindings, zitems[0])
        attribute = termEvalErr(agent, bindings, zitems[1])
        return PythonProxy(modname, attribute)

class PyModRaw(Imp):
    __slots__ = ()
    def call(self, agent, bindings, zitems):
        modname = termEvalErr(agent, bindings, zitems[0])
        attribute = termEvalErr(agent, bindings, zitems[1])
        return PythonProxyRaw(modname, attribute)

class Qent(Imp):
    __slots__ = ()
    def call(self, agent, bindings, zitems):
        return entity(agent, bindings, zitems[0])

    def match_inverse(self, agent, bindings, zitems, obj):
        return entity(agent, bindings, zitems[0]) == obj

class BackquotePrefix(Imp):
    __slots__ = ()
    def call(self, agent, bindings, zitems):
        return quotedEval(agent, bindings, zitems[0])

    def match_inverse(self, agent, bindings, zitems, obj):
        return quotedMatch(agent, bindings, zitems[0], obj)

class CommaPrefix(Imp):
    __slots__ = ()
    def quotedEval(self, agent, bindings, zitems):
        return termEvalErr(agent, bindings, zitems[0])

    def quotedMatch(self, agent, bindings, zitems, obj):
        return termMatch(agent, bindings, zitems[0], obj)

class PlusPrefix(Imp):
    __slots__ = ()
    def formal(self, agent, formalBindings, zexpr, actualBindings, zitem, match):
        if match:
            val = termEvalOpt(agent, actualBindings, zitem)
            if val is None:             # actual param not evaluable
                return False
            else:
                return termMatch(agent, formalBindings, zexpr[0], val)
        else:
            return True
 
from spark.internal.parse.expr import ExprLocalVariable
class MinusPrefix(Imp):
    __slots__ = ()
# True Output Parameter
#     def formal(self, agent, formalBindings, zexpr, actualBindings, zitem, match):
#         if match:
#             return True
#         else:
#             val = termEvalErr(agent, formalBindings, zexpr[0])
#             return termMatch(agent, actualBindings, zitem, val)
# Ouput Parameter as a constraint (only works for variables)
# Will have to do until procedures include code to evaluate output parameters  on success - DNM
# TODO: must fix this
    def formal(self, agent, formalBindings, zexpr, actualBindings, zitem, match):
        varExpr = zexpr[0]
        if not (isinstance(varExpr, ExprLocalVariable)): raise AssertionError, \
               "Currently, only variables may be used as output parameters, not %s"%varExpr
        if match:
            formalBindings.setConstraint(agent, varExpr._value, actualBindings, zitem)
            return True
        else:
            val = formalBindings.getVariableValue(agent, varExpr._value)
            return termMatch(agent, actualBindings, zitem, val)
        

class Implementation(Imp):
    __slots__ = ()
    def conclude(self, agent, bindings, zexpr):
        sym = termEvalErr(agent, bindings, zexpr[0])
        imp = termEvalErr(agent, bindings, zexpr[1])
        agent.setImp(sym, imp)
        #print "Setting implementation of %s to %s"%(sym, imp)

    def solutions(self, agent, bindings, zexpr):
        sym = termEvalErr(agent, bindings, zexpr[0])
        imp = agent.getImp(sym)
        if termMatch(agent, bindings, zexpr[1], imp):
            return ONE_SOLUTION
        else:
            return NO_SOLUTIONS

    def solution(self, agent, bindings, zexpr):
        sym = termEvalErr(agent, bindings, zexpr[0])
        imp = agent.getImp(sym)
        if termMatch(agent, bindings, zexpr[1], imp):
            return SOLVED
        else:
            return NOT_SOLVED

################################################################
# PythonProxy

class PythonProxyRaw(ConstructibleValue):
    __slots__ = (
        "_PythonProxyInstance",
        "_PythonProxyModName",
        "_PythonProxyVarName",
        )
    def __init__(self, modname, varname):
        ConstructibleValue.__init__(self)
        self._PythonProxyModName = modname
        self._PythonProxyVarName = varname
        val = pyMod(modname, varname)
        self._PythonProxyInstance = val

    def __getattr__(self, name):
        # the following automatically access the most recently loaded version
        #instance = getattr(sys.modules[self._PythonProxyModName], self._PythonProxyVarName)
        # the following accesses the version loaded at proxy creation time
        instance = self._PythonProxyInstance
        #print "Getting attribute", name
        return getattr(instance, name)

    def __call__(self, *args, **keyargs):
        instance = self._PythonProxyInstance
        return instance(*args, **keyargs)

    def constructor_args(self):
        return [self._PythonProxyModName, self._PythonProxyVarName]
    constructor_mode = "VV"
    
installConstructor(PythonProxyRaw)

class PythonProxy(PythonProxyRaw):
    __slots__ = ()
    def __call__(self, *args, **keyargs):
        instance = self._PythonProxyInstance
        val = instance(*args, **keyargs)
        if val is None:
            return None
        else:
            return coerceToSparkValue(val)

installConstructor(PythonProxy)

################################################################

def inspect_me():
    import pdb, sys
    try:
        raise Exception
    except:
        pdb.post_mortem(sys.exc_info()[2])



def pyMod(modname, funname):
    import sys
    try:
        __import__(modname)
    except ImportError, e:
        errid = NEWPM.recordError()
        #import traceback
        #print "EXCEPTION IN", self.name
        #traceback.print_exception(*self.exc_info)
        raise UnlocatedError("Error importing Python module %s:\n[%d] %s"%(modname, errid, e))
    module = sys.modules[modname]
    try:
        return getattr(module, funname)
    except AttributeError:
        raise UnlocatedError("Python module %s has no attribute %s" \
                             % (modname, funname))


class Method(ConstructibleValue):
    __slots__ = (
        "_methodname",
        )

    def __init__(self, methodname):
        ConstructibleValue.__init__(self)
        self._methodname = methodname

    def __call__(self, object, *args):
        try:
            value = getattr(object, self._methodname)
        except AttributeError:
            raise UnlocatedError("Object has no python method %s: %r"%(self._methodname, object))
        return value(*args)        

    def __repr__(self):
        return "Method(%r)" % self._methodname

    def constructor_args(self):
        return [self._methodname]
    constructor_mode = "V"

installConstructor(Method)

################################################################
#

def symbol_absname(object):
    if not isSymbol(object):
        raise UnlocatedError("Not a symbol: %r"%object)
    return object.name

def construct_struct(functor_string, *args):
    return Structure(Symbol(functor_string), args)

def deconstruct_struct(struct):
    if isStructure(struct):
        return List((struct.functor.name,) + tuple(struct))
    else:
        return None

def get_functor_string(struct):
    return struct.functor.name

def get_functor(struct):
    return struct.functor

def get_args(struct):
    return List(struct)

################################################################
# Various functions useful for implementations
    
class ApplyAct(ActImpInt):
    __slots__ = ()
    def __init__(self, _symbol):
        pass

    def tframes(self, agent, event, bindings, zexpr):
        actvalue = termEvalErr(agent, bindings, zexpr[0])
        imp = agent.value_imp(actvalue)
        return imp.tframes(agent, event, bindings, zexpr[1:])

class ApplyProc(ActImpInt):
    """Apply a fixed procedure"""
    __slots__ = ()
    def __init__(self, _symbol):
        pass

    def tframes(self, agent, event, bindings, zexpr):
        procvalue = termEvalErr(agent, bindings, zexpr[0])
        tframes = []
        procvalue.append_tframes(agent, event, bindings, zexpr[1:], tframes)
        return tframes


class MetaProcedure2(SimpleProcedure): # fact invoked
    __slots__ = ()

    def applicable(self, agent, event, bindings, zexpr):
        base_event = event.base_event()
        allow_multi = not base_event.is_solver() # allows multiple solutions
        tframes = termEvalErr(agent, bindings, zexpr[1])
        return allow_multi and len(tframes) > 1
        
    def execute(self, agent, event, bindings, zexpr):
        #print "non-solver multiple - intend all"
        tframes = termEvalErr(agent, bindings, zexpr[1])
        for tframe in tframes:
            agent.add_tframe(tframe)
        return SUCCESS

MP2 = MetaProcedure2("Fact-invoked-meta")

pyFunction = BasicFun("++", BasicFun)

def numrequiredargs(agent, symbol):
    decl = agent.getDecl(symbol)
    return decl.modes[0].sigreq

def restargsallowed(agent, symbol):
    decl = agent.getDecl(symbol)
    return decl.modes[0].sigrep

def requiredargnames(agent, symbol):
    decl = agent.getDecl(symbol)
    sigreq = decl.modes[0].sigreq
    facts = agent.factslist1(P_ArgNames, symbol)
    if facts:
        return List(facts[0][1][:sigreq])
    else:
        return None
#     # Note - this needs to be accessed by sparkdoc => must be available without agent
    
#     syminfo = symbol_get_syminfo(symbol)
#     return syminfo.get_property(P_RequiredArgNames, ())

def restargnames(agent, symbol):
    mode = agent.getDecl(symbol).modes[0]
    sigrep = mode.sigrep
    if sigrep > 0:
        sigreq = mode.sigreq
        facts = agent.factslist1(P_ArgNames, symbol)
        if facts:
            return List(facts[0][1][sigreq:sigreq+sigrep])
        else:
            return None
    else:
        return None
        
#     syminfo = symbol_get_syminfo(symbol)
#     return syminfo.get_property(P_RestArgName, None)

#################################################################
# Stuff formerly part of spark.lang.common
#################################################################

log_file = None

def set_print_log_file(log_file_handle):
    """Use this function to direct [do: (print ...)] output to a log file
    in addition to stdout"""
    global log_file
    log_file = log_file_handle
    
def testGround(*args):
    if None in args:
        raise UnlocatedError("Parameter %d of Ground is not a bound variable"%list(args).index(None))
    return args

def testGround1(arg):
    #if (arg is None): raise AssertionError, \
    #    "Parameter of Ground is not a bound variable"
    return arg

from spark.lang.string import format_string
def prin(format, args):
    """Print implementation for the print task.
    By default prints to stdout, but if set_print_log_file
    is called, output can be directed to a log file as well.
    Returns the printed string or " " if there was no problem
    and returns False if there was an error."""
    done = False
    try:
        print_str = format_string(format, args)
        print print_str
        if log_file is not None:
            log_file.write(print_str + '\n')
        done = print_str or " "         # ensures done is treated as true
    finally:
        if not done:
            print "ERROR IN PRINT ACTION: format=%r, args=%r" % (format, args)
    return done

def print_predicate(format, *args):
    return prin(format, args)

def intbetween(low, x, high):
    if x is None:
        return List(range(low, high+1))
    else:
        return low <= x and x <= high
        
def arg(struct, i):
    return struct[i]

def get_attribute(obj, attribute_namex):
    return get_attribute_default(obj, attribute_namex, None)

def get_attribute_default(obj, attribute_namex, defaultVal):
    """get Python/JavaBean attribute."""
    
    #convert symbols to strings to make it easier to write
    #routines for converting structure values into java beans
    if isSymbol(attribute_namex):
        attribute_name = attribute_namex.id
    else:
        attribute_name = attribute_namex

    #check for java-style getProperty(key) classes and wrap these
    #XXX: should probably check arity of getProperty()
    if hasattr(obj, "getProperty") and callable(obj.getProperty):
        return obj.getProperty(attribute_name) or defaultVal
        
    if not hasattr(obj, attribute_name):
        #XXX:EXCEPTIONTYPE
        raise UnlocatedError("Object has no attribute named %s"%attribute_name)

    return getattr(obj, attribute_name) or defaultVal

def set_attribute(obj, attribute_namex, attribute_val):
    """set Python/JavaBean attribute."""

    #convert symbols to strings to make it easier to write
    #routines for converting structure values into java beans
    if isSymbol(attribute_namex):
        attribute_name = attribute_namex.id
    else:
        attribute_name = attribute_namex

    if not hasattr(obj, attribute_name):
        #XXX:EXCEPTIONTYPE        
        raise UnlocatedError("Object has no attribute named %s"%attribute_name)
    setattr(obj, attribute_name, attribute_val)

# def install_builtin():
#     get_builtin_module()._install()  # add in info from .spark file and install

#=======================================    
# List and String functions:

def concatanate(first, second, *args):
    # works for both strings and lists
    res = first + second
    for l in args:
        res = res + l
    return res

def length(item):
    return len(item)

def index_function(idx, elt, item):
    if idx == None:
        if elt == None:
            # for NULL ELEMENT do not return a solution
            return [i_elt for i_elt in enumerate(item) if i_elt[1]!=None]
        else:
            return [i_elt for i_elt in enumerate(item) if i_elt[1]==elt]
    else:
        if elt == None:
            return ((idx, item[idx]),)
        elif elt == item[idx]:
            return ((idx, elt),)
        else:
            return ()

def item_index(i, item):
    try:
        return item[i]
    except IndexError:
        return None
    
def find_all_indices(item):
    return 

# getSubstring
#
# returns substring of $string identified by range
def subitem(s, beg, end):
    sub = s[beg:end]
    return sub

def object_type(value):
    rawform = str(type(value))
    return rawform.split("'")[1]
################################################################

################################################################
class GlobalSet(Imp):
    __slots__ = ()

    def call(self, agent, bindings, zexpr):
        raise LowError("Cannot evaluate @-, you can only match it")

    def match_inverse(self, agent, bindings, zexpr, obj):
        sym = termEval(agent, bindings, zexpr[0])
        if not (isSymbol(sym) or isString(sym)): raise AssertionError, \
           "@- argument must be a symbol or string, not %s"%(value_str(sym),)
        setattr(V, str(sym), obj)
        return True

################################################################
class GlobalGet(Imp):
    __slots__ = ()

    def call(self, agent, bindings, zexpr):
        sym = termEval(agent, bindings, zexpr[0])
        if not (isSymbol(sym) or isString(sym)): raise AssertionError, \
           "@- argument must be a symbol or string, not %s"%(value_str(sym),)
        try:
            val = getattr(V, str(sym))
        except AttributeError:
            raise LowError("Global V.%s is not set"%str(sym))
        return val

    def match_inverse(self, agent, bindings, zexpr, obj):
        return self.call(agent, bindings, zexpr) == obj


def symbolPackage(symbol):
    return symbol.modname

################################################################
# functions to support partial lists and structures, i.e., one with
# "missing" elements.

def partial(full, nullvalue):
    "Given a full list/structure, replace elements equal to nullvalue with null"
    return substitute(full, nullvalue, None)

def substitute(sequence, oldvalue, newvalue):
    if oldvalue not in sequence:
        return sequence
    def sub(original):
        if original == oldvalue:
            return newvalue
        else:
            return original
    if isList(sequence):
        return List([sub(x) for x in sequence])
    elif isStructure(sequence):
        return Structure(sequence.getFunctor(), [sub(x) for x in sequence])
    else:
        raise LowError("Cannot create a partial object other than a List or Structure")
        

def inversePartial(partial):
    """Return a full list/structure and the lowest non-negative
    integer nullvalue usable as input to partial."""
    for nullvalue in range(len(partial) + 1):
        if nullvalue not in partial:
            return substitute(partial, None, nullvalue), nullvalue
    # We cannot reach here because at least nullvalue must be usable

def partialPredicate(fullSeq, nullValue, partialSeq):
    """Implement the predicate Partial relating full and partial sequences.

    The implementation is incomplete (i.e., returns only a single
    solution, that with the lowest non-negative integer value for
    nullValue) for mode +-+ if the partialSeq has no missing elements
    and for mode --+.
    """
    if fullSeq != None and None in fullSeq:
        raise LowError("The full sequence argument cannot have missing elements")
    if partialSeq is None:              # mode ??-
        if fullSeq is None:             # mode -?-
            raise LowError("Either the full sequence or the partial sequence must be supplied")
        else:                           # mode +?-
            if nullValue is None:       # mode +--
                raise LowError("The null value must be supplied")
            else:                       # mode ++-
                p = partial(fullSeq, nullValue)
                return (fullSeq, nullValue, p)
    else:                               # mode ??+
        if fullSeq is None:             # mode -?+
            if nullValue is None:       # mode --+
                (f,n) = inversePartial(partialSeq)
                return (f, n, partialSeq)
            else:                       # mode -++
                if nullValue in partialSeq:
                    # nullValue is already an element of the partial sequence
                    return None
                else:
                    f = substitute(partialSeq, None, nullValue)
                    return (f, nullValue, partialSeq)
        else:                           # mode +?+
            n = nullValue
            for (fe,pe) in zip(fullSeq, partialSeq):
                if pe is None:
                    if n is None:
                        n = fe
                    elif fe != n:   # the given (or no single) nullValue works
                        return None
                elif fe != pe:        # mismatched elemnts
                    return None
            if n is None:           # partialSeq == fullSeq
                n = 0               # pick the lowest
            return (fullSeq, n, partialSeq)
                    
PARTIAL_SYMBOL = Symbol('partial')
SPARK_NULL = Symbol("spark.lang.builtin.NULL")

def sparkNULL():
    global SPARK_NULL
    return SPARK_NULL

################################################################

from spark.internal.parse.fip import Decl

class IfdefBase(NullConcludeImp):
    __slots__ = ()
    def stageOne(self, spu, zexpr):
        # Assumes that zexpr and sub-exprs are all validated
        sym = str(syntaxEval(spu, zexpr[0], SYMBOL_SYNTAX))
        symdecl = spu.findCacheId(sym, False)
        # TODO check this works (is Decl) for special import of symbols
        if isinstance(symdecl, Decl) != self.decl_present_condition:
            return False
        return spu.stageOneProcessExpr(zexpr[1], True)
        
class Ifdef(IfdefBase):
    __slots__ = ()
    decl_present_condition = True

class Ifndef(IfdefBase):
    __slots__ = ()
    decl_present_condition = False

################################################################

class HashProperties(Imp):
    def solutions(self, agent, bindings, zexpr):
        return predSolve(agent, bindings, zexpr[0])

    def solution(self, agent, bindings, zexpr):
        return predSolve1(agent, bindings, zexpr[0])
