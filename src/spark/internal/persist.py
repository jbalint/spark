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
#* "$Revision:: 309                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

from spark.internal.version import *
from spark.internal.common import NEWPM, DEBUG
from spark.internal.persist_aux import *
from spark.internal.repr.varbindings import optBZ
from spark.internal.repr.common_symbols import P_ObjectExists, P_ObjectState, P_ObjectNextId, P_LoadedFileFacts, P_ArgNames, P_ArgTypes, P_Doc, P_Features, P_Properties, P_Roles, P_LoadedFileObjects, P_PersistenceIncarnation
import os
import string
from time import localtime, strftime, time

from spark.internal.instrument import set_persist_point_handler
from spark.internal.source_locator import SPARK_SUFFIX
from spark.internal.parse.basicvalues import Symbol, Structure, List, PERSIST_ID_SAVE, STANDARD_ID_SAVE, set_id_save
from spark.internal.exception import LowError

from spark.pylang.implementation import PersistablePredImpInt
from spark.pylang.defaultimp import DefaultImp
from spark.util.logger import get_sdl

debug = DEBUG(__name__)#.on()

#Testing Script. Begin:
#from spark.internal.debug.chronometer import chronometer, chronometers, print_chronometers, reset_chronometers
#chronometers["persistence_default_module"] = chronometer("persistence_default_module")
#chronometers["persistence_kb"] = chronometer("persistence_kb")
#Testing Script. End.


###################################################
#
# Main API and routines for persisting/resuming
# SPARK state to/from disk
#
###################################################

#
# Internal variables
#

_lastPersistKbTime = 0 #time that last persist_kb operation completed

#
# Main API/internal routines
#

#boolean value indicating whether or not SPARK should write out state changes to disk
_persistState = None

def set_persist_params(persistState, persistDir):
    """because internal/init.py calls methods here, we cannot import the
    persist/resume parameters. we must instead rely on init.py to call
    this method and set these values"""
    global _persistState
    _persistState = persistState
    if not persistState:
        return
    if persistDir is not None:
        set_persist_root_dir(persistDir)

    #perform persist initialization
    set_persist_point_handler(persist_point)

    print "SPARK persistence directory is", os.path.abspath(get_persist_root_dir())

    #initialize the persistence root dir
    ensure_dir(get_persist_root_dir())
    ensure_dir(get_persist_src_dir())
    
def persist_point(agent, point):
    #print "persist_point()"
    try:
        #the instrumentation layer has already verified that is_persist_point() is
        #True, so we can just directly call persist_kb() from here if we're not
        #in a resuming state
        if not is_resuming() and _persistState:
            #print "persist_point()"
            persist_version()
            #print "persist_version() complete"
            persist_kb(agent)
            #print "persist_kb() complete"
            persist_default_module()
            #print "persist_point() complete"
    except:
        #we can't allow the persist operation to fubar the executor state, so we catch
        #and print here for now
        errid = NEWPM.displayError()
    
#  def console_persist(stringSource):
#      #don't actually want to create a direct dependency on newparse,
#      #esp. just for this assert
#      if is_resuming() or not _persistState:
#          return
#      persist_unit(None, stringSource, CONSOLE_SUFFIX)

# def persist_unit(module, source):
#     #print "persist_unit", source.get_filepath(), source.loadid
#     if not _persistState:
#         return
#     from spark.internal.parse.newparse import SparklStringUnit
#     if isinstance(source, SparklStringUnit):
#         suffix = CONSOLE_SUFFIX
#     else:
#         suffix = SPARK_SUFFIX        

#     counter = source.loadid
#     if counter < 0:
#         print "ERROR: persist layer asked to persist SPARK-L unit '%s' with ID less than zero"%source.get_filepath()
#         return #tolerant of this error
#     if counter in PERSISTED_LOAD_IDS:
#         return
#     PERSISTED_LOAD_IDS.append(counter)
    
#     #encode the module ID in the filename if necessary (e.g. purchase%purchase.main)
#     name = encodeModpath(module, source.get_filepath())
#     #e.g. persist/1.spark.module.spark
#     filename = os.path.join(get_persist_src_dir(), "%05d.%s%s"%(counter, name, suffix))
#     f = open(filename, 'wb')
#     f.write(source.get_text())
#     f.close()
    
# def persist_module(mod):
#     if is_resuming() or not _persistState:
#         return
#     #print "persist_module"
#     #NOTE: this does not persist the SparklStringUnit (from Module.parse_string)
#     #separate callbacks to console_persist() must be made to
#     #persist the SparklStringUnit
#     for unit in mod._sparklUnits:
#         persist_unit(mod, unit)

