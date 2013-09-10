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
from spark.internal.common import LOCAL_ID_PREFIX
from spark.internal.parse.mode import Mode
from spark.internal.parse.combiner import PARALLEL
from spark.internal.parse.basicvalues import Symbol
from spark.internal.exception import ProcessingError
from spark.internal.parse.pickleable_object import PickleableObject

################################################################
################
####
#
# Info that the stage 1 processing can determine


class Decl(PickleableObject):
    """Declaration of an identifier."""
    __stateslots__ = (
        "_sym",
        "modes",       # sequence of allowed Modes
        "combinerString",
        "impString")
    __slots__ = __stateslots__ + (
        "combiner",                     # string  name of combination object
        "impGen",
        "imp",
        )

    USES_KEYWORDS = True

    def __init__(self, sym, modeStrings, sigkeys=None, keysRequired=None, \
                 imp=None, combiner=None):
        self._sym = sym
        sigkeys = list(sigkeys or ())   # must be list to use .index method
        keysRequired = list(keysRequired or ())
        if not (modeStrings): raise AssertionError, \
           "At least one mode string is required"
        self.modes = []
        for string in modeStrings:
            mode = Mode(string, sigkeys, keysRequired)
            for priorMode in self.modes:
                if mode.isWeakerOrSame(priorMode):
                    raise ProcessingError("Mode %s must appear before stronger mode %s"%(mode.source, priorMode.source))
            self.modes.append(mode)
        #self.modes = [Mode(string, sigkeys, keysRequired) for string in modeStrings]
        self.impString = imp
        if imp:
            self.impGen = _PythonReference(imp)
        else:
            from spark.pylang.defaultimp import DefaultImp
            self.impGen = DefaultImp
        self.imp = None # delay instantiation until after self.setFP called
        self.combinerString = combiner
        self.combiner = (combiner and _PythonReference(combiner)) or PARALLEL

    def __repr__(self):
        return "<Decl %s>"%self._sym.name

    def asSymbol(self):
        return self._sym

    def __eq__(self, other):
        return self.__class__ == other.__class__ \
               and self.asSymbol() == other.asSymbol() \
               and self.modes == other.modes \
               and self.combinerString == other.combinerString \
               and self.impString == other.impString

    def __ne__(self, other):
        return not self.__eq__(other)

    def getImp(self):
        imp = self.imp
        if imp is None:
            imp = self.impGen(self)
            self.imp = imp
        return imp
        
    def optMode(self, usage):
        "Look for the first mode that has a result that satisfies usage"
        # This should be the WEAKEST constraint (and maybe a % mode)
        # Assuming weaker result <=> weaker required,
        # weaker result modes should come before stronger
        # -=... before +=... and x%... before x=... and x=...
        for mode in self.modes:
            if mode.resultSatisfies(usage, True):
                return mode
        return None

    def checkMode(self, reqUsage, elements):
        "Return the strongest (last) result usage of any mode that matches subresults"
        chosenMode = None
        usages = [(i,usage(sub)) for (i, sub) in elements]
        for mode in self.modes:
            if mode.satisfiedBy(reqUsage, usages, False):
                chosenMode = mode
        return chosenMode


    def __restore__(self):
        self.combiner = (self.combinerString and _PythonReference(self.combinerString)) or PARALLEL
        if self.impString:
            self.impGen = _PythonReference(self.impString)
        else:
            from spark.pylang.defaultimp import DefaultImp
            self.impGen = DefaultImp
        self.imp = self.impGen(self)



def usage(x):
    if x is None:
        return None
    else:
        return x.usage

class NoKeyDecl(Decl):           # no key arguments
    """Declaration that does not involve an id and does not treat any
    components as keys."""
    __slots__ = (
        )
    USES_KEYWORDS = False

################################################################

class _PythonReference(PickleableObject):
    __stateslots__ = (
        "_module",
        "_attrname",
        )
    __slots__ = __stateslots__

    def __init__(self, modname_name):
        dotpos = modname_name.rfind(".")
        if dotpos < 0:
            raise ValueError("Expecting python reference to be of the form module.attribute: %s"%modname_name)
        modname = modname_name[:dotpos]
        attrname = modname_name[dotpos+1:]
        self._attrname = attrname
        import sys
        try:
            __import__(modname)
        except ImportError, e:
            raise ValueError("Error during import of Python module %s: %s"%(modname, e))
        self._module = sys.modules[modname]
        if not hasattr(self._module, attrname):
            raise ValueError("Python module %s has no attribute %s"%(modname, attrname))

    def __getattr__(self, name):
        return getattr(getattr(self._module, self._attrname), name)

    def __call__(self, *args, **keyargs):
        return getattr(self._module, self._attrname)(*args, **keyargs)
    
# def _PythonReference(modname_name):
#         dotpos = modname_name.rfind(".")
#         if dotpos < 0:
#             raise ValueError("Expecting python reference to be of the form module.attribute: %s"%modname_name)
#         modname = modname_name[:dotpos]
#         attrname = modname_name[dotpos+1:]
#         try:
#             mod = __import__(modname)
#         except ImportError, e:
#             raise ValueError("Cannot import Python module %s:\n %s"%(modname, e))
#         import sys
#         mod = sys.modules[modname]
#         try:
#             return getattr(mod, attrname)
#         except AttributeError:
#             raise ValueError("Python module %s has no attribute %s"%(modname, attrname))
