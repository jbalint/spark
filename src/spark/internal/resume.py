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
from spark.internal.common import DEBUG, console, console_error, console_warning, console_debug, BUILTIN_PACKAGE_NAME
from spark.internal.exception import LowError
from spark.internal.common import NEWPM
from spark.internal.repr.common_symbols import P_LoadedFileObjects, P_PersistenceIncarnation

import sys
import os
import string

from spark.internal.source_locator import set_source_locator, default__must_find_file
from spark.internal.persist_aux import *
from spark.internal.engine.find_module import ensure_modpath_installed
#from spark.internal.repr.newkinds import TASKEXPR, STATEMENT
from spark.internal.parse.basicvalues import Symbol

debug = DEBUG(__name__).on()

# #list of (modpath, stringsource path) tuples [(Symbol,filepath)]
# # - the string source path is an optional path argument to a file
# #   containing SPARK-L code that is to be loaded into the agent,
# #   within the specified modpath.
# modpathLoadOrder = None

# #map of modpath absnames to file paths: {StringType, StringType}
# MODPATH_FILEPATH_MAP = {}

# #maps console unit loadids to the (expr, unit) object
# CONSOLE_SOURCE_ID_MAP = {}


###################################
# Resume initialization routines
#
# * Initialize data structures from
#   on-disk state
###################################


#boolean to indicate whether or not SPARK should resume its state from disk
_resumeState = None
#boolean to indicate whether or not SPARK should reload the process models from the src tree
_reloadProcessModels = False
#controls how the resume process interacts with the user. If set to non-interactive,
#SPARK will not as the user whether or not to process with resuming in the event of errors.
_isInteractive = False

def set_resume_params(resumeState, isInteractive):
    """because internal/init.py calls methods here, we cannot import the
    persist/resume parameters. we must instead rely on init.py to call
    this method and set these values"""
    global _resumeState
    _resumeState = resumeState
    _isInteractive = isInteractive

def get_persist_modpath_load_order(agent):
    filename = os.path.join(get_persist_root_dir(), agent.name+'.loadOrder')
    if not os.path.exists(filename):
        return [] #no persisted data
    f = open(filename, 'r')
    order = []
    try:
        l = f.readline().rstrip()
        while l:
            data = l.split(':')
            l = f.readline().rstrip()
            
            modpathname = data[1].rstrip()
            if data[0] == 'load':
                order.append( ('load', Symbol(modpathname), None, ) )
            elif data[0] == 'string':
                order.append( ('string', Symbol(modpathname), string.atoi(data[2]), ) )
    finally:
        f.close()
    #console_debug("MODPATH LOAD ORDER FOR %s: %s", agent.name, str(order))
    #clear the filename: cannot guarantee same load order on resume due to reloadProcessModels
    #os.remove(filename)
    return order

#I would like to make this more generic in the future, but for now we have lots
#of special cases for handling console sources
def get_console_source_expr_and_unit(loadid):
    """get the parsed expr and sparklunit associated with a parsed console source"""
    if CONSOLE_SOURCE_ID_MAP.has_key(loadid):
        return CONSOLE_SOURCE_ID_MAP[loadid]
    else:
        #we can't return None as we already None to indicate unparseable source units
        raise LowError("console source fragment is missing")

def clear_resume_data():
    #not too important, doesn't use up that much memory to keep this around
    MODPATH_FILEPATH_MAP.clear()
    CONSOLE_SOURCE_ID_MAP.clear()
    #global modpathLoadOrder
    #modpathLoadOrder = None

def _init_resume_data():
    """examine the on-disk persisted state and initialize necessary
    data structures for resuming SPARK agent state"""
    _examine_persisted_kbs()
#     _examine_persisted_sources()

def get_persisted_version_number():
    """return the spark version number for the persisted state"""
    path = os.path.join(get_persist_root_dir(), "sparkVersion")
    if not os.path.exists(path):
        return None
    f = open(path, 'r')
    version = f.read()
    f.close()
    return version
    
#harder to do correctly in multiagent model, so don't bother for now
#def clear_persist_init_data():
#    """free up load data used to resume from persisted state"""
#    global modpathLoadOrder
#    MODPATH_FILEPATH_MAP.clear()
#    CONSOLE_SOURCE_ID_MAP.clear()
#    modpathLoadOrder = None

