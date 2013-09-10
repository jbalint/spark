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
#* "$Revision:: 405                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

from spark.internal.slogger import SLogger
from spark.internal.version import *    # must import everything
from spark.internal.common import NEWPM
import logging
import os.path, sys

sdlogger = None

def loggerPause():
    get_sdl().pause()

def loggerResume():
    get_sdl().resume()

def logInfo(message, *args):
    get_sdl().logInfo(message, *args)
    return True
    
def logWarning(message, *args):
    get_sdl().logWarning(message, *args)
    return True
    
def logDebug(message, *args):
    get_sdl().logDebug(message, *args)
    return True
    
def logError(message, *args):
    get_sdl().logError(message, *args)
    return True
  
def loggerSetLevel(level):
    get_sdl().setLevel(level)

def loggerGetFilename():
    import os.path
    handlers = get_sdl().getHandlers()
    for h in handlers:
        if isinstance(h, logging.FileHandler):
            return os.path.normpath(os.path.abspath(h.stream.name))
    return ""

def initial_sdl(logParams={}):
    global sdlogger
    name = "SDL"
    
    if not logParams.has_key('sparkhome'):
        from spark.util.misc import getSparkHomeDirectory
        logParams['sparkhome'] = getSparkHomeDirectory()
    
    if not logParams.has_key('logdir'):
        # Create log directory if not present
        logParams['logdir'] = os.path.join(logParams['sparkhome'], "log")
    
    #keep logging.config happy since it expects string literals
    logParams['logdir'] = logParams['logdir'].replace("\\", "\\\\")
    
#    print "logdir=", logParams['logdir']
#    print "sparkhome=", logParams['sparkhome']
    from spark.internal.persist_aux import ensure_dir
    ensure_dir(logParams['logdir'])
    #
    try:
        import logging.config
        config_log_file = os.path.join(logParams['sparkhome'], "config", "logger.cfg")
        
        if os.path.isfile(config_log_file):
            logging.config.fileConfig(config_log_file, logParams)
        else:
            # Use default setting if it can not find the config file
            print "Could not find %s. Using default logger configuration..."%config_log_file
            logger = logging.getLogger(name)
            sparklog = os.path.join(logParams['logdir'], 'spark.log')
            #print "sparklog=", sparklog
            hdlr = logging.FileHandler(sparklog)
            formatter = logging.Formatter('%(created)f [%(thread)d] %(levelname)s %(name)s - %(message)s')
            hdlr.setFormatter(formatter)
            logger.addHandler(hdlr)
        print "%s initiated."%name
    except AnyException, e:
        errid = NEWPM.displayError()
        print "Error initiating %s."%e
    sdlogger = SLogger(name)
    # Shutting down log4j:
    #if isJython:
    #    from org.apache.log4j import LogManager
    #    LogManager.shutdown()
   
def get_sdl():
    global sdlogger
    return sdlogger
