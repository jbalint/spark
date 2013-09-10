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
#try:
#    from com.sri.oaa2.lib import LibOaa
#    from com.sri.oaa2.icl import IclTerm, IclList, IclStr
#except ImportError:
#    print "XXWARNING: Cannot access OAA Java packages - OAA interface will not work"
#from spark.io.oaa import get_oaa_connection, value_to_icl
#
#def get_oaa(agent):
#    oaa = get_oaa_connection(agent)
#    if not oaa:
#        raise Exception("oaa object is null, you may not be connected to the facilitator.")
#    return oaa
#
#def get_online_agents(agent):
#    oaa = get_oaa(agent)
#    OAAAGENTS = []
#    tTerm = IclTerm.fromString(True, "agent_data(Id,Type,ready,Sv,Name,Info)")
#    answers = IclList()
#    oaa.oaaSolve(tTerm, IclList(IclTerm.fromString(True, "block(true)")),answers)    
#    for i in range(answers.size()):
#        OAAAGENTS.append(answers.getTerm(i).getTerm(4).toIdentifyingString()) # Name is term #4.
#    return OAAAGENTS
#    
#def can_solve(agent, goal):
#    oaa = get_oaa(agent)
#    return oaa.oaaCanSolve(goal)
#
#    
#def oaa_set_trigger(agent,type,triggerterm,actionterm,params):
#    oaa = get_oaa(agent)
#    return oaa.oaaAddTrigger(value_to_icl(type), value_to_icl(triggerterm), value_to_icl(actionterm), value_to_icl(params))
#
#
#def get_agent_address(agent):
#    oaa = get_oaa(agent)    
#    address = oaa.oaaPrimaryAddress()
#    return address
#    
#def oaa_add_data(agent, clause, params):
#    oaa = get_oaa(agent)
#    return oaa.oaaAddData(clause, params)    
#    
#    
#def oaa_replace_data(agent, clause1, clause2, params):
#    oaa = get_oaa(agent)
#    return oaa.oaaReplaceData(clause1, clause2, params)
#    
#def oaa_remove_data(agent, clause, params):
#    oaa = get_oaa(agent)
#    return oaa.oaaRemoveData(clause, params)
#
# 
#
