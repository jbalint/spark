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
#* "$Revision:: 129                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.version import *
import math, os, time
from spark.internal.repr.taskexpr import DoEvent, TFrame
from spark.internal.repr.common_symbols import P_Properties
from spark.internal.repr.procedure import ProcedureTFrame
from spark.internal.repr.taskexpr import TaskExprTFrame
from spark.lang.builtin import object_type
from spark.internal.parse.basicvalues import objectId
#from spark.internal.parse.processing import Constraint
from spark.lang.meta_aux import module_name, procedure_module, getTaskName, getTaskParentID, getInputGoalParameters, getOutputGoalParameters, getPredicateParameters
from spark.internal.exception import Failure, FailFailure, TestFailure, ExceptionFailure, MessageFailure, NoGoalResponseFailure, SignalFailure
from spark.io.file import *
from spark.util.misc import getMachineName
from spark.lang.string import format_string
from spark.internal.parse.basicvalues import *
from spark.internal.common import NEWPM, DEBUG
from spark.internal.persist_aux import get_persist_root_dir, ensure_dir
import os.path

debug = DEBUG(__name__).on()
#=============================

machineName = getMachineName()
eventCounter = 0

class Logger(ConstructibleValue):
    __slots__ = ("_location","_filename", "name", "_desc", "abs_location", "descriptor")

    def __init__(self, location, extra = (), fn = None):
        ConstructibleValue.__init__(self)
        self._location = location
        ensure_dir(os.path.abspath(location))
        self.name  = "ExecutionTracer"
        self._desc = "ExecutionTracer"
        if os.path.isabs(location): # if it is not an absolute path:
            self.abs_location = location
        else:
            self.abs_location = os.path.join(get_persist_root_dir(), location)
        ensure_dir(self.abs_location)
        try:
            if fn != None and os.path.exists(self.abs_location + "/" + fn):
                # Reopen the old file
                resuming = True
                self._filename = fn
                ffn = self.abs_location + "/" + fn
            else:
                #Creating a new file.
                resuming = False
                self._filename = "sparklog_%04d%02d%02dT%02d%02d%02d.xml"%time.localtime()[0:6]
                ffn = self.abs_location + "/" + self._filename
        except:
            ConstructibleValue.__init__(self)
            NEWPM.displayError()
            debug("Error constructing the log file name.")
            return
        try:
            self.descriptor = FileWrapper(ffn, "a")
            self.writeLog("<?xml version=\"1.0\" ?>\n")
            self.writeLog("<ExecutionTracer>\n")
            if not resuming:
                global machineName
                self.writeLog("\t<Initiator>TaskManager</Initiator>\n")
                self.writeLog("\t<TimeZone>%s</TimeZone>\n"%time.tzname[0])
                self.writeLog("\t<MachineName>%s</MachineName>\n"%machineName)
            for x in extra:
                key, value = x
                self.writeLog("\t<%s>%s</%s>\n"%(key, value, key))
        except:
            NEWPM.displayError()
            debug("Error initiating the log file.")

    cvcategory = "Logger"
    constructor_mode = "VVV"

    def cvname(self):
        return self.abs_location
    
    def getFilename(self):
        return self._filename        
    
    def getLocation(self):
        return self.abs_location        

    def getFullPath(self):
        return os.path.join(self.abs_location, self._filename)        

    def constructor_args(self):
        return [self._location, (), self._filename]

    def set_state(self, agent):
        pass

    def writeLog(self, loginfo):
        try:
            self.descriptor.write(str(loginfo))
            self.descriptor.flush()
        except:
            debug("Error in writing into the log file.")
    
    def startLogger(self):
        pass

    def stopLogger(self):
        try:
            self.writeLog("</ExecutionTracer>\n")
            self.flushLogger()
            self.descriptor.close()
            self.descriptor = None
        except:
            debug("Error in closing the log file.")
    
    def flushLogger(self):
        try:
            self.descriptor.flush()
        except:
            debug("Error in flushing the log file.")

installConstructor(Logger)