def _examine_persisted_kbs():
    """initialize the AGENT_KB_MAP by examining the on-disk
    persisted state of knowledge bases"""
    AGENT_KB_MAP.clear()
    KB_WORKING_SET.clear()
    newest = {}

    persistRoot = get_persist_root_dir()
    if not os.path.exists(persistRoot):
        return
    fileList = os.listdir(persistRoot)
    if fileList is None or len(fileList) == 0:
        return
    for f in fileList:
        path = os.path.join(persistRoot, f)
        if not os.path.isfile(path):
            continue
        splits = f.split('.')
        #knowledge bases have the 'agent.agentName.kb.version' naming scheme
        # - agentName is allowed to have '.'s in it, so it may span multiple splits
        # - version indicator is ignored (use getmtime instead)
        if not splits or len(splits) < 4 or splits[-2] != 'kb':
            continue
        name = '.'.join(splits[1:-2])
        if not name or len(name) == 0: #sanity check
            continue 

        #initialize working set and newest
        modtime = os.path.getmtime(path)
        if not KB_WORKING_SET.has_key(name):
            KB_WORKING_SET[name] = []
            newest[name] = modtime
        KB_WORKING_SET[name].append(path)
        if modtime >= newest[name]:
            #choose newest as the latest version
            AGENT_KB_MAP[name] = path            
            newest[name] = modtime

# def _examine_persisted_sources():
#     """initialize the MODPATH_FILEPATH_MAP and modpathLoadOrder
#     by examining the on-disk persisted state of the .spark source
#     files"""
#     global modpathLoadOrder
#     MODPATH_FILEPATH_MAP.clear()
#     modpathLoadOrder = []

#     persistSrc = get_persist_src_dir()
#     if not os.path.exists(persistSrc):
#         return
#     fileList = os.listdir(persistSrc)
#     if fileList is None or len(fileList) == 0:
#         return
#     fileList.sort()
#     lastCounter = -1 #first counter value will be zero
#     global _reloadProcessModels
#     for f in fileList:
#         try:
#             persistFile = os.path.join(persistSrc, f)
            
#             if os.path.isdir(persistFile): #backup dir
#                 continue
            
#             splits = f.split('.')
#             #not really using counter yet, eventually want to store this in
#             #a list somewhere
#             counter = string.atoi(splits[0])
#             if counter != (lastCounter + 1):
#                 console_warning("persisted source directory is possibly corrupted. Appear to be missing a source file before '%s'", f)
#             PERSISTED_LOAD_IDS.append(counter)
#             lastCounter = counter

#             if f.endswith(CONSOLE_SUFFIX):
#                 (modname, modpath) = decodeModpath('.'.join(splits[1:-2]))
#                 modpathLoadOrder.append((counter, Symbol(modname), Symbol(modpath),os.path.join(persistSrc, f),))
#             else:
#                 #modpath is unique, modname is not
#                 (modname, modpath) = decodeModpath('.'.join(splits[1:-1]))
#                 MODPATH_FILEPATH_MAP[modpath] = f
#                 modpathLoadOrder.append((counter, Symbol(modname),Symbol(modpath),None,))
                
#                 #RESUME:RELOADPROCESSMODELS: check to see if we have a newer version of the file
#                 #if we set _reloadProcessModels to true, during the resume process we will
#                 #throwout all spark.lang.builtin data from the knowledge base and instead
#                 #populate it with the .spark data
#                 try:
#                     srcFile = default__must_find_file(Symbol(modpath))
#                     srcAge = os.path.getmtime(srcFile)
#                     persistAge = os.path.getmtime(persistFile)
#                     if not _reloadProcessModels and persistAge < srcAge:
#                         #TODO: don't use python print
#                         console("Newer version of %s found, reloading all process models", modpath)
#                         _reloadProcessModels = True
#                 except AnyException, e:
#                     #example errors: file no longer exists in source tree
#                     print "ERROR comparing files"
#                     raise e
#                     _reloadProcessModels = True
                
#         except AnyException, e:
#             console_warning("unrecognized file '%s' in persisted source directory, ignoring", f)
#             raise e
        
