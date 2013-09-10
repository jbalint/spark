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
#* "$Revision:: 216                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.version import *
from weakref import ref
from spark.internal.common import DEBUG, ABSTRACT, delete_all, SUCCESS
from spark.internal.parse.constructor import Constructor, INTEGER, FLOAT, STRING, VARIABLE, SYMBOL, STRUCTURE, LIST
from spark.internal.parse.usages import *
from spark.internal.parse.usagefuns import *
from sets import Set, ImmutableSet
from spark.internal.parse.basicvalues import *
from spark.internal.exception import LowError, Unimplemented
from spark.pylang.implementation import Imp
from spark.internal.parse.fip import Decl, NoKeyDecl
from spark.internal.parse.sets_extra import *
from spark.internal.parse.errormsg import ErrorMsg, F2, F4
EMPTY_SET = ImmutableSet()

debug = DEBUG(__name__)#.on()

################################################################
################
####
#
# Internal data structures correspond to syntactic types

# To simplify the execution of non-structure Exprs, we treat these as
# having non-symbol "functor"s. This allows the implementation look up
# to be done in exactly the same way as for ExprStructures.

IMP_KEY_STRING = intern('"')
IMP_KEY_INTEGER = intern("I")
IMP_KEY_FLOAT = intern("F")
IMP_KEY_SYMBOL = intern("S")
IMP_KEY_LOCAL_VARIABLE = intern("$")
IMP_KEY_CAPTURED_VARIABLE = intern("C")
IMP_KEY_LIST = intern("L")
IMP_KEY_STRUCTURE = intern("(")



class E221InvalidUsage(ErrorMsg):
    level = F2
    argnames = ["typeStr"]
    format = "Invalid usage: cannot be %(typeStr)s"
    description = "Different classes of Exprs (StructureExpr, SymbolExpr, ...) each have their own limitations on what sort of usages are possible."

class E222VarNotBound(ErrorMsg):
    level = F2
    argnames = ["var"]
    format = "Variable %(var)s is not bound"

class E223OuterVarNotBound(ErrorMsg):
    level = F2
    argnames = ["var"]
    format = "Variable %(var)s cannot be used before it is bound"
    description = "An attempt is being made to match an unbound captured variable (e.g. $$x)"

class E234VarAlreadyBound(ErrorMsg):
    level = F2
    argnames = ["var"]
    format = "Variable %(var)s is already bound and cannot be quantified over"
    description = "Where a varlist is required, generally introducing some form of quantification, a variable that is already bound has been supplied. We don't currently quantification to introduce a new scope for a variable."

class E235IOVarNotBound(ErrorMsg):
    level = F2
    argnames = ["var"]
    format = "Variable %(var)s is not bound by the body (consider making it input)."
    description = "A formal parameter variable that is not specifed as input has not been bound by the time that i/o and output parameters need to be bound. This may just be a case of not having annotated a parameter as input."

class E226NoDeclaredUsage(ErrorMsg):
    level = F2
    argnames = ["symStr", "typeStr"]
    format = "%(symStr)s has not been declared to be %(typeStr)s"
    description = "A declaration of an id limits what it can be used as."

class E227MismatchSig(ErrorMsg):
    level = F2
    argnames = ["symStr", "msg"]
    format = "%(symStr)s: %(msg)s"
    description = "The expression does not match the declared signature of the id"

class E228InvalidSpecialMode(ErrorMsg):
    level = F2
    argnames = ["typeStr", "needed", "actual"]
    format = "For this to be %(typeStr)s the mode must be %(needed)s not %(actual)s"
    description = "The expression matches a %-mode but not a =-mode"

class E229InvalidFormalSpec(ErrorMsg):
    level = F2
    argnames = []
    format =  "Invalid formal parameter specification"

class E421InvalidUsage(ErrorMsg):
    level = F4
    argnames = ["sym", "typeStr"]
    format = "'%(sym)s' is not declared to be %(typeStr)s"

class E422InvalidMode(ErrorMsg):
    level = F4
    argnames = ["sym", "typeStr", "mode"]
    format = "For '%(sym)s' used as %(typeStr)s the arguments must match %(mode)s"
class E423MismatchSig(E227MismatchSig):
    level = F4







def noneRef():
    return None

