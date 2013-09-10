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
raise AssertionError, "NO LONGER TO BE LOADED"

from spark.internal.source_locator import get_source_locator
from spark.internal.parse.basicvalues import Symbol
import cPickle
import os, sys, zlib

BINARY_EXTENSION = "spo"
must_find_file = get_source_locator()

def getPickledFilename(source):
    global BINARY_EXTENSION
    sourcefile = must_find_file(Symbol(source))
    compfile = sourcefile[:-6] + "." + BINARY_EXTENSION
    return compfile
    
def generateBinFile(spu):
    compfile = getPickledFilename(spu.filename)
    binFile = open(compfile, "wb")
    sourcefile = must_find_file(Symbol(spu.filename))
    modiftime = os.path.getmtime(sourcefile)
    cPickle.dump(modiftime , binFile, -1)
    pickledString = cPickle.dumps(spu,-1)
    compressedString = zlib.compress(pickledString, 1)
    cPickle.dump(compressedString , binFile, -1)
    binFile.close()
    return compfile

def readBinFile(filename):
    spu = None
    try:
        binFile = open(filename,"rb")
        sourcemodiftime = cPickle.load(binFile)
        compressedString = cPickle.load(binFile)
        spu = cPickle.loads(zlib.decompress(compressedString))
        binFile.close()
    except IOError, e:
        print "Error reading %s"%filename
    return spu
    
def isBinFileUpdate(source):
    try:
        global BINARY_EXTENSION
        sourcefile = must_find_file(Symbol(source))
        compfile = sourcefile[:-6] + "." + BINARY_EXTENSION
        modiftime1 = os.path.getmtime(sourcefile)
        if not os.path.exists(compfile): return False
        binFile = open(compfile,"rb")
        modiftime2 = cPickle.load(binFile)
        binFile.close()
        if modiftime1 == modiftime2: return True
    except IOError, e:
        print "Error reading %s"%soruce
    return False
    

def _ptest(x):
    s = cPickle.dumps(x, -1)
    y = cPickle.loads(s)
    return y
