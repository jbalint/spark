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
#* "$Revision:: 26                                                        $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.version import *
from spark.internal.parse.usages import *
from spark.internal.exception import ProcessingError
from spark.internal.parse.pickleable_object import PickleableObject

################################################################
# Modes

class Mode(PickleableObject):
    __stateslots__ = (
        "source",
        "sigkeys",                      # keyword parameter keys as a list
        "keysRequired",                 # list of required keywords
        )
    __slots__ = __stateslots__ + (
        "sigreq",            # minimum number of positional parameters
        "sigrep", # number of positional parameters to repeat (for rest: args)
        "modelength",                    # number of characters up to / or end
        )

    def __init__(self, source, sigkeys, keysRequired):
        self.source = source
        self.sigkeys = list(sigkeys or ())   # must be list to use .index method
        self.keysRequired = list(keysRequired or ())
        self.__restore__()

    def __restore__(self):
        (sigreq, sigrep, numkeys, modelength) = _getModeSig(self.source)
        self.sigreq = sigreq
        self.sigrep = sigrep
        self.modelength = modelength
        if numkeys != len(self.sigkeys):
            raise ProcessingError("Number of keys %d does not match mode %s" \
                                    %(len(self.sigkeys), self.source))

    def __eq__(self, other):
        return self.__class__ == other.__class__ \
               and self.source == other.source \
               and self.sigkeys == other.sigkeys \
               and self.keysRequired == other.keysRequired

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "<Mode:%s>"%self.source

    def __repr__(self):
        if self.sigkeys:
            return "<Mode:%s:%s>"%(self.source, "".join(self.sigkeys))
        else:
            return self.__str__()

    def getResult(self):
        return self.source[0]

    def resultSatisfies(self, usage, allowVirtual):
        return (allowVirtual or self.source[1] == REQSYM) \
               and usageIsWeakerOrSame(usage, self.source[0])

    def __getitem__(self, indexkey):
        "For a given Mode, work out the specific Kind of a parameter"
        if not (isinstance(indexkey, int)): raise AssertionError
        # indexkey is negative for a key parameter and non-negative for positional
        if indexkey < 0:
            modeindex = self.modelength + indexkey
        else:
            sigreq = self.sigreq
            if indexkey < sigreq:
                modeindex = indexkey + 2
            else:
                sigrep = self.sigrep
                if sigrep == 1:
                    modeindex = sigreq + 3
                else:
                    try:
                        modeindex = sigreq + 3 + ((indexkey - sigreq) % sigrep)
                    except ZeroDivisionError:
                        raise IndexError, "mode index out of range"
        return self.source[modeindex]

    def satisfiedBy(self, reqUsage, enumerated_subusages, allowVirtual):
        if not self.resultSatisfies(reqUsage, allowVirtual):
            return False
        for indexkey, usage in enumerated_subusages:
            if usage is not None:
                subReqUsage = self[indexkey]
                if not usageIsWeakerOrSame(subReqUsage, usage):
                    return False
        else:
            return True

    def isWeakerOrSame(self, other):
        for (s, o) in zip(self.source, other.source):
            if s not in SEPARATORS:
                if not usageIsWeakerOrSame(s, o):
                    return False
        else:
            return True
        

    def orderedElements(self, obj, keynamefn):
        """Check that obj satisfies the signature of self and is well formed.
        The function keynamefn returns the string name of the keyword for
        keyword arguments and None for other arguments.
        If all is well, return a list
        [(0, posarg_0), (1, posarg_1), ... (-n, keyarg_0), ... (-1, keyarg_n+1)]
        where posarg_i is the i-th positional arg and keyarg_i is the argument
        corresponding to the i-th keyword in sigkeys. If the i-th keyword
        was omitted, then keyarg_i = None.
        If there was a problem, return a string instead."""
        sigrep = self.sigrep
        sigreq = self.sigreq
        sigkeys = self.sigkeys
        keyargs = [None for key in sigkeys]
        numpositional = None
        result = list(enumerate(obj))
        for i, component in result:
            fname = keynamefn(component)
            if fname:                   # a keyword
                try:
                    index = sigkeys.index(fname)
                except ValueError:
                    if sigkeys:
                        keys = " ".join(sigkeys)
                        return "Incorrect keyword %r, expecting one of %r"%(fname, keys)
                    else:
                        return "No keyword is allowed here"
                numsubcomponents = len(component)
                if numsubcomponents != 1: # correctly formed key component
                    return "Keyword %s should be followed by one parameter not %d"%(fname, numsubcomponents)
                if numpositional is None: # first keyword found
                    numpositional = i
                if keyargs[index] is None:
                    keyargs[index] = component[0]
                else:
                    return "Keyword %s is duplicated"%fname
            elif numpositional is not None: # not a keyword, but after keywords
                return "Positional parameter after keyword parameter %s"%fname
            else:
                pass                    # leave it as is
        # remove keyword arguments from result and ensure numpositional set
        if numpositional is not None: # keywords found
            del result[numpositional:]
        else:
            numpositional = len(result)
        if keyargs:
            # check for required keyword arguments
            for reqKey in self.keysRequired:
                if keyargs[sigkeys.index(reqKey)] is None:
                    return "Required keyword %r not supplied"%reqKey
            # prepend keyword values with a negative index
            for i in range(-len(sigkeys), 0):
                keyargs[i] = (i, keyargs[i])
            # add the keyword arguments to the end of result
            result.extend(keyargs)
        # Check for the correct number of positional parameters
        err = None
        if sigrep == 0 and numpositional != sigreq:
            err = "exactly %d"%sigreq
        elif numpositional < sigreq:
            err = "at least %d"%sigreq
        elif sigrep > 1 and (numpositional - sigreq) % sigrep != 0:
            if sigreq == 0:
                err = "a multiple of %d"%sigrep
            else:
                err = "%d plus a multiple of %d"%(sigreq, sigrep)
        if err is not None:
            return "Expecting the number of positional parameters to be %s, not %d" \
                   % (err, numpositional)
        return result



def _getModeSig(mode):
    l = len(mode)
    endpos = mode.find(ENDSYM)
    if endpos < 0:
        endpos = l
    reppos = mode.find(REPSYM)
    keypos = mode.find(KEYSYM)
    if reppos > 0 and keypos > 0:
        return (reppos-2, keypos-reppos-1, endpos-keypos-1, endpos)
    elif reppos > 0:
        return (reppos-2, endpos-reppos-1, 0, endpos)
    elif keypos > 0:
        return (keypos-2, 0, endpos-keypos-1, endpos)
    else:
        return (endpos-2, 0, 0, endpos)