#     #inform persist_aux so rest of code can see
#     set_reload_process_models(_reloadProcessModels)
#     if _reloadProcessModels:
#         #remove all persisted sources and clean up loadids
#         copy = PERSISTED_LOAD_IDS[:]
#         for x in copy:
#             PERSISTED_LOAD_IDS.remove(x)
#         MODPATH_FILEPATH_MAP.clear()

#         persistSrcBackup = get_persist_src_backup_dir()
#         ensure_dir(persistSrcBackup)
#         clear_dir(persistSrcBackup)
#         fileList = os.listdir(persistSrc)
#         for f in fileList: #move to backup dir
#             persistPath = os.path.join(persistSrc, f)
#             if os.path.isdir(persistPath):
#                 continue
#             persistPathBackup = os.path.join(persistSrcBackup, f)
#             os.rename(persistPath, persistPathBackup)
        

# def _load_persisted_sources():
#     for (counter, modname, modpath, string_source_path) in modpathLoadOrder:
#         if modname.name != modpath.name:
#             mod = ensure_modpath_installed(modname)
#             mod.parse_and_build_source(modpath)
#         else:
#             mod = ensure_modpath_installed(modpath)

#         #have to make sure source is there as it may have been cleared by reloadprocessmodels
#         if string_source_path is not None and os.path.exists(string_source_path):
#             ssFile = open(string_source_path, 'rb')
#             text = ssFile.read()
#             try:
#                 #XXX:KLUDGE, REWRITE: we don't know if the source is a taskexpr or statement,
#                 #so we have to parse twice to see if it's parseable.
#                 expr, sparklUnit = mod.parse_string(TASKEXPR, text, [], True, counter)
#             except:
#                 try:
#                     expr, sparklUnit = mod.parse_string(STATEMENT, text, [], True, counter)
#                 except:
#                     #source probably contains syntax errors, which may occur with console sources
#                     #as we store all console sources regardless of parseability
#                     expr = None
#                     sparklUnit = None
#             ssFile.close()            
#             #assuming that we are resuming properly, the parsed loadid must be the same
#             CONSOLE_SOURCE_ID_MAP[counter] = (expr, sparklUnit, )

def _load_default_module():
    dmFilename = os.path.join(get_persist_root_dir(), "defaultModule")
    if not os.path.exists(dmFilename):
        return
    
    f = open(dmFilename, 'r')
    defaultModulename = f.read().rstrip()
    if len(defaultModulename) == 0:
        return
    #debug("(persist) default module is %s", defaultModulename)
    defaultModule = ensure_modpath_installed(Symbol(defaultModulename))
    if defaultModule is None:
        raise Exception("Persistence could not properly load default module '%s'"%defaultModulename)
    from spark.internal.parse.processing import set_default_module
    set_default_module(defaultModule)
    f.close()

def resume_sources():
    """resume loads any non-agent related persistence data. it is a pre-requisite
    to loading the agent KBs"""
    if not _resumeState:
        return
    console("Resuming sources...")
    persist_root_dir = get_persist_root_dir()
    persist_src_dir = get_persist_src_dir()
    if not os.path.exists(persist_root_dir) or not os.path.exists(persist_src_dir):
        console("Could not find %s or %s" % (persist_root_dir, persist_src_dir))
        return

    try:
        from spark.internal.parse.processing import SPU_RECORD
        SPU_RECORD.restore()

        _init_resume_data()
        # set_resuming(True)
        # set_source_locator(persist__must_find_file)

        # _load_persisted_sources()
        _load_default_module()

        # set_source_locator(default__must_find_file)
        # set_resuming(False)
        console("DONE resuming sources")
    except AnyException, e:
        console("ERROR resuming sources")
        errid = NEWPM.displayError()
        NEWPM.pm(errid)
        

