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
"""
This module provides the ability to find elemnts of a list of things
sorted by the .index attribute.

Each element must have a class attribute .indexCompound being True if it contains elements itself or False if it doesn't.


"""
from __future__ import generators
from spark.internal.version import *

def binarySearch(sortedList, index):
    """Find the last element of sortedList that has .index <= index"""
    low = 0
    high = len(sortedList)
    while high - low > 1:
        mid = (high + low) // 2
        if sortedList[mid].index > index:
            high = mid
        else:
            low = mid
    return sortedList[low]
    
def recursiveBinarySearch(sortedTree, index):
    elt = binarySearch(sortedTree, index)
    while elt.index != index:
        if elt.indexCompound:
            elt = binarySearch(elt, index)
        else:
            return elt
    return elt

def setIndex(obj, index):
    "Set index of obj to index and set obj's "
    obj.index = index
    index = index + 1
    if obj.indexCompound:
        for elt in obj:
            index = setIndex(elt, index)
    return index
        
def preOrder(obj):
    yield obj
    if obj.indexCompound:
        for elt in obj:
            for x in preOrder(elt):
                yield x
