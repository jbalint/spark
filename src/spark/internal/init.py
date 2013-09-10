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
#* "$Revision:: 391                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

from spark.internal.version import *
import os.path
from spark.internal.persist import remove_persisted_files, set_persist_params
from spark.internal.persist_aux import PERSIST_SPARK, ensure_dir
from spark.internal.resume import resume_sources, set_resume_params, get_persisted_version_number
from spark.internal.source_locator import set_source_locator, default__must_find_file
from spark.util.logger import initial_sdl, get_sdl
#
# Responsible for initialization of SPARK. Currently, this entails
# configuring the persist/resume options and state appropriately (including
# directing the persistence layer to remove the persisted state on startup
# if necessary).
#
# init_spark() MUST be called before creating new agents
#

# if True, agent should load in persisted state. if None, SPARK has not
# been initialized and any attempts to check the state of is_resume_state()
# will raise an Exception
_resumeState = None
# if True, agent should save state changes to disk (persistence). if None, SPARK has not
# been initialized and any attempts to check the state of is_persist_state()
# will raise an Exception
_persistState = None
_persistIntentions = None

# if True, it means that SPARK is running in a user-interactive console. If false,
# it means that the SPARK console may be inaccessible to a user and SPARK
# should not depend on interactive input. NOTE: this option does not disable
# the SPARK console, it merely prevents SPARK from requiring user input (e.g.
# in the case of resuming, where there were errors, SPARK will not block
# for user confirmation on whether or not to proceeed)

_ISINTERACTIVE_DEFAULT = True
_isInteractive = _ISINTERACTIVE_DEFAULT

_initialized = False


def init_spark(**parameters):
    """initialization function for all of SPARK. properties that must be set
    before rest of SPARK starts, as well as actions such as persistence/resume
    operations that must execute first, should be placed/initialized here. The
    current recognized parameters are 'persist' and 'resume'"""
    global _resumeState, _persistState, _isInteractive, _persistIntentions
    persistDir = None
    if parameters.has_key('resume'):
        _resumeState = parameters['resume']
    if parameters.has_key('persist'):
    	if not PERSIST_SPARK:
            print "SPARK persistence is currently disabled"
            _persistState = False
            _persistIntentions = False
    	else:
            _persistState = parameters['persist']
            _persistIntentions = _persistState #by default, same as persist
    if parameters.has_key('persistIntentions'):
        _persistIntentions = parameters['persistIntentions']
    if parameters.has_key('persistDir'):
        persistDir = parameters['persistDir']
        if persistDir is not None and persistDir.startswith('"'):
            persistDir = persistDir[1:-1]
    if parameters.has_key('interactive'):
        _isInteractive = bool(parameters['interactive'])
        if _isInteractive != _ISINTERACTIVE_DEFAULT:
            print "SPARK: overriding interactive-mode setting,",_isInteractive

    #we don't need to tell persist.py about the persistIntentions parameter --
    #it gets read by the CurrentlyIntended class instead
    set_persist_params(_persistState, persistDir)
    set_resume_params(_resumeState, _isInteractive)

    # Initiating SDL"
    if parameters.has_key('logParams'):
        initial_sdl(parameters['logParams'])
    else:
        initial_sdl()
    get_sdl().logger.info("Parameters: %s", parameters)
    #parameters have been initialized, so their values can be checked
    global _initialized
    _initialized = True

    from spark.internal.parse.newparse import init_builtin
    init_builtin()
    #from spark.lang.builtin import install_builtin   # TODO: make this usable
    #install_builtin()                                #

    #PERSIST
    if _persistState or _resumeState:
        from spark.internal.version import VERSION
        persistVersion = get_persisted_version_number()
        if _resumeState and persistVersion is None:
            # Resuming, but no persist directory exists
            print "WARNING: No persist state to resume from"
        elif _resumeState and persistVersion == VERSION:
            # Resuming, and valid persist directory exists
            resume_sources()
        else:
            # Persisting but not resuming OR invalid persistVersion
            #REMOVAL OF PREVIOUSLY PERSISTED STATE - we currently use
            # the versioning mechanism to wipe older files when we
            # update process models, as we do not have a merging
            # mechanism yet
            if persistVersion and persistVersion != VERSION and _resumeState:
                print "WARNING: SPARK cannot resume persisted files with version ID [%s]. \nSPARK's current version ID is [%s]. "%(persistVersion, VERSION)
                if _isInteractive:
                    print "The persisted files will be removed if SPARK continues loading."
                    print " * Type 'q' to quit loading SPARK (persisted state will not be altered)" 
                    print " * Hit <enter> to continue (persisted state will be deleted)"
                    option = raw_input(">> ")
                    if option.startswith('q'):
                        import sys
                        sys.exit(-1)
                    print "Continuing SPARK agent resume"
                else:
                    print "SPARK is removing the previously persisted state in order to continue loading." 
            # Give the agent a blank slate with which to record new
            # persisted data
            remove_persisted_files()

def is_interactive():
    return _isInteractive

def is_resume_state():
    """Returns True if agent should load persisted state from disk. Raises
    Exception if init_spark() has not been called first"""
    if not _initialized:
        raise Exception("SPARK has not been properly initialized. "+\
                        "init_spark() must be invoked before initializing agents")
    return _resumeState

def is_persist_state():
    """Returns True if agent should save persisted state to disk. Raises
    Exception if init_spark() has not been called first"""
    if not _initialized:
        raise Exception("SPARK has not been properly initialized. "+\
                        "init_spark() must be invoked before initializing agents")
    return _persistState

def is_persist_intentions():
    """Returns True if agent should save intention state to disk. Raises
    Exception if init_spark() has not been called first"""
    if not _initialized:
        raise Exception("SPARK has not been properly initialized. "+\
                        "init_spark() must be invoked before initializing agents")
    return _persistIntentions