def get_persisted_kb_filepath(agent):
    """return the filepath of the persisted knowledge base for the
    specified agent, or None if no persisted KB for the agent was
    found during initialization"""
    if AGENT_KB_MAP.has_key(agent.name):
        return AGENT_KB_MAP[agent.name]
    return None

def remove_persisted_files():
    """remove all on-disk state"""
    persistIncarnations = get_persist_incarnation_dirs()
    for p in persistIncarnations:
        clear_dir(p)
        os.remove(p)
    clear_dir(get_persist_src_backup_dir())
    clear_dir(get_persist_src_dir())
    clear_dir(get_persist_root_dir())     

    #make sure the persist kb data structures aren't keeping any info 
    global PERSISTED_LOAD_IDS
    AGENT_KB_MAP.clear()
    KB_WORKING_SET.clear()
    copy = PERSISTED_LOAD_IDS[:]
    for x in copy:
        PERSISTED_LOAD_IDS.remove(x)

def _loadOrderAppend(agent, string):
    #print "Adding to load order:", string
    f = open(os.path.join(get_persist_root_dir(), agent.name+'.loadOrder'), 'a')
    try:
        f.write(string)
    finally:
        f.close()
    
def persist_report_load_modpath(agent, modpath):
    _loadOrderAppend(agent, "load:%s\n"%(str(modpath))) # allow symbol or string

# def persist_report_load_string(agent, modpath, loadid):
#     _loadOrderAppend(agent, "string:%s:%d\n"%(modpath.name, loadid))

#########################################
# Knowledge Base Persist Routines
#########################################

def _roll_versions(agent, newVersion):
    if not KB_WORKING_SET.has_key(agent.name):
        KB_WORKING_SET[agent.name] = [] #init data structure
        return
    agentKbWs = KB_WORKING_SET[agent.name]
    #add in the new version to the table
    agentKbWs.append(newVersion)
    if len(agentKbWs) < MAX_VERSIONS:
        return

    #Delete an older version off the disk. always just purge the oldest rather
    #than trying ensure that we only have MAX_VERSIONS as its not worth the
    #more complicated code
    oldest = None
    oldestAge = None
    for f in agentKbWs:
        age = os.path.getmtime(f)
        if not oldestAge or age < oldestAge:
            oldest = f
            oldestAge = age
    if oldest:
        try:
            if os.path.exists(oldest):            
                os.remove(oldest)
            if os.path.exists(oldest+ERRORS_SUFFIX):
                os.remove(oldest+ERRORS_SUFFIX)
        finally:
            #there is the potential here to accumulate more versions
            #on disk than our parameters state we should have
            #if there is a problem deleting older versions.
            agentKbWs.remove(oldest)

def _get_unique_filename(f):
    if not os.path.exists(f):
        return f
    forig = f
    counter = 1
    while os.path.exists(f):
        f = forig + str(counter)
        counter += 1
    return f

def persist_version():
    """write out the spark version number to the persist directory. this
    allows us to detect when we should purge the persisted state"""
    #it's not necessary to do this every time we persist, but
    #this way we don't have to worry about race conditions with resume.py
    #reading this
    f = open(os.path.join(get_persist_root_dir(), "sparkVersion"), 'w')
    from spark.internal.version import VERSION    
    f.write(VERSION)
    f.close()
    
def persist_default_module():
    from spark.internal.parse.processing import get_default_module
    #print "persist_default_module"
    #Testing Script. Begin:
#    global chronometers
#    chronometers["persistence_default_module"].start()
    #Testing Script. End.
    dm = get_default_module()
    if not dm:
        #Testing Script. Begin:
#        chronometers["persistence_default_module"].stop()
        #Testing Script. End.
        return #no default module, happens during loading
    f = open(os.path.join(get_persist_root_dir(), "defaultModule"), 'w')
    f.write(dm.get_modpath().name)
    f.close()
    #get_sdl().logger.info("persist[Default Module[%s]]"%dm)
    #Testing Script. Begin:
#    chronometers["persistence_default_module"].stop()
    #Testing Script. End.
    
def persist_kb(agent):
    """save the persistable predicates in the agent knowledge base"""
    if is_resuming() or not _persistState:
        return

    debug("persisting kb....")
    startTime = time()

    #TODO: NEED TO REPLACE IMPLEMENTATION OR REFACTOR OUT OF DEBUGGER
    from spark.internal.debug.debugger import get_all_predicates
    # 1
    predicates = get_all_predicates(agent)

    #this implementation is similar to the save_predicates
    #implementation in the spark.util.persistence module,
    #but the persist format is slightly altered due to the
    #non-spark-l save format. this format uses reader-macro-like
    #representations and also fully quailifies symbol names

    # Make sure predicates describing persistent objects appear at the start
    objpredicates = []
    # 2
