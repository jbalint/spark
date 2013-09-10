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
#* "$Revision:: 237                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
import time as _time
import calendar
import re
from spark.internal.parse.basicvalues import isString, isFloat, isInteger
from spark.internal.exception import LowError
# A real time T is converted to a simulated time
# T'=(T-realbase)*speed+simulatedbase
# _TIMEWARP is a triple (<realbase>, <simulatedbase>, <speed>)
NULL_TIMEWARP = (0.0, 0.0, 1.0)
_TIMEWARP = NULL_TIMEWARP
SIMULATED_TIME = "NOW"
REAL_TIME = "REAL"

DURATION = re.compile(r"(-)?P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:.\d+)?)S)?$")
DATE_TIME = re.compile(r"(\d\d\d\d)-?(\d\d)-?(\d\d)(?:T(\d\d)(?::?(\d\d)(?::?(\d\d(?:.\d+)?))?)?(?:|(Z)|([+-]\d\d):?(\d\d)?))?$")

TIMEZONE = re.compile(r"([+-]\d\d):?(\d\d)?$")

def optInt(x):
    if x == None:
        return 0
    else:
        return int(x)

def optFloat(x):
    if x == None:
        return 0.0
    else:
        return float(x)


def timeString(time, mode):
    """Return the given time/duration as a string as acceptable by
    getTime. $mode is 'P' for a duration, 'DATE' for a date
    with no time, 'Z' to return a UT/GMT time string, ''
    to return a local time, or a timezone designation string, such
    as'+10:30' to return the time for a specific timezone.
    """
    if mode == "P":                     # Duration
        if (time < 0):
            time = -time
            out = ["-P"]
        else:
            out = ["P"]
        dhm, s = divmod(time, 60)
        dh, m = divmod(dhm, 60)
        d, h = divmod(dh, 24)
        if d != 0.0:
            out.append("%dD"%d)
        if h != 0.0:
            out.append("%dH"%h)
        if m != 0.0:
            out.append("%dM"%m)
        if s != 0.0:
            out.append("%gS"%s)
        if len(out) == 1:
            out.append("0S")
        return "".join(out)
    elif mode == "Z":
        struct_time = _time.gmtime(time)
    elif mode == "":
        struct_time = _time.localtime(time)
    elif mode == "DATE":
        # Date represented by 00:00 GMT on the given date
        return _time.strftime("%Y-%m-%d", _time.gmtime(time))
    else:
        match = TIMEZONE.match(mode)
        if match:
            (tzh, tzm) = match.groups()
            offset = (int(tzh)*60 + optInt(tzm))*60
            struct_time = _time.gmtime(time + offset)
        else:
            raise LowError("Invalid timeString mode argument: %s"%mode)
    return _time.strftime("%Y-%m-%dT%H:%M:%S", struct_time) + mode

def getTime(arg=None):
    """Get the time as a floating point number
    arg=None or arg="NOW": get the current simulated time
    arg="REAL": get the current real time
    arg='<yyyy>-<mm>-<dd>T<HH>:<MM>:<SS>[.<frac>]': get from localtime string
    arg='<yyyy>-<mm>-<dd>T<HH>:<MM>:<SS>[.<frac>]Z': get from UT string
    arg='<yyyy>-<mm>-<dd>T<HH>:<MM>:<SS>[.<frac>][+-]<HH>:<MM>': use given timezone
    arg='<yyyy>-<mm>-<dd>; represent date by 00:00 UT
    arg='P<d>D<H>H<M>M<S>[.<frac>]' treat as a duration
    arg='-P<d>D<H>H<M>M<S>[.<frac>]' treat as a negative duration
    arg is a float: leave it unchanged
    Note: the - and : separators and some unused components can be left out
    """
    if arg is None or arg == SIMULATED_TIME:
        return _realtimeToSimtime(_time.time())
    elif arg == REAL_TIME:
        return _time.time()
    elif isString(arg):
        match = DURATION.match(arg)
        if match:
            (neg, d,h,m,s) = match.groups()
            dur = ((optInt(d)*24 + optInt(h))*60 + optInt(m))*60 + optFloat(s)
            if neg:
                return -dur
            else:
                return dur
        match = DATE_TIME.match(arg)
        if match:
            (Y, M, D, h, m, s, z, tzh, tzm) = match.groups()
            year = int(Y)
            month = int(M)
            day = int(D)
            hour = optInt(h)
            min = optInt(m)
            sec = optFloat(s)
            if z or h == None: # explicit GMT suffix or date without time
                return calendar.timegm((year,month,day,hour,min,0,0,1,0)) + sec
            elif tzh:
                offset = (int(tzh)*60 + optInt(tzm))*60
                gmt = calendar.timegm((year,month,day,hour,min,0,0,1,0)) + sec
                return gmt - offset
            else:
                return _time.mktime((year,month,day,hour,min,0,0,1,-1)) + sec
        else: 
            raise LowError('Invalid datetime string: %s'%arg)
