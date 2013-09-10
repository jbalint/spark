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
def computeCycles(root, successors):
    finished = []
    companions = {}
    path = []
    _process(successors, [], companions, path, root)
    return companions

def _process(successors, complete, companions, path, node):
    #print "Processing", companions, path, node
    if node in path:                # we have found a cycle
        pos = path.index(node)
        #print "Found new cycle", path[pos:]
        group = None
        for cnode in path[pos:]:
            # for every other node in this cycle, merge the companions
            group = _merge_group(group, companions, cnode)
    elif node in complete and _subset(companions.get(node,()), complete):
        # every node in the companion group is complete
        #print "Pruning search under", node
        pass
    else:
        path.append(node)
        #print "successors", node, successors(node)
        for next in successors(node):
            _process(successors, complete, companions, path, next)
        path.pop()
        complete.append(node)

def _subset(seq1, seq2):
    for elt in seq1:
        if elt not in seq2:
            return False
    return True

def _merge_group(group, companions, cnode):
    """Merge group with the previously known companions of cnode,
    return the group (which should now be the companion list for
    everything in group) """
    # precondition: if group then forall x in group companions[x]==group
    if group is not None and cnode in group:
        return group
    #print "_merge_group", group, companions, cnode
    othergroup = companions.get(cnode)
    if group is None:
        if othergroup is None:
            group = [cnode]
            companions[cnode] = group
        else:
            group = othergroup
    elif othergroup is None:
        group.append(cnode)
        companions[cnode] = group
    elif group is not othergroup:
        for onode in othergroup:
            if onode not in group:
                #print " adding", onode
                group.append(onode)
            companions[onode] = group
    return group

TEST1 = {1:[2,3], 2:[1,4,5], 3:[6,7,8], 4:[1], 5:[], 6:[2], 7:[], 8:[8]}
ANSWER1 = {1: [1, 2, 4, 3, 6], 2: [1, 2, 4, 3, 6], 3: [1, 2, 4, 3, 6], 4: [1, 2, 4, 3, 6], 6: [1, 2, 4, 3, 6], 8:[8]}

def test():
    result = computeCycles(1, TEST1.get)
    if (result != ANSWER1): raise AssertionError