class Expr(Value):
    __stateslots__ = (
        "start",
        "end",
        "_value",
        "usage",
        )
    __slots__ = __stateslots__ + (
        "index",                    # index within SPU in prefix order
        "parentref",
        )

    def __restore__(self):
        # check to see if self has been inserted as an argument of
        # it's parent before self has been initialised
        if (hasattr(self, "parentref")): raise AssertionError, \
           "parentref is already set"
        self.parentref = noneRef
        self.index = None

    indexCompound = False       # this is overridden for compound Exprs
    
    def __init__(self, start, end, value):
        self.start = start
        self.end = end
        self.usage = None
        self._value = value
        self.__restore__()

    def __cmp__(self, other):
        # Comparison is based on start and end characters
        if other is None:
            return -1
        else:
            return cmp(self.start, other.start) or cmp(self.end, other.end)

    def __str__(self):
        return value_str(self.asValue())

    def __repr__(self):
        return "<Expr %s %s>"%(self.index, value_str(self.asValue()))

    # no value_str method since this is not a core data value
    def inverse_eval(self):
        return SYM_idExpr.structure(self.index or 0)

    def append_value_str(self, buf):
        buf.append(",")
        return self.inverse_eval().append_value_str(buf)

    # arentref information
    # Used by:
    #   getParent
    #     varsBeforeAndHere
    #       (tracing)(forall:)(utilities.resource)
    #   getSPU
    #     (utilities.resource)
    #     ErrorMsg.setExpr
    #   getDepth # UNUSED?
        

    def getParent(self):      # TODO: replace this with accessor .parent
        return self.parentref()

    def getSPU(self):
        parentref = self.parentref
        if parentref == noneRef:
            print "ERROR GETTING SPU OF %r"%self
            print "returning None"
            return None
        parent = parentref()
        if parent is None:
            print "ERROR - PARENT IS NONE: %r"%self
            print "returning None"
            return None
        return parent.getSPU()

    def getDepth(self):                 # UNUSED?
        depth = 0
        parentref = self.parentref
        while parentref:
            depth = depth + 1
            parent = parentref()
            if not isinstance(parent, Expr):
                break
            parentref = parent.parentref
        return depth


    def getLocationString(self, message):
        spu = self.getSPU()
        if spu:
            return "in %s - %s\n%s"%(spu, message, spu.exprLocation(self))
        else:
            return "in <cannot get SPU> - %s\n%s"%(message, self)

    # subclasses redefine the following

    functor = None                      # override in structure
    impKey = ABSTRACT # symbol indicating implementation to use
    description = ABSTRACT      # string describing the syntactic form
    validUsages = ABSTRACT      # What usages are syntactically valid
    def asString(self):     # override in Variable, Symbol, and String
        raise Constructor.ValueException("Not a String, Variable, or Symbol")
    def asInteger(self):                # override in Integer
        raise Constructor.ValueException("Not an Integer")
    def asFloat(self):                  # override in Float
        raise Constructor.ValueException("Not a Float")
    def components(self):               # override in ExprCompound
        raise Constructor.ValueException("Not a List or Structure")
    def category(self):
        raise Constructor.ValueException("Not a valid category")

    def revalidate(self, context, vbbefore): # DEFAULT
        """Perform validation of output formal parameters."""

    def error(self, format, *args):
        return LocatedError(self, format%args)

    def introducesNewContext(self):     # DEFAULT
        return False

    def asValue(self):
        raise Unimplemented()

    def validate(self, context, vbbefore, activity, usage):
        """Return a set of free variables of self or None on error.
        Set self.usage to usage and ensure it is valid.
        Adjust self.usage to a stricter usage if justified.
        vbbefore are the variables of context that are bound going in to self.
        activity specifies whether self is executed at LOADTIME or RUNTIME."""
        raise Exception("Unimplemented")

    def checkUsages(self, spu, pspu):
        """In stage four, confirm the usages match the known modes"""
        pass
    
    def _setValidUsageOrError(self, usage):
        self.usage = usage
#         if self.getDepth() == 1:
#             print "VALIDATE usage %s: %s"%(usage, self)
        if usage not in self.validUsages:
            typeStr = reqUsagePrintableName(usage)
            self.getSPU().err(E221InvalidUsage(self, typeStr))
            return False
        return True
        


SYM_idExpr = Symbol("idExpr")

def idExpr(index):
    from spark.internal.parse.processing import SPU_RECORD
    from spark.internal.parse.searchindex import recursiveBinarySearch
    return recursiveBinarySearch(SPU_RECORD, index)


class ExprAtomic(Expr):
    __slots__ = ()

    def asValue(self):
        return self._value

    def annotated(self):
        return str(self)

    # runtime

#     def quoted_eval(self, agent, bindings):
#         return self._value

#     def quoted_match(self, agent, bindings, value):
#         return self._value == value

    
class ExprSimple(ExprAtomic):
    __slots__ = ()

    validUsages = [TERM_EVAL, TERM_MATCH, QUOTED_EVAL, QUOTED_MATCH]

    def validate(self, context, vbbefore, activity, usage):
        if not self._setValidUsageOrError(usage):
            return None
        if usage == TERM_MATCH:
            self.usage = TERM_EVAL
        elif usage == QUOTED_MATCH:
            self.usage = QUOTED_EVAL
        return EMPTY_SET
    
class ExprInteger(ExprSimple):
    __slots__ = ()
    impKey = IMP_KEY_INTEGER
    def category(self):
        return INTEGER
    description = "integer"
    def asInteger(self):
        return self._value