def resume_kb(agent, persistKbPath=None):
    if not _resumeState:
        return
    if persistKbPath is None:
        if not AGENT_KB_MAP.has_key(agent.name):
            raise Exception("unable to locate a persisted knowledge base for agent '%s'"%agent.name)
        persistKbPath = AGENT_KB_MAP[agent.name]
    if not os.path.exists(persistKbPath):
        raise Exception("persisted knowledge base [%s] missing for agent '%s'"%(persistKbPath, agent.name))
     
    console("(persist) Agent '%s' persisted KB: [%s]", agent.name, persistKbPath)
 
    if os.path.exists(persistKbPath+ERRORS_SUFFIX):
        kbErrFile = open(persistKbPath+ERRORS_SUFFIX, 'rb')
        persistedErrorText = kbErrFile.read()
        kbErrFile.close()
        console("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"+\
                "(persist) Agent '%s'\n"%agent.name+\
                "The agent reported the following errors when it saved its\n"+\
                "knowledge base:\n"+\
                "\n"+\
                "-----------------------------------------------------\n"+\
                persistedErrorText+\
                "\-----------------------------------------------------\n"+\
                "SPARK can continue loading, but some facts may be lost or corrupt.\n")
        if _isInteractive:
            #TODO: eliminate uses of raw_input
            option = raw_input("Type 'q' to quit loading SPARK or <enter> to continue: ")
            if option.startswith('q'):
                sys.exit(-1)
            console("Continuing SPARK agent resume")
     
    from cStringIO import StringIO        
 
    failedConcludes = []
    #bogusValues = []
    diffIo = StringIO()

    missingPredsList = [] #only used to make warning messages to user unique
    loadFactsFromFile(agent, persistKbPath, failedConcludes, diffIo, missingPredsList)

    # Due to is_resume_block_concludes() we cannot just assert a new incarnation
    # incarnation = agent.factslist0(P_PersistenceIncarnation)[0][0]
    # agent.addfact(P_PersistenceIncarnation, (incarnation+1,))
    # Instead we rely on knowledge of exactly how it is implemented
    info = agent.getInfo(P_PersistenceIncarnation)
    incarnation = info.keys()[0]

    # Get the current incarnation directory for the agent before
    # bumping the incarnation number.
    incarnation_dir = get_persist_incarnation_dir(agent.name, incarnation)
                                                  
    del info[incarnation]
    info[incarnation+1] = [(incarnation+1,)]

    # Load all the relevant SPU persistence files
    loadedFileObjectsFacts = agent.factslist0(P_LoadedFileObjects)
    
    from spark.internal.init import is_persist_state
    from spark.internal.persist import ieFact, writeSPUPersistIEFacts
    for lfofact in loadedFileObjectsFacts: # for each LoadedFileObject fact
        # load in the appropriate SPU persist file
        spufilename = lfofact[0]
        spuindex = lfofact[1]
        name = 'kb2.%08d'%spuindex
        filename = os.path.join(incarnation_dir, name)
        facts = loadFactsFromFile(agent, filename, failedConcludes, diffIo, missingPredsList)
        # If also persisting, rewrite the file with new objectids
        if is_persist_state():
            iefacts = [ieFact(agent, fact.functor, fact) for fact in facts]
            writeSPUPersistIEFacts(agent, spufilename, spuindex, iefacts)

    
    diffVal = diffIo.getvalue()
    if diffVal and len(diffVal) > 0:
        console("\n-------------------------------------------------------------------\n"+\
                "(persist) Agent '%s'\n"%agent.name+\
                "The resumed state of the agent knowledge base will be modified.\n"+\
                "These modifications may represent changes in connections to \n"+\
                "external entities or other dynamic state that has changed. These\n"+\
                "changes are considered normal, though they may interfere with\n"+\
                "success of ongoing and future agent actions.\n"+\
                "\n"+\
                "The following is a summary of these modifications:\n"+\
                "\n"+\
                diffVal+"\n"+\
                "-------------------------------------------------------------------\n")
     
#     if bogusValues:
#         console_error("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"+\
#                       "(persist) Agent '%s'\n"%agent.name+\
#                       "The Agent Knowledge Base contained invalid values.\n"+\
#                       "SPARK can continue loading, but some values may be lost or corrupt.\n"+\
#                       "\n"+\
#                       "The following is a list of the corrupt data:\n")
#         for b in bogusValues:
#             #TODO: should append to a StringIO so that we don't get the ERROR: prefix repeatedly
#             console("%s\n", b)
#         if _isInteractive:
#             #TODO: can't use raw_input anymore
#             option = raw_input("Type 'q' to quit loading SPARK or <enter> to continue: ")
#             if option.startswith('q'):
#                 sys.exit(-1)
#             console("Continuing SPARK agent resume")
             
    #print "RESUMED KB", persistKbPath
    return failedConcludes

