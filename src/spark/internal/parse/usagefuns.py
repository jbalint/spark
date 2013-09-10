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
from __future__ import generators
from spark.internal.version import *
from spark.internal.common import SOLVED, NEWPM
from spark.internal.exception import NotLocatedError, LocatedError, CapturedError

def termEval(agent, bindings, expr):
    return bindings.bTermEval(agent, expr)

termEvalEnd = termEval

def termEvalP(agent, bindings, expr):
    return bindings.bTermEvalP(agent, expr)

def termEvalOpt(agent, bindings, expr):
    if bindings.bTermEvalP(agent, expr):
        return bindings.bTermEval(agent, expr)
    else:
        return None

def termEvalErr(agent, bindings, expr):
    if bindings.bTermEvalP(agent, expr):
        return bindings.bTermEval(agent, expr)
    else:
        raise LocatedError(expr, "Term not evaluable")

def termMatch(agent, bindings, expr, value):
    return bindings.bTermMatch(agent, expr, value)

def termMatchErr(agent, bindings, expr, value):
    if not bindings.bTermMatch(agent, expr, value):
        raise LocatedError(expr, "Term does not match the given value")

def quotedEval(agent, bindings, expr):
    return bindings.bQuotedEval(agent, expr)

def quotedMatch(agent, bindings, expr, value):
    return bindings.bQuotedMatch(agent, expr, value)

def entity(agent, bindings, expr):
    return bindings.bEntity(agent, expr)

def formal(agent, bindings, expr, actualBindings, actualExpr, match):
    imp = bindings.bImp(agent, expr)
    return imp.formal(agent, bindings, expr, actualBindings, actualExpr, match)

def formals(agent, formalBindings, formalExprs, actualBindings, actualExprs, match):
    # ignore functor, assume no keys or rest:
    for elt,zitem in zip(formalExprs, actualExprs):
        if not formal(agent, formalBindings, elt, actualBindings, zitem, match):
            return False
    else:
        #print "formalBindings=", formalBindings._variables
        return True


def predSolve(agent, bindings, expr):
    imp = bindings.bImp(agent, expr)
    try:
        if _tracing:
            _tracing.do_try(agent, bindings, expr)
            for x in imp.solutions(agent, bindings, expr):
                if x:
                    _tracing.do_succeed(agent, bindings, expr)
                    yield x
                    _tracing.do_retry(agent, bindings, expr)
            _tracing.do_fail(agent, bindings, expr)
        else:
            for x in imp.solutions(agent, bindings, expr):
                yield x
    except NotLocatedError:
        errid = NEWPM.recordError()
        raise CapturedError(expr, errid, "solving")


def predSolve1(agent, bindings, expr):
    imp = bindings.bImp(agent, expr)
    try:
        if _tracing:
            _tracing.do_try(agent, bindings, expr)
            x = imp.solution(agent, bindings, expr)
            if x:
                _tracing.do_succeed(agent, bindings, expr)
                return x
            _tracing.do_fail(agent, bindings, expr)
        else:
            return imp.solution(agent, bindings, expr)
    except NotLocatedError:
        errid = NEWPM.recordError()
        raise CapturedError(expr, errid, "solving")


def predUpdate(agent, bindings, expr):
    imp = bindings.bImp(agent, expr)
    try:
        return imp.conclude(agent, bindings, expr)
    except NotLocatedError:
        errid = NEWPM.recordError()
        raise CapturedError(expr, errid, "concluding")

    
def predRetractall(agent, bindings, expr):
    imp = bindings.bImp(agent, expr)
    try:
        return imp.retractall(agent, bindings, expr)
    except NotLocatedError:
        errid = NEWPM.recordError()
        raise CapturedError(expr, errid, "retracting")

def taskImp(agent, tframe, expr):
    bindings = tframe.getBaseBindings()
    imp = bindings.bImp(agent, expr)
    return imp
    
_tracing = None
def set_tracing(boolean):
    global _tracing
    if boolean:
        _tracing = TRACING
    else:
        _tracing = None