class ExprFloat(ExprSimple):
    __slots__ = ()
    impKey = IMP_KEY_FLOAT
    def category(self):
        return FLOAT
    description = "float"
    def asFloat(self):
        return self._value


class ExprString(ExprSimple):
    __slots__ = ()
    impKey = IMP_KEY_STRING
    def category(self):
        return STRING
    description = "string"
    def asString(self):
        return self._value

#     def entity(self, agent, bindings):
#         # TODO: delete this method when strings are no longer valid procedure names
#         return Symbol(self._value) # this enables strings to be used as procedure names


class ExprSymbol(ExprAtomic):
    __stateslots__ = (
        "resolvedSymbol",
        )
    __slots__ = __stateslots__

    def category(self):
        return SYMBOL
    description = "identifier"
    impKey = IMP_KEY_SYMBOL

    def asString(self):
        return self._value.name

    validUsages = [TERM_EVAL, TERM_MATCH, QUOTED_EVAL, QUOTED_MATCH, ENTITY]

    def __init__(self, start, end, value):
        ExprAtomic.__init__(self, start, end, value)
        self.resolvedSymbol = None
        
    def checkUsages(self, spu, pspu):
        if self.usage not in (QUOTED_EVAL, QUOTED_MATCH):
            decl = spu.stageFourDecl(self._value.name, self, pspu)

    def validate(self, context, vbbefore, activity, usage):
        if not self._setValidUsageOrError(usage):
            return None
        if usage == TERM_MATCH:
            self.usage = TERM_EVAL
        elif usage == QUOTED_MATCH:
            self.usage = QUOTED_EVAL
        if self.usage in (TERM_EVAL, TERM_MATCH, ENTITY):
            idname = self._value.name
            declsym = context.spu.findCacheId(idname, True)
            if isinstance(declsym, Decl):
                self.resolvedSymbol = declsym.asSymbol()
            else:
                self.resolvedSymbol = declsym
        return EMPTY_SET


class ExprVariable(ExprAtomic):
    __slots__ = ()
    def category(self):
        return VARIABLE

    def asString(self):
        return self._value.name

    def annotated(self):
        return (self.usage or "") + str(self)

    def validate(self, context, vbbefore, activity, usage):
        if not self._setValidUsageOrError(usage):
            return None
        if usage == QUOTED_MATCH:
            self.usage = QUOTED_EVAL
            return EMPTY_SET
        elif usage == QUOTED_EVAL or usage == FORMAL:
            # don't see the variable as being used
            return EMPTY_SET
        var = self._value
        context.recordVarUsage(self, var)
        if vbbefore is None:
            return EMPTY_SET
        if usage == TERM_EVAL:
            if var not in vbbefore:
                context.spu.err(E222VarNotBound(self, var))
        elif usage == TERM_MATCH:
            if var in vbbefore:
                self.usage = TERM_EVAL
            elif var.name.startswith("$$"):
                context.spu.err(E223OuterVarNotBound(self, var))
        elif usage == VARLIST:
            if var in vbbefore:
                context.spu.err(E234VarAlreadyBound(self, var))
        else:
            raise Exception("Invalid usage") # should never reach this
        return Set((var,))              # singleton

    def revalidate(self, context, vbbefore):
        #print "revalidate", self.annotated()
        if self.usage == FORMAL:
            var = self._value
            context.recordVarUsage(self, var)
            if var not in vbbefore:
                context.spu.err(E235IOVarNotBound(self, var))


class ExprLocalVariable(ExprVariable):
    __slots__ = ()
    impKey = IMP_KEY_LOCAL_VARIABLE
    description = "variable"

    validUsages = [TERM_EVAL, TERM_MATCH, QUOTED_EVAL, QUOTED_MATCH, FORMAL, VARLIST]

    # runtime

    def varlist(self, agent, formalBindings, actualBindings, zitem):
        val = termEvalOpt(agent, actualBindings, zitem)
        if val is None:             # actual param not evaluable
            return False
        else:
            # TODO: The following could be more efficient, it may not
            # need to look up the implementation.
            return termMatch(agent, formalBindings, self, val)



class ExprCapturedVariable(ExprVariable):
    __slots__ = ()
    impKey = IMP_KEY_CAPTURED_VARIABLE
    description = "captured variable"
    
    validUsages = [TERM_EVAL, TERM_MATCH, QUOTED_EVAL, QUOTED_MATCH]




