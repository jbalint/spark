#! /usr/bin/env python
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
import sys

import setrootlevel
setrootlevel.setrootlevel(2)

from spark.internal.version import *
from spark.internal.exception import Error, FailFailure, TestFailure

from spark.internal.engine.agent import Agent, SUCCESS

agent = Agent("Test")
agent.start_executor()

class PredExprsTestCase(unittest.TestCase):
    def runTest(self):
        self.testSimple()
        self.testPredClosure()
        self.testTask()

    def eval_eq(self, str1, str2):
        modname = "spark.tests.test_predexprs"
        val1 = agent.eval(str1, modname)
        val2 = agent.eval(str2, modname)
        self.failUnlessEqual(val1, val2)

    def invalid_val(self, valexpr, class_):
        modname = "spark.tests.test_predexprs"
        self.failUnlessRaises(class_, agent.eval, valexpr, modname)

    def task_failure(self, taskexpr, class_):
        modname = "spark.tests.test_predexprs"
        ext = agent.run(taskexpr, modname)
        self.failUnlessRaises(class_, ext.wait_result, 2)

    def task_success(self, taskexpr):
        modname = "spark.tests.test_predexprs"
        ext = agent.run(taskexpr, modname)
        self.failUnlessEqual(ext.wait_result(2), None)


    def testSimple(self):
        self.eval_eq('(+ 1 0)',
                     '1')
        self.eval_eq('(plus1 0)',
                     '1')
        self.eval_eq('(solutions [] (not (exists [$c $b] (p $c $b))))',
                     '[]')
        self.eval_eq('(sort (solutions [$a $b] (p $a $b)))',
                     '[[1 2] [2 3] [3 4]]')
        self.eval_eq('(sort (solutions [$a $b] (p1 $a $b)))',
                     '[[1 2] [2 3] [3 4]]')
        self.eval_eq('(sort (solutionspat [$a $b] (p $a $b) (+ $a $b)))',
                     '[3 5 7]')
        self.eval_eq('(sort (solutions [$a $b $c] (and (p $c $b) (q $b $a))))',
                     '[[3 2 1] [4 3 2]]')
        self.eval_eq('(sort (solutions [$x] (IntBetween 3 $x 7)))',
                     '[[3][4][5][6][7]]')
        self.eval_eq('(applyfun {fun [] 1})',
                     '1')
        self.eval_eq('(applyfun {fun [$x] (+ $x 1)} 3)',
                     '4')
        self.invalid_val('(solutions)', Error)
        self.invalid_val('(solutions 1 2 3 4 5)', Error)
        self.invalid_val('(solutions [] (not (p $free $free)))', Error)
        self.task_success('[do: (task1)]')

    def testPredClosure(self):
        self.eval_eq('(solutions [$y] (applypred {pred [$x] (= $x 1)} $y))',
                     '[[1]]')
        self.eval_eq('(solutions [$y] (exists [$c] (and (= $c {pred [$x] (= $x 1)}) (applypred $c $y))))',
                     '[[1]]')


    def testTask(self):
        self.task_failure('[fail: "x"]', FailFailure)
        self.task_failure('[context: (false)]', TestFailure)
        self.task_failure('[select:]', TestFailure)
        self.task_success('[]')
        self.task_success('[context: (true)]')
        self.task_success('[conclude: (q 9 9)]')
        self.task_success('[retract: (q 9 9)]')
        self.task_success('[contiguous: [conclude: (q 1 1)][context: (q $x $x)][conclude: (q (+ 1 $x)(+ 1 $x))][context: (q 2 2)]]')
        self.task_success('[retractall: [$x $y] (q $x $y)]')
        self.task_success('[forall: [$x] (IntBetween 1 $x 3) [conclude: (q $x (+ $x 1))]]')
        self.eval_eq('(sort (solutions [$a $b] (q $a $b)))',
                     '[[1 2] [2 3] [3 4]]')
        self.eval_eq('(sort (solutions [$a $b] (and (q $a $b) (= $b (+ $a 1)))))',
                     '[[1 2] [2 3] [3 4]]')
        self.task_success('[while: [$x $y] (and (q $x $y) (= $y (+ $x 1))) [retract: (q $x $y) conclude: (q $y $x)]]')
        self.eval_eq('(sort (solutions [$a $b] (q $a $b)))',
                     '[[2 1] [3 2] [4 3]]')
        self.task_success('[try: [] []]')
        self.task_success('[try: [fail: 1] [fail: 2] [] []]')
        self.task_success('[try: [fail: 1] [fail: 2] [fail: 3] [fail: 4] [] []]')
        
        




if __name__ == '__main__':
    #print __file__
    unittest.main()

def dotest():
    PredExprsTestCase().runTest()
    print "Test succeeded"
