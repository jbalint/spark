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
from spark.internal.version import *

from spark.internal.engine.core import Internal

#
# Instrumentation Points for persisting/tracing
# - allow for easier configuration/manipulation of when/where agent is persisted
#   and tracing agent 
#

PRE_USER_MODULE_LOAD   = 0 #user-directed module load about to be initiated
POST_USER_MODULE_LOAD  = 1 #user-directed module load complete
OBJECTIVE_COMPLETED    = 2
EXTERNAL_COMMUNICATION = 4 #communication with an external entity (e.g. OAA) #TODO: unused
USER_PERSIST_COMMAND   = 5 #user-directed persist request
SPARK_SHUTDOWN         = 6 
NEWFACT_COMPLETED      = 7 # completion of newfact procedure
_LARGEST_POINT = 8 #make sure this is set higher than any of the constants above

# - PERSIST_POINTS: configures which instrumentation events are triggers for persisting

_PERSIST_POINTS = [False for i in range(0,_LARGEST_POINT)]
_PERSIST_POINTS[PRE_USER_MODULE_LOAD]   = True
_PERSIST_POINTS[POST_USER_MODULE_LOAD]  = True
_PERSIST_POINTS[OBJECTIVE_COMPLETED]    = True
_PERSIST_POINTS[EXTERNAL_COMMUNICATION] = False
_PERSIST_POINTS[USER_PERSIST_COMMAND]   = True
_PERSIST_POINTS[SPARK_SHUTDOWN]         = True
_PERSIST_POINTS[NEWFACT_COMPLETED]      = True # likely to be very many 

_PPLEN = len(_PERSIST_POINTS)

_persistPointFn = None

def set_persist_point_handler(handlerFn):
    global _persistPointFn
    _persistPointFn = handlerFn

def report_instrumentation_point(agent, point):
    if is_persist_point(point) and _persistPointFn:
        #perist within the agent executor loop
        agent.add_internal(InternalPersist(_persistPointFn, point))

def is_persist_point(point):
    """return True if the agent should be persisted after passing
    specified persistence point"""
    if point < 0 or point > _PPLEN:
        raise Exception("invalid persist point: %s"%point)
    return _PERSIST_POINTS[point]

#PERSIST: perform a persist operation using the agent Internal API
class InternalPersist(Internal):
    """An Internal that persists the agent knowledge base. The Internal
    mechanism guarantees that the knowledge base state is locked."""
    __slots__ = ("_persistPointFn", "_persistPoint", )

    def __init__(self, persistPointFn, persistPoint):
        self._persistPointFn = persistPointFn
        self._persistPoint = persistPoint
        
    def perform(self, agent):
        self._persistPointFn(agent, self._persistPoint)   
