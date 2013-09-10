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
from spark.internal.exception import LowError
from spark.internal.set import BITS, rbitstring, bitmap_indices
from spark.internal.common import ABSTRACT
from spark.internal.parse.basicvalues import isString

# A call_mode is a bitmap with one bit for each parameter in a call -
# 0 for an evaluable parameter, 1 for a non-evaluable parameter. The
# least significant bit corresponds to first parameter.

ALL_EVALUABLE_CALL_MODE = 0

def call_mode_first_evaluable(call_mode):
    return not (call_mode & 1)

def modestring_bitmap(modestring, zerochar, onechar):
    mode = 0
    for b,bit in zip(modestring, BITS):
        if b == onechar:
            mode = mode | bit
        elif b != zerochar:
            raise LowError("Mode string contains something other" \
                                  "than + or -")
    return mode

class Mode(object):
    __slots__ = (
        "_bitmap", # 1 for each parameter required to be evaluable
        "_modestring",
        )
    zerochar = ABSTRACT
    onechar = ABSTRACT
    def __init__(self, modestring):
        if not isString(modestring):
            raise LowError("Mode should be a string: %r", modestring)
        self._modestring = modestring
        self._bitmap = modestring_bitmap(modestring, \
                                         self.zerochar, self.onechar)

    def __repr__(self):
        return "%s(%r)"%(self.__class__.__name__, self._modestring)

    def bitmap(self):
        return self._bitmap

class RequiredMode(Mode):
    __slots__ = (
        "_required_indices", #tuple of indices of args required to be evaluable
        )
    zerochar = "-"                      # not required to be evaluable
    onechar = "+"                       # required to be evaluable

    def __init__(self, modestring):
        Mode.__init__(self, modestring)
        self._required_indices = bitmap_indices(self._bitmap)
        
    def satisfied_by(self, call_mode):
        return not (self._bitmap & call_mode)

    def required_indices(self):
        return self._required_indices

class DetMode(Mode):
    __slots__ = ()
    zerochar = "-"                      # not required to be evaluable
    onechar = "+"                       # required to be evaluable

        
    def satisfied_by(self, call_mode):
        return not (self._bitmap & call_mode)
    

#NONE_REQUIRED_MODE = RequiredMode("")        # others are "-" by default
#FIRST_REQUIRED_MODE = RequiredMode("+")      # others are "-" by default

# class CallModeSpec(object):
#     """Produces call mode for subcall based on call_mode of bindings"""
#     __slots__ = (
#         "base_call_mode",
#         "ems_call_bit_pairs",
#         "_repr"
#         )

#     def __init__(self, patexprs):
#         ems_call_bit_pairs = []
#         base_call_mode = 0
#         for (patexpr, bit) in zip(patexprs,BITS):
#             ems = patexpr.evaluable_mode_spec()
#             if ems.never_evaluable(): # know now
#                 base_call_mode = base_call_mode | bit
#             elif ems.always_evaluable(): # know now
#                 pass
#             else: # don't know now check at call time
#                 ems_call_bit_pairs.append((ems, bit))
#         self.base_call_mode = base_call_mode
#         self.ems_call_bit_pairs = ems_call_bit_pairs

#     def __repr__(self):
#         emodes = [str(c.evaluable_mode_spec()) for c in self]
#         return "<CallModeSpec %s>"%("".join(map(str, emodes)))

#     def mode(self, bindings):
#         call_mode = self.base_call_mode
#         for ems,bit in self.ems_call_bit_pairs:
#             if not ems.evaluable(bindings.call_mode): # arg is nonevaluable
#                 call_mode = call_mode | bit
#         return call_mode

class _EvaluableModeSpec(object):
    """Determines whether a patexpr is evaluable based on the call_mode"""
    __slots__ = (
        # -1 if the patexpr is never evaluable, or
        # 1 for each bivar that is first used in the patexpr
        "_nonevaluable_mode",
        )

    def __init__(self, nonevaluable_mode):
        try:
            nonevaluable_mode = int(nonevaluable_mode)
        except OverflowError:
            pass
        self._nonevaluable_mode = nonevaluable_mode

    def bitmap(self):
        return self._nonevaluable_mode

    def binds_locals(self):
        return self._nonevaluable_mode < 0

    def binds_bivars(self):
        return self._nonevaluable_mode > 0

    def evaluable(self, call_mode):
        nem = self._nonevaluable_mode
        return nem >= 0 and not (nem & call_mode)

    def __eq__(self, other):
        return self._nonevaluable_mode == other._nonevaluable_mode

    def __ne__(self, other):
        return self._nonevaluable_mode != other._nonevaluable_mode
        
    def __str__(self):
        nem = self._nonevaluable_mode
        if nem == 0:
            return "E"
        elif nem < 0:
            return "N"
        else:
            return "(%s)"%rbitstring(nem, ".R")

    def __repr__(self):
        return "<EvaluableModeSpec %s>"%self.__str__()

    def always_evaluable(self):
        return self._nonevaluable_mode == 0

    def never_evaluable(self):
        return self._nonevaluable_mode < 0
    

NEVER_EVALUABLE_MODE_SPEC = _EvaluableModeSpec(-1)
ALWAYS_EVALUABLE_MODE_SPEC = _EvaluableModeSpec(0)

def evaluable_mode_spec_from_components(patexpr):
    bitmap = 0
    for component in patexpr:
        bitmap = bitmap | component.evaluable_mode_spec().bitmap()
    return _EvaluableModeSpec(bitmap)

def evaluable_mode_spec_for_if(patexpr):
    comps = patexpr._components
    truebitmap = comps[1].evaluable_mode_spec().bitmap()
    falsebitmap = comps[2].evaluable_mode_spec().bitmap()
    return _EvaluableModeSpec(falsebitmap | truebitmap)

def evaluable_mode_spec_from_vars(patexpr):
        """The mode of an expression specifies which bivars appear for
        the first time (outside the parameters) in patexpr and
        therefore will be bound in this expression (if they are not
        inputs). This is expressed as a _Set bitmap, one bit per
        parameter, 1 if bound first in this patexpr. If some local
        (non-parameter) variable appears for the first time in this
        expression, then the bitmap is -1, indicating that it is never
        evaluable."""
        
        # This will have to change when we allow patexprs as formal parameters
        vars_bound_here = patexpr.used_first_here() & patexpr.free_vars()
        bivars = patexpr.context().bivars
        if vars_bound_here & ~bivars:
            return NEVER_EVALUABLE_MODE_SPEC
        else:
            return _EvaluableModeSpec((vars_bound_here & bivars).bitmap())