class ExprCompound(Expr):
    __slots__ = (
        "__weakref__",
        )

    indexCompound = True

    def __init__(self, start, end, args):
        Expr.__init__(self, start, end, tuple(args))

    def __restore__(self):
        Expr.__restore__(self)
        r = ref(self)
        for arg in self._value:
            if not (arg.parentref is noneRef): raise AssertionError
            arg.parentref = r

    def components(self):
        return self._value

    def __getitem__(self, index):
        return self._value[index]

    def __len__(self):
        return len(self._value)

    def __nonzero__(self):
        return True
        #raise Exception("Coercing a ExprCompound to a boolean is ambiguous")

    def keyget0(self, keystring):
        for elt in self._value:
            functor = elt.functor
            if functor and functor.name == keystring:
                #print "keyget0(%r, %r)->%r"%(self, keystring, elt._value[0])
                return elt._value[0]
        else:
            #print "keyget0(%r, %r)->None"%(self, keystring)
            return None

    def revalidate(self, context, vbbefore):
        #print "revalidate", self.annotated()
        usage = self.usage
        if usage == FORMALS or usage == CUE or usage == CUE_LIST:
            for arg in self._value:
                arg.revalidate(context, vbbefore)

    def checkUsages(self, spu, pspu):
        for sub in self:
            sub.checkUsages(spu, pspu)

    def getCompoundDecl(self, context, activity, usage, functorSym):
        """Get Decl for functor symbol functorSym.
        Possibly use DEFAULT_DECL if reasonable.
        Return EMPTY_SET if no further processing is needed now.
        Return None on fatal error.
        Set self.impKey."""
        # TODO: fold the two other methods into this one


    def validate(self, context, vbbefore, activity, reqUsage):
        if not self._setValidUsageOrError(reqUsage):
            return None
        decl = self.getCompoundDecl(context, activity, reqUsage, self.functor)
        if decl is None or decl == EMPTY_SET:
            return decl
        # At this point we have found a declaration for self.functor
        # CHECK FOR ANY MODE MATCHING REQUSAGE
        mode = decl.optMode(reqUsage)
        if mode is None:
            # TODO: This needs explaining
            symStr = EXPR_IMPS.get(self.impKey, self.impKey)
            typeStr = reqUsagePrintableName(reqUsage)
            context.spu.err(E226NoDeclaredUsage(self, symStr, typeStr))
            # Don't process further down
            return None
        # CHECK THE SIGNATURE & ENUMERATE THE ELEMENTS
        elements = mode.orderedElements(self, keynameFn(decl.USES_KEYWORDS))
        if isinstance(elements, basestring):
            symStr = EXPR_IMPS.get(self.impKey, self.impKey)
            context.spu.err(E227MismatchSig(self, symStr, elements))
            return None
        # PROCESS COMPONENTS IN THE CORRECT ORDER
        # Note: since we sometimes reference elements of the following using
        # negative indices, we need to start with the list being the right length.
        # We cannot build it by appending on each iteration.
        subfrees = [None for x in elements]
        subvbafters = [None for x in elements]
        for indexkey, sub in elements:
            # work out the variables bound before sub
            subprior = decl.combiner.prior(indexkey)
            if subprior is None:
                subvbbefore = vbbefore
            else:
                subvbbefore = subvbafters[subprior]
            # determine the activity status of sub
            subactivity = RUNTIME       # default, unless ...
            if activity == LOADTIME:
                activitymode = decl.optMode(LOADTIME)
                if activitymode is None \
                       or activitymode[indexkey] == LOADTIME:
                    subactivity = LOADTIME
            # determine the required kind of sub
            subusage = mode[indexkey]
            # compute the Result for sub
            # subvbbefore=None if vars unknown
            if sub is not None:
                subfree = sub.validate(context, subvbbefore, subactivity, subusage)
            else:
                subfree = EMPTY_SET
            subfrees[indexkey] = subfree
            if subvbbefore is not None and subfree is not None:
                subvbafters[indexkey] = subvbbefore.union(subfree)

        # if we don't what the previously bound variables are,
        # can't determine what variables are free here
        if vbbefore is None:
            return None
        
        # CHECK FOR MATCHING MODE
        bestMode = decl.checkMode(reqUsage, elements)
        if bestMode is None:      # (satisfies %-mode but not =-modes)
            typeStr = reqUsagePrintableName(reqUsage)
            actual = "".join([sub.usage for _ik, sub in elements])
            needed = " or ".join([mode.source for mode in decl.modes \
                                  if mode.resultSatisfies(reqUsage, False)])
            context.spu.err(E228InvalidSpecialMode(self, typeStr, needed, actual))
            return None
        usage = bestMode.getResult()
        self.usage = usage              # may be stronger than reqUsage
        if None in subfrees:            # cannot validate some components
            return None
        allvars = union_of(subfrees)
        # revalidate to check output formals at the top of each context
        if isinstance(self, ExprStructureBrace):
            #print "REVALIDATE", self
            for _i, elt in elements:
                if elt is not None:
                    elt.revalidate(context, allvars)
        # find variables limited to this scope
        alternatives = decl.combiner.varsAlternatives(subfrees)
        if alternatives is None or len(alternatives) <= 1:
            hidden = EMPTY_SET
        else:
            hidden = allvars.difference(intersection_of(alternatives)).difference(vbbefore)
        freevars = allvars.difference(hidden)
        # check the variable usage is consistent with the declaration
        varsError = decl.combiner.validateVars(subfrees, vbbefore, freevars, hidden)
        if varsError:
            varsError.setExpr(self)
            context.spu.err(varsError)
            return None
        # set the scope of the variables limited to this scope
        for v in hidden:
            context.setVarScope(v, self)
        #print "SUBFREES", self, subfrees
        #print "SUBVBAFTERS", self, subvbafters
        return freevars


    # runtime

    def varlist(self, agent, formalBindings, actualBindings, zexpr):
        for elt, zitem in zip(self._value, zexpr):
            if not elt.varlist(agent, formalBindings, actualBindings, zitem):
                return False
        else:
            return True

    def __setstate__(self, state):
        Expr.__setstate__(self, state)
        # Recreate the weak reference to itself
        r = ref(self)
        for arg in self._value:
            if not (arg.parentref is noneRef): raise AssertionError
            arg.parentref = r
            