#         try:
#             if arg[8] != "T":
#                 raise LowError("Invalid datetime string: %s"%arg)
#             year = int(arg[0:4])
#             month = int(arg[4:6])
#             day = int(arg[6:8])
#             hour = int(arg[9:11])
#             min = int(arg[11:13])
#             if arg.endswith('Z'):           # UT
#                 sec = float(arg[13:-1] or 0)
#                 return calendar.timegm((year,month,day,hour,min,0,0,1,0)) + sec
#             else:                           # localtime
#                 sec = float(arg[13:] or 0)
#                 return _time.mktime((year,month,day,hour,min,0,0,1,-1)) + sec
#         except (ValueError, IndexError):
#             raise LowError('Invalid datetime string: %s'%arg)
    elif isFloat(arg):
        return arg
    elif isInteger(arg):
        return float(arg)
    else:
        raise LowError('Invalid time argument of type %s: %r'%(type(arg), arg))

def _realtimeToSimtime(realtime):
    timewarp = _TIMEWARP
    return (realtime - timewarp[0]) * timewarp[2] + timewarp[1]
        
    
def setTimeSpeed(simtime, simspeed):
    """Set the simlated time speed and the current simulated time.
    A simspeed of 10 means simulated time progresses at 10x realtime.
    A simspeed of 0 or less means leave the simspeed the same as it was.
    If simtime is None or 'NOW', the simulated tme does not change."""
    global _TIMEWARP
    realtime = _time.time()
    if simtime is None or simtime == SIMULATED_TIME:
        simtime = _realtimeToSimtime(realtime)
    elif simtime is REAL_TIME:
        simtime = realtime
    elif isString(simtime):
        simtime = getTime(simtime)
    elif isFloat(simtime):
        pass
    elif isInteger(simtime):
        simtime = float(simtime)
    else:
        raise LowError('Invalid time argument')
    if simspeed <= 0:
        simspeed = _TIMEWARP[2]
    else:
        simspeed = float(simspeed)
    if realtime == simtime and simspeed == 1.0:
        _TIMEWARP = NULL_TIMEWARP
    else:
        _TIMEWARP = (realtime, simtime, simspeed)

def formatLocalTime(t=None):
    return strftime("%Y%m%dT%H%M%S", localtime(getTime(t)))

def formatGMTime(t=None):
    return strftime("%Y%m%dT%H%M%S", gmtime(getTime(t)))

################################################################
# Replacements for contents of time module

# Data copied from _time, should not be modified
#from time import accept2dyear, altzone, daylight, timezone, tzname
# accept2dyear = _time.accept2dyear
# altzone = _time.altzone
# daylight = _time.daylight
# timezone = _time.timezone
# tzname = _time.tzname

def asctime(t=None):
    if t is None:
        t = localtime()
    return _time.asctime(t)

# Cannot realistically adjust CPU time for simulated time
clock = _time.clock

def ctime(secs=None):
    if secs is None:
        secs = time()
    return _time.ctime(secs)

def gmtime(secs=None):
    if secs is None:
        secs = time()
    return _time.gmtime(secs)

def localtime(secs=None):
    if secs is None:
        secs = time()
    return _time.localtime(secs)

mktime = _time.mktime

def sleep(secs):
    # NOTE: We have to assume that the simulated speed does not change
    # while we sleep.
    _time.sleep(secs/_TIMEWARP[2])

def strftime(format, t=None):
    if t is None:
        t = localtime()
    return _time.strftime(format, t)
try:
    strptime = _time.strptime
except AttributeError:
    # strptime not defined on this platform
    pass

struct_time = _time.struct_time

time = getTime

try:
    tzset = _time.tzset
except AttributeError:
    # tzset is a Python 2.3 addition
    pass
