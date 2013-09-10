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
from spark.internal.parse.basicvalues import objectId, value_str, inverse_eval
from spark.internal.source_locator import SPARK_SUFFIX
from spark.internal.repr.common_symbols import P_PersistenceIncarnation
from spark.internal.common import NEWPM

import os

#
# Common/utility functions for persisting SPARK state
# - separated out from spark.internal.persist in order to prevent circular imports
#


#
# Constants for persisting spark
#

#PERSIST_SPARK = False # Force SPARK to never use persistence
PERSIST_SPARK = True  # Allow SPARK to use persistence

#name of subdirectory to store persistence files in
DEFAULT_PERSIST_ROOT = os.path.expanduser('persist')
DEFAULT_PERSIST_SRC_ROOT = os.path.join(DEFAULT_PERSIST_ROOT, 'src')
DEFAULT_PERSIST_SRC_BACKUP_ROOT = os.path.join(DEFAULT_PERSIST_SRC_ROOT, 'backup')

#CONSOLE_SUFFIX = '._console'+SPARK_SUFFIX
ERRORS_SUFFIX = '.errors'

MAX_VERSIONS = 10 #arbitrary

_persistRoot = DEFAULT_PERSIST_ROOT
_persistSrc = DEFAULT_PERSIST_SRC_ROOT
_persistSrcBackup = DEFAULT_PERSIST_SRC_BACKUP_ROOT

#
# Internal variables/shared variables for persist/resume
#

_resuming = False

#location of persisted knowledge base for agent
AGENT_KB_MAP = {}

#list of current on-disk persisted knowledge bases (by agent)
#map {agent.name, List[paths]}
KB_WORKING_SET = {}

PERSISTED_LOAD_IDS = []

def get_persist_root_dir():
    return _persistRoot

def get_persist_src_dir():
    return _persistSrc

def get_persist_src_backup_dir():
    return _persistSrcBackup
    
def set_persist_root_dir(persistDir):
    global _persistRoot, _persistSrc, _persistSrcBackup
    _persistRoot = persistDir
    _persistSrc = os.path.join(_persistRoot, 'src')
    _persistSrcBackup = os.path.join(_persistSrc, 'backup')

def get_persist_incarnation_dirs():
    root = get_persist_root_dir()
    fileList = os.listdir(root)
    list = []
    for f in fileList:
        filePath = os.path.join(root, f)
        if f.startswith("agent.") and f.find(".kb2.") and os.path.isdir(filePath):
            list.append(filePath)
    return list
    
def get_persist_incarnation_dir(agentName, incarnation):
    #incarnation = agent.factslist0(P_PersistenceIncarnation)[0][0]
    d = os.path.join(_persistRoot, "agent.%s.kb2.%s"%(agentName, incarnation))
    return d

# Make sure persist/ directory exists as part of our initialization
def ensure_dir(dir):
    if os.path.isfile(dir):
        raise InternalException("Cannot create directory '%s': file is in the way"%dir)
    if not os.path.isdir(dir):
        print "Creating directory '%s'"%dir
        os.makedirs(dir)

# clear a persistence related dir, raising an exception if it fails
def clear_dir(dirPath):
    if os.path.exists(dirPath):
        fileList = os.listdir(dirPath)
        for f in fileList:
            try:
                filePath = os.path.join(dirPath, f)
                if os.path.isfile(filePath):
                    os.remove(filePath)
            except:
                #this is a fatal exception because it means that we cannot reliably
                #continue to run SPARK
                raise Exception("Unable to remove persisted file '%s'"%f)
    
def is_resuming():
    """Check to see whether or not SPARK is
    currently resuming from a persisted state"""
    return _resuming

def set_resuming(isResuming):
    global _resuming
    _resuming = isResuming

#RESUME:RELOADPROCESSMODELS: testable condition for PersistablePredImps so that they
#know if they can conclude their stuff
def is_resume_block_concludes():
    """make it easier for persistable predexprs to test whether or not
    they should be concluding facts into their mini-KB. If True, then the
    predexprs may NOT conclude into their KB"""
    return is_resuming() and not is_reload_process_models()

#RESUME:RELOADPROCESSMODELS: global flag to test whether or not we are reloading process models
_reloadProcessModels = None

def is_reload_process_models():
    """Returns True if the agent during resume is also reloading process models
    from disk. The status of this flag is not set until the resume procedures
    have initialized"""
    return _reloadProcessModels

def set_reload_process_models(reload):
    """set the resume flag: we are resuming, but we are also reloading the process
    models from the .spark files instead of the persisted sources"""
    global _reloadProcessModels
    _reloadProcessModels = reload

#wrapper around value_source_string for now
def persist_strrep(sparkData):
    val = value_str(inverse_eval(sparkData))
    if val is None:
        raise Exception("cannot create persistable representation for %s"%sparkData)
#     if val.startswith("<"):
#         NEWPM.recordLocation(val)
    return val

# def standard_write_persist_repr(imp, agent, output, arity):
#     "Handle writing the persist repr for most persistable predicates"
#     from spark.internal.repr.varbindings import optBZ
#     errors = []
#     b, z = optBZ([None]*arity)
#     fstr1 = "(%s "%imp.symbol.name
#     for solution in imp.solutions(agent, b, z):
#         if solution:
#             try:
#                 fstr2 = " ".join([persist_strrep(b.bTermEval(agent, x)) for x in z])
#                 output.write(fstr1)
#                 output.write(fstr2)
#                 output.write(")\n")
#             except AnyException, e:
#                 print "# ERROR PERSISTING (%s %s)"%(imp.symbol.name, " ".join([str(b.bTermEval(agent, x)) for x in z]))
#                 errid = NEWPM.displayError()
#                 #breakpoint()
#                 errors.append(e)
#     if errors:
#         raise Exception(" \n".join([str(ex) for ex in errors]))

def encodeModpath(module, modpath):
    """shared persist/resume routine for encoding a modpath/modname pair in a persisted source"""
    if module is None or module._modpath.name == modpath.name:
        return modpath.name
    return "%s%%%s"%(module._modpath.name, modpath.name)

def decodeModpath(encodedStr):
    """shared persist/resume routine for decoding an encoded modpath/modname pair in a persisted source"""
    if encodedStr.find('%') > -1:
        return encodedStr.split('%')
    return (encodedStr, encodedStr,)