class ExprList(ExprCompound):
    __slots__ = ()
    def category(self):
        return LIST
    impKey = IMP_KEY_LIST

    description = "list"
    
    def asValue(self):
        return List([a.asValue() for a in self._value])
    def annotated(self):
        return (self.usage or "") + "[" + " ".join([x.annotated() for x in self]) + "]"

    validUsages = [TERM_EVAL, TERM_MATCH, QUOTED_EVAL, QUOTED_MATCH, \
                   TASK_EXECUTE, CUE_LIST, FORMALS, VARLIST, \
                   STAGE_ONE_KIND, PRED_UPDATE] # these for stage one processing

    CUE_LIST_DECL = NoKeyDecl(IMP_KEY_LIST, ["l=c"])
    FORMALS_DECL = Decl(None, ["f=*g:g"], sigkeys=["rest:"])
    LIST_DECL = NoKeyDecl(IMP_KEY_LIST, ["-=*-", "+=*+", "k=*k", "q=*q", "x=*x", "v=*v", "1=*1"],
                          combiner="spark.internal.parse.combiner.SERIAL")

    def getCompoundDecl(self, context, activity, usage, functor):
        # Note, functor = None for lists
        if usage == CUE_LIST:
            return self.CUE_LIST_DECL
        elif usage == FORMALS:
            return self.FORMALS_DECL
        else:
            return self.LIST_DECL

    def revalidate(self, context, vbbefore):
        # TODO: Check if ExprCompound.revalidate is sufficient
        #print "revalidate", self.annotated()
        usage = self.usage
        if usage == CUE_LIST or usage == FORMALS:
            for arg in self._value:
                arg.revalidate(context, vbbefore)
    # runtime
#     def quoted_eval(self, agent, bindings):
#         args = [x.quoted_eval(agent, bindings) for x in self._value]
#         return List(args)

#     def quoted_match(self, agent, bindings, value):
#         if not isList(value) \
#            or len(value) != len(self._value):
#             return False
#         for i,arg in enumerate(self._value):
#             if not arg.quoted_match(agent, bindings, value[i]):
#                 return None
#         else:
#             return True

    def cue_list(self, agent, bindings, actualBindings, zexpr, match): #UNUSED?
        return self[0].cue_match(agent, bindings, actualBindings, zexpr, match)