#     for sym in [Symbol(ObjectNextId.predname), Symbol(ObjectExists.predname), \
#                 Symbol(ObjectState.predname)]:
#         if sym in predicates:
#             predicates.remove(sym)
#             objpredicates.append(sym)

    filename = ''
    try:
        dateStamp = strftime("%Y%m%d%H%M%S", localtime())        
        name = 'agent.%s.kb.%s'%(agent.name, dateStamp)
        filename = _get_unique_filename(os.path.join(get_persist_root_dir(), name))
    except AnyException, e:
        raise Exception("ERROR: cannot determine where to store %s. Directory for module must exist.\n%s"%(modname, e))

    #collect list of applicable predicates (must be persistable)
    dateTime = strftime("%a, %d %b %Y %H:%M:%S", localtime())
    # 3

    from cStringIO import StringIO
    errOutput = StringIO()
    objOutput = StringIO()
    predOutput = StringIO()

    # Write out the standard predicates, assuming objects exist.
    # As a side effect, record objects that need to be persisted.
    def writePersistInfo():
        # write out non-object predicates
        writePredicates(agent, predicates, predOutput, errOutput)
        # Write out information about all objects that need to be persisted.
        for iefact in PERSIST_ID_SAVE.nextIdIEFacts():
            writeIEFact(agent, P_ObjectNextId, iefact, objOutput)
        for iefact in PERSIST_ID_SAVE.existsIEFacts():
            writeIEFact(agent, P_ObjectExists, iefact, objOutput)
        for iefact in PERSIST_ID_SAVE.stateIEFacts():
            writeIEFact(agent, P_ObjectState, iefact, objOutput)

    withPersistIdSaveCall(writePersistInfo)
    # 4
    try:
        output = open(filename, 'w')
        output.write('###########################################################\n'+\
                     '# SPARK Agent Knowledge Base\n'+\
                     "#  * Agent '%s'\n"%agent.name+\
                     "#  * Date '%s'\n"%dateTime+\
                     '###########################################################\n'+\
                     '# This is a SPARK-generated dump the SPARK knowledge base.\n'+\
                     '# Modify this file at your own risk (and only while SPARK\n'+\
                     '# is not currently running).\n'+\
                     '###########################################################\n\n')
        # write object info first
        output.write(objOutput.getvalue())
        # then write predicate info that relies on objects existing
        output.write(predOutput.getvalue())
    finally:
        output.close()

    #remove oldest version and add new version
    # 5
    _roll_versions(agent, filename)
    # 6
    errValue = errOutput.getvalue() 
    errOutput.close()
    if errValue:
        errFile = open(filename+ERRORS_SUFFIX, 'w')
        errFile.write("Errors for agent '%s'\n"%agent.name+\
                      "Date '%s'\n\n"%dateTime)
        errFile.write(errValue)
        errFile.close()
        
    global _lastPersistKbTime 
    _lastPersistKbTime = time()
    elapsed = _lastPersistKbTime - startTime
    debug("persisting kb complete (%f secs).", elapsed)
    #get_sdl().logger.info("persistKb: %f secs"%elapsed)
    #print "PERSISTED KB TO", name
    #all done

def withPersistIdSaveCall(function):
    old_id_save = None
    try:
        # keep track of all objects used from here on
        old_id_save = set_id_save(PERSIST_ID_SAVE)
        if (old_id_save != STANDARD_ID_SAVE): raise AssertionError, \
           "Overlapping calls to persist"
        PERSIST_ID_SAVE.clear()
        function()
    finally:
        if old_id_save is not None:
            newer_id_save = set_id_save(old_id_save)
            if (newer_id_save != PERSIST_ID_SAVE): raise AssertionError, \
                   "Something has changed ID_SAVE"
        PERSIST_ID_SAVE.clear()
    


def writePredicates(agent, predicates, output, errOutput):
    """Write the current state of the given predicates to output.
    Report errors to errOutput."""
    #Testing Script. Begin:
#    global chronometers
    #Testing Script. End.
    predimpls = []
    for pred in predicates:
        impl = agent.getImp(pred)
        if impl is None:
            continue
        try:
            if isinstance(impl, PersistablePredImpInt) \
                   and impl.symbol not in SPU_LOAD_INFO_PREDICATES:
                predimpls.append(impl)
        except AnyException, f:
            NEWPM.displayError()
            errOutput.write('[%s.%s]: %s\n'%(pred.name, impl.__class__.__name__, str(f)))
    
    #Print predicate definitions to file
    for impl in predimpls:
        try:
            #Testing Script. Begin:
#            #esm = str(type(impl))
#            #if not chronometers.has_key(esm):
#            #    chronometers[esm] = chronometer(esm)
#            #chronometers[esm].start()            
            #Testing Script. End.
            arityOrFacts = impl.persist_arity_or_facts(agent)
            if isinstance(arityOrFacts, int):
                b, z = optBZ([None]*arityOrFacts)
                facts = [[b.bTermEval(agent, x) for x in z] \
                        for s in impl.solutions(agent, b, z) if s]
            elif arityOrFacts == None:
                raise LowError("persist_arity_or_facts method for %s returned None"%impl.symbol)
            else:
                facts = arityOrFacts
            for fact in facts:
                writeFact(agent, impl.symbol, fact, output)
        except AnyException, f:
            errid = NEWPM.displayError()
            NEWPM.pm(errid)
            if isinstance(impl, DefaultImp):
                #use the predsym
                errOutput.write("%s(DefaultImp): %s\n"%(impl.symbol,str(f)))
            else:
                errOutput.write("%s: %s\n"%(impl.__class__.__name__,str(f)))
        #Testing Script. Begin:
#        #chronometers[esm].stop()
        #Testing Script. End.

def writeFact(agent, functorSymbol, fact, output):
    """Write a single fact."""
    output.write("(")
    output.write(functorSymbol.name)
    for arg in fact:
        output.write(" ")
        output.write(value_str(inverse_eval(arg)))
    output.write(")\n")

def writeIEFact(agent, functorSymbol, iefact, output):
    """Write a single inverse-evaluated fact."""
    output.write("(")
    output.write(functorSymbol.name)
    for iearg in iefact:
        output.write(" ")
        output.write(value_str(iearg))
    output.write(")\n")

def ieFact(agent, functorSymbol, fact):
    """Perform inverse-eval on elements of facts and construct a structure to write"""
    return Structure(functorSymbol, [inverse_eval(arg) for arg in fact])

def writeSPUPersistIEFacts(agent, spufilename, spuindex, iefacts):
    output = None
    try:
        incarnation = agent.factslist0(P_PersistenceIncarnation)[0][0]
        name = 'kb2.%08d'%spuindex
        incarnation_dir = get_persist_incarnation_dir(agent.name, incarnation)
        ensure_dir(incarnation_dir)
        filename = os.path.join(incarnation_dir, name)
        #print "WRITING PERSIST FILE %s FOR %s"%(filename, spufilename),
        output = open(filename, 'w')
        output.write('###########################################################\n'+\
                     '# SPARK Agent Knowledge Base\n'+\
                     "#  * Agent '%s'\n"%agent.name+\
                     "#  * Index '%s'\n"%spuindex+\
                     "#  * Filename '%s'\n"%spufilename+\
                     '###########################################################\n'+\
                     '# This is a SPARK-generated dump the SPARK knowledge base.\n'+\
                     '# Modify this file at your own risk (and only while SPARK\n'+\
                     '# is not currently running).\n'+\
                     '###########################################################\n\n')
        for iefact in iefacts:
            writeIEFact(agent, iefact.functor, iefact, output)
    finally:
        #print
        if output:
            output.close()

def computeSPUPersistFacts(agent, spu, asserted):
    """Return the inverse-eval facts for the persistence file for SPU.
    As a side effect, conclude a LoadedFileObjects fact
    (which puts an event on the agent's event queue)."""
    iefactlist = []
    def persistSPULoadInfo():
        # write added facts of the file
        for fact in asserted:
            functor = fact.functor
            if functor in SPU_LOAD_INFO_PREDICATES:
                iefactlist.append(ieFact(agent, functor, fact))
        # assert LoadedFileObjects
        objects = List(PERSIST_ID_SAVE.recordedObjects())
        lfofact = (spu.filename, spu.index, objects)
        agent.addfact(P_LoadedFileObjects, lfofact)

    withPersistIdSaveCall(persistSPULoadInfo)
    return iefactlist

# Special predicates for persistence

# The defaultimp predicates are not saved during ordinary persist_kb,
# but instead when an SPU is loaded into an agent. Note that
# P_LoadedFileObjects is NOT among them. It is saved during the normal
# persist_kb.

SPU_LOAD_INFO_PREDICATES = \
    [P_LoadedFileFacts,
     P_ArgNames,
     P_ArgTypes,
     P_Doc,
     P_Features,
     P_Properties,
     P_Roles,
     ]
