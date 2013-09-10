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
from spark.internal.common import DEBUG
from spark.internal.exception import LowError

import os
import sys

debug = DEBUG(__name__)#.on()

################################################################
#
# path to SourceObject map
#
# We abstract out the notion of locating source files so that
# the persistence layer can substitute in different mechanisms

SPARK_SUFFIX = ".spark"
MODULE_ROOT = "_module"

def default__must_find_file(modpath):
    """locates SPARK-L sources files during normal SPARK agent
    operation. Uses SPARK_SUFFIX and MODULE_ROOT as implicit
    parameters for determining SPARK-L source naming scheme."""
    absname = modpath.name
    base = os.path.join(*absname.split("."))
    mod_path_ext = base + SPARK_SUFFIX
    dirmod_path_ext = os.path.join(base, MODULE_ROOT) + SPARK_SUFFIX
    #debug("Look for %s in %s", absname, sys.path)
    path = None
    for p in sys.path:                  # LOAD PATH is sys.path
        testpath = os.path.expanduser(os.path.join(p, mod_path_ext))
        #debug("trying %r - %s", testpath, os.path.isfile(testpath))
        if os.path.isfile(testpath):
            #print "found"
            return testpath
        testpath = os.path.expanduser(os.path.join(p, dirmod_path_ext))
        #debug("trying %r - %s", testpath, os.path.isfile(testpath))
        if os.path.isfile(testpath):
            #print "found"
            return testpath
    #raise LowError("Cannot find file %s.\nPath is %s", mod_path_ext, sys.path)
    raise LowError("Cannot find file %s."%mod_path_ext)

_must_find_file = default__must_find_file

def get_source_locator():
    return _must_find_file

def set_source_locator(must_find_file_fn):
    global _must_find_file    
    _must_find_file = must_find_file_fn

def default__must_find_dir(modulenameString, path=sys.path):
    """takes in a string module name (e.g. 'spark.lang.foo') and attempts to
    find the directory where that module would be installed. modules may not
    exist. note that this API is different from must_find_file (module name
    is a string rather than modpath)"""
    idx = modulenameString.rfind('.')
    if idx < 1:
       raise LowError("Cannot calculate directory path for SPARK module %s.\nModule may not be a root module"%modulenameString)
       #raise LowError("Cannot find calculate directory path for SPARK module %s.\nModule may not be a root module"%modulenameString)
    
    absname = modulenameString[0:idx]
    
    mod_path_ext = os.path.join(*absname.split(".")) 
    for p in path:                  # LOAD PATH is path
        testpath = os.path.expanduser(os.path.join(p, mod_path_ext))
        if os.path.isdir(testpath):
            return testpath
    raise LowError("Cannot find directory for SPARK module %s"%mod_path_ext)
    #raise LowError("Cannot find calculate directory path for SPARK module %s.\nPath is %s", \
    #               mod_path_ext, path)

_must_find_dir = default__must_find_dir

def get_dir_locator():
    return _must_find_dir

def set_dir_locator(must_find_dir_fn):
    """Override the method used to locate the directory in which a particular
    source file may be located. In general, don't expect this method to ever
    be called as must_find_dir is for creating new source files rather than
    locating existing ones (i.e. it is not affected by the persistence scheme)."""
    global _must_find_dir    
    _must_find_dir = must_find_dir_fn