class ExprStructure(ExprCompound):
    __stateslots__ = (
        "functor",                      # symbol
        "impKey",
        )
    __slots__ = __stateslots__
    def category(self):
        return STRUCTURE

    def __init__(self, start, end, functor, args):
        ExprCompound.__init__(self, start, end, args)
        self.functor = functor
        self.impKey = IMP_KEY_STRUCTURE # default is to be quoted

    def asValue(self):
        return self.functor.structure(*[a.asValue() for a in self._value])

    def getResolvedSymbol(self):
        return self.impKey

    def setResolvedSymbol(self, resolvedSymbol):
        self.impKey = resolvedSymbol

    resolvedSymbol = property(getResolvedSymbol, setResolvedSymbol)

    QUOTED_DECL = NoKeyDecl(IMP_KEY_STRUCTURE, ["k=*k", "q=*q"])
    DEFAULT_DECL = Decl(None, ["-=*-", "+=*+", "s=*-", "r=*-", "u=*+", "a=*+", "d=*-", "f=*g"])

    def getCompoundDecl(self, context, activity, usage, functor):
        decl = None
        if usage in (QUOTED_EVAL, QUOTED_MATCH):
            if functor != PREFIX_COMMA_SYMBOL:
                decl = self.QUOTED_DECL
        elif usage == FORMAL:
            if functor == PREFIX_MINUS_SYMBOL and len(self) == 1:
                return EMPTY_SET        # delay until revalidate is called
            if functor != PREFIX_PLUS_SYMBOL:
                context.spu.err(E229InvalidFormalSpec(self))
                return None
        if decl is None:
            idname = functor.name
            declsym = context.spu.findCacheId(idname, True)
            if isinstance(declsym, Decl):
                decl = declsym
                self.impKey = declsym.asSymbol()
            else:
                decl = self.DEFAULT_DECL
                self.impKey = declsym
                if activity == LOADTIME and not usage == DECLARATION:
                    msg = "Symbol must be defined before it's use at runtime"
                    context.spu.addUndeclaredLoadUse(self)
                    #context.spu.recordError(F2, self, msg)
        else:
            self.impKey = decl.asSymbol()
        if usage == DECLARATION:
            return EMPTY_SET
        else:
            return decl
        
    def checkUsages(self, spu, pspu):
        # usage = None for keywords
        if self.usage not in (QUOTED_EVAL, QUOTED_MATCH, DECLARATION, FORMAL, None):
            decl = spu.stageFourDecl(self.functor.name, self, pspu)
            if decl:
                # any non-term usages in self means this was special
                for sub in self:
                    if sub.usage != TERM_EVAL and sub.usage != TERM_MATCH:
                        # short circuit all further testing at this level
                        #debug("special usage: %s due to %s %s", self, sub, sub.usage)
                        ExprCompound.checkUsages(self, spu, pspu)
                        return
                mode = decl.optMode(self.usage)
                if mode is None:
                    # TODO: need better error message
                    sym = decl.asSymbol()
                    typeStr = reqUsagePrintableName(self.usage)
                    spu.err(E421InvalidUsage(self, sym, typeStr))
                #@-noPostCheck# elif True:
                #@-#     pass                # eliminate checks
                else:
                    elements = mode.orderedElements(self, keynameFn(decl.USES_KEYWORDS))
                    if isinstance(elements, basestring):
                        symStr = EXPR_IMPS.get(self.impKey, self.impKey)
                        spu.err(E423MismatchSig(self, symStr, elements))
                    elif not decl.checkMode(self.usage, elements):
                        # TODO: need better error message
                        #raise LowError("E422")
                        sym = decl.asSymbol()
                        typeStr = reqUsagePrintableName(self.usage)
                        spu.err(E422InvalidMode(self, sym, typeStr, mode))
                    else:
                        pass
                        #debug("satisfied by: %s %s", self, mode)
        ExprCompound.checkUsages(self, spu, pspu)
        
    def revalidate(self, context, vbbefore):
        ExprCompound.revalidate(self, context, vbbefore)
        if self.usage == FORMAL:
            if self.functor == PREFIX_MINUS_SYMBOL and len(self) == 1:
                # mode g=+
                decl = context.spu.findCacheId(PREFIX_MINUS_SYMBOL.name, True)
                if not isinstance(decl, Decl):
                    raise AssertionError, "No declaration of '-' prefix"
                self.impKey = decl.asSymbol()
                self[0].validate(context, vbbefore, RUNTIME, TERM_EVAL)
        
    # runtime
        
    def eenter(self, agent, tframe):
        imp = tframe.getBaseBindings().bImp(agent, self)
        return imp.tenter(agent, tframe, self)
    def eresume(self, agent, tframe):
        imp = tframe.getBaseBindings().bImp(agent, self)
        return imp.tresume(agent, tframe, self)
    def echild_complete(self, agent, tframe, index, result):
        imp = tframe.getBaseBindings().bImp(agent, self)
        return imp.tchild_complete(agent, tframe, self, index, result)

    
class ExprStructureColon(ExprStructure):
    __slots__ = ()
    description = "keyword-structure"
    def annotated(self):
        return  ((self.usage and (self.usage + ".")) or "") + self.functor.name + " ".join([""]+[x.annotated() for x in self])

    validUsages =  [QUOTED_EVAL, QUOTED_MATCH, TASK_EXECUTE, FORMALS, CUE, STAGE_ONE_KIND,
                    PRED_UPDATE         # since STAGE_ONE_KIND is stronger than PRED_UPDATE
                    ]

    # runtime

    #def task_execute(...):

    #def cue_match(self, agent, bindings): ??? # e.g., do:

class ExprStructureBrace(ExprStructure):
    __stateslots__ = (
        "captured",                    # captured variables {ov:iv}
        "filename",                     # used to interpret ids
        "scopes",
        )
    __slots__ = __stateslots__
    
    description = "brace-structure"
    def annotated(self):
        return self.usage + "{" + self.functor.name[:-2] + " ".join([""]+[x.annotated() for x in self]) + "}"

    validUsages =  [TERM_EVAL, TERM_MATCH, QUOTED_EVAL, QUOTED_MATCH, FORMALS, STAGE_ONE_KIND, PRED_UPDATE, PRED_RETRACTALL]

    _oldContextUsages = (QUOTED_EVAL, QUOTED_MATCH, FORMALS)

    def introducesNewContext(self):
        return self.usage not in self._oldContextUsages

    def validate(self, context, vbbefore, activity, usage):
        if usage in self._oldContextUsages:
            return ExprStructure.validate(self, context, vbbefore, activity, usage)
        else:
            if vbbefore is None:
                innervbbefore = EMPTY_SET
            else:
                innervbbefore = Set([ov.innerVersion() for ov in vbbefore])
            innercontext = context.subContext(self)
            # Note: usually whatever is inside the braces is executed
            # at RUNTIME, but there is a slight chance that it will be
            # executed at LOADTIME - for example, consider the fact:
            # (P (applyfun {fun [] 1}))
            r = ExprStructure.validate(self, innercontext, innervbbefore, activity, usage)
            if r is None:
                return None
            else:
                outerInner = {}
                for iv in r:
                    innercontext.setVarScope(iv, self)
                    ov = iv.outerVersion()
                    if ov:
                        outerInner[ov] = iv
                innercontext.checkVarUsages()
                self.captured = outerInner
                self.filename = self.getSPU().filename
                scopes = {}
                for var, usage in innercontext._varScope.items():
                    if usage[-1] == self:
                        scopes[var] = None
                    else:
                        scopes[var] = usage[-1]
                self.scopes = scopes
                return Set(outerInner)

    
