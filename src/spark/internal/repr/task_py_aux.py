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
#* "$Revision:: 131                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

from spark.internal.version import *
from spark.internal.repr.patexpr import *
from spark.internal.common import NEWPM
import types
from spark.internal.parse.basicvalues import Symbol, isSymbol, BACKQUOTE_SYMBOL

from spark.pylang.defaultimp import Structure


#TODO: need to unify with task_icl_aux.Meth.  Should
#both import from same place
# mode = None - use standard mode, and use constant for evaluables
class Meth(object):
    __slots__ = (
        #"evaluate_if_possible",
        "use_parent_bindings",
        )
    
    def __init__(self, use_parent_bindings):
        #self.evaluate_if_possible = evaluate_if_possible
        self.use_parent_bindings = use_parent_bindings

    def recurse_components(self, agent, bindings, patexpr, mode):
        return [self.recurse(agent, bindings, c, mode) \
                for c in patexpr]

    def recurse(self, agent, bindings, patexpr, mode):
        if not isinstance(patexpr, Pat):
            return self.unhandleable(agent, bindings, patexpr)
        # If the patexpr has a value, find it
        if mode is None:       # Use standard mode for this expression
            if patexpr.evalpx(agent, bindings):
                value = termEvalErr(agent, bindings, patexpr)
            else:
                value = None
        else:                   # Use special mode for this expression
            if patexpr.evaluable_given(mode):
                if patexpr.evalpx(agent, bindings):
                    value = termEvalErr(agent, bindings, patexpr)
                else:
                    value = termEvalEnd(agent, bindings, patexpr)
            else:
                value = None
        if isinstance(patexpr, NonAnonVarPatExpr):
            acc = patexpr.accessor
            if value is not None:
                return self.ground(acc.name, value)
            elif isinstance(acc,FirstBivarAccessor) \
                     and self.use_parent_bindings:
                newb = bindings.pat_bindings
                try:
                    newe = bindings.pat_zexpr[acc.bivar_index]
                except AttributeError:
                    return self.nonground(acc.name)
                return self.recurse(agent, newb, newe, None)
            else:
                return self.nonground(acc.name)
        elif value is not None:
            return self.constant(value)            
        elif isinstance(patexpr, ListPatExpr):
            elements = self.recurse_components(agent, bindings, patexpr, mode)
            return self.list(tuple(elements))
        elif isinstance(patexpr, CompoundPatExpr):
            args = self.recurse_components(agent, bindings, patexpr, mode)
            return self.struct(patexpr.funsym, tuple(args))
        elif isinstance(patexpr, AnonVarPatExpr):
            return self.anon(patexpr.name)
        elif isinstance(patexpr, ConstantPatExpr):
            return self.constant(patexpr.value)
        elif not isinstance(patexpr, PatExpr): # a funny zexpr thing
            return self.anon('$_')
        else:
            return self.unhandleable(self, agent, bindings, patexpr)

    # Redefine the following to get different behavior
    def struct(self, functor_sym, args):
        return Structure(functor_sym, args)
    def list(self, elements):
        return tuple(elements)
    def constant(self, value): # constant or (value if evaluate_if_possible)
        return BACKQUOTE_SYMBOL.structure(value)
    def ground(self, name, value):      # bound variable 
        return Symbol(name)
    def nonground(self, name):          # variable not bound to ground value
        return Symbol(name)
    def anon(self, name="$_"):
        return Symbol(name)
    def unhandleable(self, agent, bindings, patexpr):
        raise Exception("Cannot handle %s"%patexpr)

#not actually a struct, just a list embedded within a list
def makePyStruct(functor, elements):
    list = [functor]
    sublist = []
    for elt in elements:
        sublist.append(elt)
    list.append(sublist)
    return list
    
class PyConverter(Meth):
    
    def __init__(self, agent):
        Meth.__init__(self, True)
        
    def struct(self, functor_sym, args):
        functor_name = functor_sym.id
        return makePyStruct(functor_name, args)

    def list(self, elements):
        return elements

    def constant(self, value):
        return value

    def ground(self, name, value):
        return value

    def nonground(self, name):
        return name

    def anon(self, name):
        return "_"+name

    def value_to_py(self, value):
        return value

def do_task_py(agent, bindings, patexprs, kind, action_symbol, mode):
    con = PyConverter(agent)
    targs = []
    for patexpr in patexprs:
        if patexpr is None:
            val = "_"
        elif isinstance(patexpr, Pat):
            val = con.recurse(agent, bindings, patexpr, mode)
        else:
            val = con.value_to_py(patexpr)
        targs.append(val)
    return makePyStruct("task", \
                         [kind, \
                          action_symbol.name, \
                          targs, \
                          ()])

def task_pyMode(agent, task, mode):
    try:
        kind = task.kind_string()
        namesym = task.goalsym()
        bindings = task.getBindings()
        zexpr = task.getZexpr()
        patexprs = [zexpr[i] for i in range(len(zexpr))]
        if not (isinstance(kind, basestring)): raise AssertionError
        if not (isSymbol(namesym)): raise AssertionError
    except:
        NEWPM.displayError()
        return "<cannot handle task %s>"%task
    try:
        return do_task_py(agent, bindings, patexprs, kind, namesym, mode)
    except AnyException:
        NEWPM.displayError()
        return "<err: %s>"%task

def task_py_0(agent, task):
    return task_pyMode(agent, task, NO_VARS_BOUND)

def task_py(agent, task):
    return task_pyMode(agent, task, None)

def task_py_done(agent, task):
    return task_pyMode(agent, task, ALL_VARS_BOUND)
