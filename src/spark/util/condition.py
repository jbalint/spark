from __future__ import generators
from spark.internal.version import *
from spark.internal.parse.usagefuns import *
from spark.pylang.implementation import Imp
from spark.internal.common import SOLVED

################################################################
# Conditional

class IfOnce(Imp):
    __slots__ = ()

    def solutions(self, agent, bindings, zexpr):
        if predSolve1(agent, bindings, zexpr[0]):
            return predSolve(agent, bindings, zexpr[1])
        else:
            return predSolve(agent, bindings, zexpr[2])

    def solution(self, agnt, bindings, zexpr):
        if predSolve1(agent, bindings, zexpr[0]):
            return predSolve1(agent, bindings, zexpr[1])
        else:
            return predSolve1(agent, bindings, zexpr[2])

    def conclude(self, agent, bindings, zexpr):
        if predSolve1(agent, bindings, zexpr[0]):
            predUpdate(agent, bindings, zexpr[1])
        else:
            predUpdate(agent, bindings, zexpr[2])

    def retractall(self, agent, bindings, zexpr):
        if predSolve1(agent, bindings, zexpr[0]):
            predRetractall(agent, bindings, zexpr[1])
        else:
            predRetractall(agent, bindings, zexpr[2])

class IfMultiple(Imp):
    __slots__ = ()

    def solutions(self, agent, bindings, zexpr):
        solutionExists = False
        for x in predSolve(agent, bindings, zexpr[0]):
            if x:
                solutionExists = True
                for y in predSolve(agent, bindings, zexpr[1]):
                    yield y
        if not solutionExists:
            for y in predSolve(agent, bindings, zexpr[2]):
                yield y

    def solution(self, agnt, bindings, zexpr):
        solutionExists = False
        for x in predSolve(agent, bindings, zexpr[0]):
            solutionExists = True
            if predSolve1(agent, bindings, zexpr[1]):
                return SOLVED
        if not solutionExists:
            return predSolve1(agent, bindings, zexpr[2])

    def conclude(self, agent, bindings, zexpr):
        # There should be no more than one solution to zexpr[0].
        # Let's assume there is at most one.
        if predSolve1(agent, bindings, zexpr[0]):
            predUpdate(agent, bindings, zexpr[1])
        else:
            predUpdate(agent, bindings, zexpr[2])

    def retractall(self, agent, bindings, zexpr):
        solutionExists = False
        for x in predSolve(agent, bindings, zexpr[0]):
            solutionExists = True
            predRetractall(agent, bindings, zexpr[1])
        if not solutionExists:
            predRetractall(agent, bindings, zexpr[2])