class ExprStructureOrdinary(ExprStructure):
    __slots__ = ()
    description = "structure"
    def annotated(self):
        return (self.usage or "") + "(" + " ".join([self.functor.name]+[x.annotated() for x in self]) + ")"

    validUsages = [TERM_EVAL, TERM_MATCH, PRED_SOLVE, PRED_UPDATE, PRED_RETRACTALL,\
                   PRED_ACHIEVE, ACTION_DO, QUOTED_EVAL, QUOTED_MATCH, \
                   FORMALS, FORMAL, DECLARATION]

    # runtime

    #def pred_achieve(self, agent, bindings): ???
    #def action_do(self, agent, tframe): ???


def keynameExpr(expr):
    if isinstance(expr, ExprStructureColon):
        return expr.functor.name
    else:
        return None

def returnNone(expr):
    return None

def keynameFn(use_keywords):
    if use_keywords:
        return keynameExpr
    else:
        return returnNone

################

    
class ExprConstructor(Constructor):
    __slots__ = ()
    def createSymbol(self, start, end, string):
        return ExprSymbol(start, end, Symbol(string))
    def createVariable(self, start, end, string):
        var = Variable(string)
        if var.isLocal():
            return ExprLocalVariable(start, end, var)
        else:
            return ExprCapturedVariable(start, end, var)
    def createStructure(self, start, end, f, args):
        functor = Symbol(f)
        fstring = functor.name
        if functor.isBrace():
            return ExprStructureBrace(start, end, functor, args)
        elif functor.isTag():
            return ExprStructureColon(start, end, functor, args)
        else:
            return ExprStructureOrdinary(start, end, functor, args)
    def createList(self, start, end, elements):
        return ExprList(start, end, elements)
    def createString(self, start, end, string):
        return ExprString(start, end, string)
    def createInteger(self, start, end, integer):
        return ExprInteger(start, end, integer)
    def createBigInteger(self, start, end, integer):
        return ExprInteger(start, end, integer)
    def createFloat(self, start, end, float):
        return ExprFloat(start, end, float)
    def start(self, obj):
        return obj.start
    def end(self, obj):
        return obj.end

    def asFloat(self, obj):
        return obj.asFloat()
    
    def asInteger(self, obj):
        return obj.asInteger()
    
    def category(self, obj):
        return obj.category()

    def functor(self, obj):
        f = obj.functor
        if f is not None:
            return f.name
        else:
            return None

    def asString(self, obj):
        return obj.asString()
    
    def components(self, obj):
        return obj.components()

EXPR_CONSTRUCTOR = ExprConstructor()

################################################################

################################################################


def varsBeforeAndHere(rootexpr):
    "Return info on free vars: (bound before, bound here, all)"
    # TODO: where is this used?
    cexpr = rootexpr
    while isinstance(cexpr, Expr) and not cexpr.introducesNewContext():
        cexpr = cexpr.getParent()
    if isinstance(cexpr, Expr):
        scopes = cexpr.scopes
    else:           # TODO: need to get scope for string-sourced exprs
        scopes = {}
    free = Set()
    bound = Set()
    def _varsFreeBound(expr):
        "Collect the free variables and those bound within this expr"
        if expr.introducesNewContext():
            free.union_update(expr.captured)
        elif isinstance(expr, ExprVariable):
            if expr.usage not in (QUOTED_EVAL, QUOTED_MATCH, FORMALS):
                free.add(expr._value)
                if expr.usage == TERM_MATCH:
                    bound.add(expr._value)
        elif isinstance(expr, ExprCompound):
            for subexpr in expr:
                _varsFreeBound(subexpr)
            for var in bound:
                if scopes.get(var) == expr:
                    free.remove(var)
    _varsFreeBound(rootexpr)
    bound.intersection_update(free) # removed scoped variables
    return free.difference(bound), bound, free

################################################################

class ExprSimpleImp(Imp):
    __slots__ = ()
    
    def call(self, agent, bindings, expr):
        return expr._value
    
    def match_inverse(self, agent, bindings, expr, value):
        return expr._value == value

    def quotedEval(self, agent, bindings, expr):
        return expr._value

    def quotedMatch(self, agent, bindings, expr, value):
        return expr._value == value