################################################################
# Load facts from a file
def loadFactsFromFile(agent, filename, failedConcludes, diffIo, missingPredsList):
    from spark.internal.parse.basicvalues import VALUE_CONSTRUCTOR, Structure, isStructure
    from spark.internal.parse.generic_tokenizer import FileSource
    #from spark.internal.parse.sparkl_parser import EOF_DELIMITER, SPARKLTokenizer, SPARKLParser, BogusValue
    from spark.internal.parse.sparkl_parser import parseSPARKL
    from spark.lang.builtin_eval import builtin_evaluate
    from spark.internal.repr.varbindings import valuesBZ
    from spark.pylang.implementation import PersistablePredImpInt
    from spark.internal.parse.usagefuns import termEvalErr
    print "RESUMING KB FROM", filename
    
    #parser = SPARKLParser(VALUE_CONSTRUCTOR, SPARKLTokenizer(FileSource(filename)))
    #parseVal = parser.terms_and_taggeds(True, EOF_DELIMITER, "end of input")
    f = open(filename, 'rb')
    string = f.read()
    f.close()
    parseVal = parseSPARKL(string, "File "+filename, VALUE_CONSTRUCTOR)
    
    facts = []                          # keep track of all facts in file
    for val in parseVal:
#         if isinstance(val, BogusValue):
#             bogusValues.append(val)
#             continue
        if not (isStructure(val)): raise AssertionError

        functor = val.functor
        
        try:
            imp = agent.getImp(functor)
        except LowError, e:
            if functor not in missingPredsList:
                #TODO: make warning only once per prediate functor
                console_warning("Predicate %s is no longer part of the SPARK process models and facts for it will be purged", functor.name)
                missingPredsList.append(functor)
            continue
            
        if not (isinstance(imp, PersistablePredImpInt)): raise AssertionError
        #evaluate each of the args before putting into the zexpr
        try:
            fact = [builtin_evaluate(agent, arg) for arg in val]
            facts.append(Structure(functor, fact))
            b, z = valuesBZ(fact)
        except:
            errid = NEWPM.displayError()
            console_error("(persist) unable to resume knowledge base fact \n\t%s\n", val)
            continue
        bindings_altzexpr = imp.resume_conclude(agent, b, z)
        if bindings_altzexpr is not None:
            (bindings, altzexpr) = bindings_altzexpr
            failedConcludes.append((imp, bindings, altzexpr,))
            diffIo.write("-(%s %s)\n"%(val.functor.name, \
                                       " ".join([persist_strrep(v) for v in val])))
            diffIo.write("+(%s %s)\n"%(val.functor.name, \
                                       " ".join([persist_strrep(termEvalErr(agent, bindings, z)) for z in altzexpr])))
    return facts
    
             



###################################
# Source Locator 
#
# * Find persisted sources during
#   reloading of SPARK.
###################################
    
# def persist__must_find_file(filepath):
#     # FILEPATH_PATH
#     absname = filepath.name
#     if not _reloadProcessModels and MODPATH_FILEPATH_MAP.has_key(absname):
#         return os.path.join(get_persist_src_dir(), MODPATH_FILEPATH_MAP[absname])

#     path = None

#     # setting up two things at once:
#     # 1. Reload process models: new file in src dir, load it instead
#     # 2. .spark file never made it to the persisted src directory (ULTRA-RECOVERY MODE): try to find among non-persisted sources
    
#     try:
#         path = default__must_find_file(filepath)
#         if not _reloadProcessModels:        
#             console_error("cannot find file %s among persisted state, using unpersisted version '%s'", absname, path)
#             return path
#     except LowError, e:
#         if not _reloadProcessModels:
#             raise LowError("Cannot find the file %s among persisted state.", absname)
        
#     #done with ultra recovery mode: just reutrn path if we got it
#     if path:
#         return path
#     raise LowError("Cannot find file %s.\nPath is %s", absname, sys.path)
