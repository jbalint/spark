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
#* "$Revision:: 344                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

#Spark Developers' Logger
import time, math, os.path
import logging


class SLogger:
    __slots__ = ("logger", "_level",)
    FATAL = logging.FATAL
    EXCEPTION = logging.ERROR
    FAILURE = logging.WARN # action or procedure fails
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    ALL = logging.NOTSET
    OFF = 100       
    
    #from spark.internal.parse.values_python import Symbol
    
    LEVELS = {"spark.util.logger.LEVEL_ALL":ALL, "spark.util.logger.LEVEL_DEBUG":DEBUG, "spark.util.logger.LEVEL_INFO":INFO, "spark.util.logger.LEVEL_FAILUER":FAILURE, "spark.util.logger.LEVEL_EXCEPTION":EXCEPTION, "spark.util.logger.LEVEL_FATAL":FATAL, "spark.util.logger.LEVEL_OFF":OFF}
                   
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self._level = SLogger.ALL
 
    def getHandlers(self):
        return tuple(self.logger.handlers)


    def setLevel(self, level):
        level = str(level)
        if SLogger.LEVELS.has_key(level):            
            self._level = SLogger.LEVELS[level]
            self.logger.setLevel(self._level)
        else: 
            print "Level was not recognized."
        
        
    def setLevelAsString(self, level):
        if level == "FATAL":
            self.setLevel(SLogger.FATAL)
        elif level == "EXCEPTION":
            self.setLevel(SLogger.EXCEPTION)
        elif level == "FAILURE":
            self.setLevel(SLogger.FAILURE)
        elif level == "INFO":
            self.setLevel(SLogger.INFO)
        elif level == "DEBUG":
            self.setLevel(SLogger.DEBUG)
        elif level == "OFF":
            self.setLevel(SLogger.OFF)
        else:
            print "WARNING: Could not recognize the logger level."
                            
    def pause(self):
        self.logger.setLevel(SLogger.OFF)

    def resume(self):
        self.logger.setLevel(self._level)
        
    def log(self, message, *args):
        self.logger.info(message, *args)

    def logInfo(self, message, *args):
        self.logger.info(message, *args)

    def logWarning(self, message, *args):
        self.logger.warning(message, *args)
        
    def logDebug(self, message, *args):
        self.logger.debug(message, *args)
        
    def logError(self, message, *args):
        self.logger.error(message, *args)
        
    def __str__(self):
        return "Spark Logger (%s)"%self._filename