class ExprSymbolImp(Imp):
    __slots__ = ()
    
    def call(self, agent, bindings, expr):
        return agent.getDecl(expr.resolvedSymbol).asSymbol()

    def match_inverse(self, agent, bindings, expr, value):
        return agent.getDecl(expr.resolvedSymbol).asSymbol() == value

    def quotedEval(self, agent, bindings, expr):
        return expr._value

    def quotedMatch(self, agent, bindings, expr, value):
        return expr._value == value


class ExprLocalVariableImp(Imp):
    __slots__ = ()

    def call(self, agent, bindings, expr):
        return bindings.getVariableValue(agent, expr._value)

    def match_inverse(self, agent, bindings, expr, value):
        if expr.usage == TERM_EVAL:
            return bindings.getVariableValue(agent, expr._value) == value
        else:
            return bindings.matchVariableValue(agent, expr._value, value)

    def quotedEval(self, agent, bindings, expr):
        return expr._value

    def quotedMatch(self, agent, bindings, expr, value):
        return expr._value == value

    def formal(self, agent, formalBindings, expr, actualBindings, zitem, match):
        if match:
            formalBindings.setConstraint(agent, expr._value, actualBindings, zitem)
            return True
        else:
            val = formalBindings.getVariableValue(agent, expr._value)
            return termMatch(agent, actualBindings, zitem, val)

    
class ExprCapturedVariableImp(Imp):
    __slots__ = ()

    def call(self, agent, bindings, expr):
        return bindings.getCapturedValue(agent, expr._value)

    def match_inverse(self, agent, bindings, expr, value):
        return bindings.getCapturedValue(agent, expr._value) == value

    def quotedEval(self, agent, bindings, expr):
        return expr._value

    def quotedMatch(self, agent, bindings, expr, value):
        return expr._value == value


class ExprListImp(Imp):
    __slots__ = ()

    def call(self, agent, bindings, expr):
        return List([termEvalErr(agent, bindings, elt) \
                                  for elt in expr])

    def match_inverse(self, agent, bindings, expr, value):
        if not isList(value) or len(value) != len(expr):
            return False
        for (elt,velt) in zip(expr, value):
            if not termMatch(agent, bindings, elt, velt):
                return False
        else:
            return True

    def quotedEval(self, agent, bindings, expr):
        args = [quotedEval(agent, bindings, x) for x in expr]
        return List(args)

    def quotedMatch(self, agent, bindings, expr, value):
        if not isList(value) \
           or len(value) != len(expr):
            return False
        for i,arg in enumerate(expr):
            if not quotedMatch(agent, bindings, arg, value[i]):
                return None
        else:
            return True

    def tenter(self, agent, tframe, zexpr):
        if len(zexpr) > 0:
            return tframe.tfpost_child(agent, 0)
        else:
            return tframe.tfcompleted(agent, SUCCESS)
        
    def tresume(self, agent, tframe, zexpr):
        # Special case of top level task in a TaskExprTFrame:
        # tenter is never called directly
        # the first call on the taskexpr is a tresume
        return self.tenter(agent, tframe, zexpr)

    def tchild_complete(self, agent, tframe, zexpr, index, result):
        next = index + 1
        if result == SUCCESS and next < len(zexpr):
            return tframe.tfpost_child(agent, next)
        else:
            return tframe.tfcompleted(agent, result)

    def conclude(self, agent, bindings, zexpr, kbResume=False): # for loading
        # No conclude effects are currently allowed
        pass




class ExprStructureImp(Imp):
    __slots__ = ()

    def quotedEval(self, agent, bindings, expr):
        args = [quotedEval(agent, bindings, x) for x in expr]
        return expr.functor.structure(*args)

    def quotedMatch(self, agent, bindings, expr, value):
        if not isStructure(value) \
           or value.functor != expr.functor or len(value) != len(expr):
            return False
        for i,arg in enumerate(expr):
            if not quotedMatch(agent, bindings, arg, value[i]):
                return None
        else:
            return True



EXPR_IMPS = {IMP_KEY_STRING:ExprSimpleImp,
             IMP_KEY_INTEGER:ExprSimpleImp,
             IMP_KEY_FLOAT:ExprSimpleImp,
             IMP_KEY_SYMBOL:ExprSymbolImp,
             IMP_KEY_LOCAL_VARIABLE:ExprLocalVariableImp,
             IMP_KEY_CAPTURED_VARIABLE:ExprCapturedVariableImp,
             IMP_KEY_LIST:ExprListImp,
             IMP_KEY_STRUCTURE:ExprStructureImp}

# How to translate from an impKey into something to put into an error message.
# A symbol not in IMP_KEY_NAME is used as itself.

IMP_KEY_NAME = {IMP_KEY_LIST: "<List>",
                IMP_KEY_STRUCTURE: "<QuotedStructure>"}