class LogInfo(object):
    __slots__ = ("name","parent","id","_time","type","status","parameters","failuretype","statusdata")
    
    def __init__(self, name, id, parent, tim, typ, par):
        self.name        = name
        self.id          = id
        self.parent      = parent
        self.type        = typ
        self.parameters  = par
        self.status      = None
        self.failuretype = None
        self.statusdata  = None
        self.setTime(tim)
 
    def setTime(self, n):
        milliseconds = "%03d"%int((n-math.floor(n))*1000)
        self._time = "%04d%02d%02dT%02d%02d%02d"%time.localtime(n)[0:6] + milliseconds
                                  
    def setStatus(self, n):
        self.status = n
                                  
    def setFailure(self, n):
        self.failuretype = n.__class__.__name__
        self.statusdata = n.getFailureValue()
        if isinstance(self.statusdata, DoEvent):
            self.statusdata = "No procedure matching %s"%self.statusdata._symbol
        
    def getEventId(self):
        global machineName, eventCounter
        eventCounter += 1
        return "%s%s%s"%(machineName, eventCounter, self._time)
 
    def __str__(self):
        st = "\t<Event id=\"%s\">\n"%self.getEventId()
        try:
            type1, type2 = self.type
            if type1=="Started":
                ptype = "Input"
            else:
                ptype = "Output"
            st += "\t\t<%sName>%s</%sName>\n"%(type2, self.name, type2)
            st += "\t\t<%sId>%s</%sId>\n"%(type2, self.id, type2)
            st += "\t\t<EventType>%s%s</EventType>\n"%self.type
            st += "\t\t<Time>%s</Time>\n"%self._time
            st += "\t\t<ParentId>%s</ParentId>\n"%self.parent
            if self.parameters is not None:
                st += "\t\t<%sParameters>\n"%ptype
                for p in self.parameters:
                    (key, value) = p
                    st += "\t\t\t<Parameter>\n"
                    st += "\t\t\t\t<Name>%s</Name>\n"%key
                    st += "\t\t\t\t<Value><![CDATA[%s]]></Value>\n"%format_string("%s", (value,))                
                    st += "\t\t\t</Parameter>\n"
                st += "\t\t</%sParameters>\n"%ptype
            if self.status:
                st += "\t\t<Status>%s</Status>\n"%self.status
            if self.failuretype:
                st += "\t\t<FailureType>%s</FailureType>\n"%self.failuretype
            if self.statusdata:
                st += "\t\t<StatusData>%s</StatusData>\n"%self.statusdata
        except:
            pass
        st += "\t</Event>\n"
        return st


def publish_spark_procedure_started_event(agent, tframe, name, tim, logger):
    try:
        event = tframe.event()
        eventtype = object_type(event)
        args = None
        if eventtype in ("spark.internal.repr.taskexpr.AchieveEvent", "spark.internal.repr.taskexpr.DoEvent"):
            args = getInputGoalParameters(agent, event)
        elif eventtype == "spark.pylang.defaultimp.AddFactEvent":
            args = getPredicateParameters(agent, event)
        loginfo = LogInfo(name, tframe.objectId(), event.objectId(), tim, ("Started", "Procedure"), args)
        logger.writeLog(loginfo)
    except Exception, e:
        debug("Error in Logging...", e)
    
def publish_spark_procedure_succeeded_event(agent, tframe, name, tim, logger):
    try:
        event = tframe.event()
        eventtype = object_type(event)
        args = None
        if eventtype in ("spark.internal.repr.taskexpr.AchieveEvent", "spark.internal.repr.taskexpr.DoEvent"):
            args = getOutputGoalParameters(agent, event)
        elif eventtype == "spark.pylang.defaultimp.AddFactEvent":
            args = getPredicateParameters(agent, event)
        loginfo = LogInfo(name, tframe.objectId(), event.objectId(), time, ("End", "Procedure"), args)
        loginfo.setStatus("Succeeded")
        logger.writeLog(loginfo)
    except Exception, e:
        debug("Error in Logging...", e)
    
def publish_spark_procedure_failed_event(agent, tframe, name, tim, reason, logger):
    try:
        event = tframe.event()
        loginfo = LogInfo(name, tframe.objectId(), event.objectId(), tim, ("End", "Procedure"), None)
        loginfo.setFailure(reason)
        loginfo.setStatus("Failed")
        logger.writeLog(loginfo)
    except Exception, e:
        debug("Error in Logging...", e)
    
def publish_spark_task_started_event(agent, task, name, tim, logger):
    try:
        args = getInputGoalParameters(agent, task)
        loginfo = LogInfo(name, task.objectId(), getTaskParentID(task), tim, ("Started", "Task"), args)
        logger.writeLog(loginfo)
    except Exception, e:
        debug("Error in Logging...", e)

def publish_spark_task_succeeded_event(agent, task, name, tim, logger):
    try:
        args = getOutputGoalParameters(agent, task)
        loginfo = LogInfo(name, task.objectId(), getTaskParentID(task), tim, ("End", "Task"), args)
        loginfo.setStatus("Succeeded")
        logger.writeLog(loginfo)
    except Exception, e:
        debug("Error in Logging...", e)

def publish_spark_task_failed_event(agent, task, name, tim, reason, logger):
    try:
        loginfo = LogInfo(name, task.objectId(), getTaskParentID(task), tim, ("End", "Task"), None)
        loginfo.setStatus("Failed")
        loginfo.setFailure(reason)
        logger.writeLog(loginfo)
    except Exception, e:
        debug("Error in Logging...", e)
