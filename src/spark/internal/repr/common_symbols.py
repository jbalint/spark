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
from spark.internal.version import *

from spark.internal.common import BUILTIN_PACKAGE_NAME
from spark.internal.parse.basicvalues import Symbol

def _s(x):
    return Symbol(BUILTIN_PACKAGE_NAME + "." + x)

P_NewFact = _s("NewFact")
P_Do = _s("Do")
P_Achieve = _s("Achieve")
P_Implementation = _s("Implementation")
P_LoadedFileFacts = _s("LoadedFileFacts")
P_LoadedFileObjects = _s("LoadedFileObjects")
P_ObjectProperty = _s("ObjectProperty")
P_ObjectPropertyChangeListener = _s("ObjectPropertyChangeListener")
P_PersistenceIncarnation = _s("PersistenceIncarnation")
ADVICE = _s("Advice")
CONSULT = _s("Consult")
SOAPI = _s("SOAPI")
GOAL_POSTED = _s("AdoptedTask")
GOAL_SUCCEEDED = _s("CompletedTask")
GOAL_TERMINATED = _s("TerminatedTask")
GOAL_FAILED = _s("FailedTask")
PROCEDURE_STARTED = _s("StartedProcedure")
PROCEDURE_STARTED_SYNCHRONOUS = _s("StartedProcedureSynchronous")
PROCEDURE_SUCCEEDED = _s("CompletedProcedure")
PROCEDURE_FAILED = _s("FailedProcedure")
APPLIED_ADVICE = _s("AppliedAdvice")
#P_Determined = _s("Determined")
P_Static = _s("Static")
P_Doc = _s("Doc")
P_Features = _s("Features")
P_Properties = _s("Properties")
P_ArgTypes = _s("ArgTypes")
P_Roles = _s("Roles")
P_NumRequiredArgs = _s("NumRequiredArgs")
P_RestArgsAllowed = _s("RestArgsAllowed")
P_RequiredArgNames = _s("RequiredArgNames")
P_RestArgNames = _s("RestArgNames")
P_ArgNames = _s("ArgNames")
P_ObjectExists = _s("ObjectExists")
P_ObjectState = _s("ObjectState")
P_ObjectNextId = _s("ObjectNextId")
