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
from types import *
from spark.internal.parse.basicvalues import Symbol, value_str, List, isList, String, isString

#
# Basic string routines, added as necessary
# author conley
#

def to_string(arg):
    if isList(arg):
        return "[%s]"%(" ".join([to_string(x) for x in arg]))
    else:
        return str(arg)

def _popArg(aList):
    if aList:
        return aList.pop()
    else:
        raise SyntaxError("Ran out of arguments in format string")

def python_format_string(format, args):
    return format%args

def format_string(format, args):
    newmsg = []
    state = 0
    aList = list(args)
    aList.reverse()
    for ch in format:
        if state == 0:
            number = ""
            if ch =='%':
                state = 1
            else:
                newmsg.append(ch)
        elif state == 1:
            if ch =='%':
                newmsg.append(ch)
                state = 0
            elif ch == 's':
                newmsg.append(to_string(_popArg(aList)))
                state = 0
            elif ch =='r':
                newmsg.append(value_str(_popArg(aList)))
                state = 0
            elif ch.isdigit():
                number = "%" + ch
                state = 2
            elif ch == "d":
                newmsg.append("%d"%_popArg(aList))
                state = 0
            else:
                raise SyntaxError("Invalid format command: %%%s"%ch)
        elif state == 2:
            if ch.isdigit():
                number = number + ch
            elif ch == "d":
                mess = number + "d"
                newmsg.append(mess%_popArg(aList))
                state = 0
            else:
                raise SyntaxError("Invalid format command: %s"%(number+ch))
    if state == 1:
        raise SyntaxError("Unused Format string ends in %")
    if aList:
        aList.reverse()
        raise SyntaxError("Unused arguments in format string: %s"%value_str(List(aList)))
    return "".join(newmsg)

def string_starts_with(value, prefix):
    return value.startswith(prefix)
  
def string_ends_with(value, suffix):
    return value.endswith(suffix)
    
# SubstringMatch
#
# returns true if $sub appears in $string, otherwise false
def contains(s, sub):
    ans = s.find(sub)
    if (ans > -1):
        return True
    else:
        return False

# substringIndex
#
# returns index of $sub in $string, -1 if it doesn't appear
def substringIndex(s, sub):
    ans = s.find(sub)
    return ans

# stringCharFromString
#
# give a string "|foo|" and char "|", returns "foo"
# NOTE: only looks for char at beginning and end of string.
def chop_char(s, char):
    if (s[0] == char):
        s = s[1:]
    if (s[-1] == char):
        s = s[:-1]
    return s

# stringJoin
#
# joins a list of strings

def stringJoin(strings, connective):
    if isString(strings):
        print "WARNING: the parameter order of spark.lang.string.join has changed"
        print "         Please use (join $strings $connective)"
        connective,strings = strings,connective
    return to_string(connective).join([to_string(x) for x in strings])

# stringSplit
#
# splits a string into a list of strings
def stringSplit(string, separator):
    return List(to_string(string).split(to_string(separator)))
