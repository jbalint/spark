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
#* "$Revision:: 215                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from __future__ import generators
from spark.internal.version import *
from spark.internal.exception import LowError, UnlocatedError
#from types import ListType, TupleType, IntType, StringType
from cStringIO import StringIO
import time, sys, os, md5
#from spark.internal.parse.pickling import *
from spark.internal.common import NEWPM, DEBUG, ABSTRACT, POSITIVE, SOLVED, NOT_SOLVED, plural, BUILTIN_PACKAGE_NAME, LOCAL_ID_PREFIX
from spark.internal.source_locator import get_source_locator
from spark.internal.parse.basicvalues import Symbol, Variable, isVariable, Structure, Symbol, PREFIX_COMMA_SYMBOL, PREFIX_PLUS_SYMBOL, PREFIX_MINUS_SYMBOL, value_str, ConstructibleValue, installConstructor, getNewIdNum, createList
from spark.internal.parse.mode import *
from spark.internal.parse.usages import *
from spark.internal.parse.expr import *
from spark.internal.parse.combiner import PARALLEL
#from spark.internal.parse.sets_extra import *
from spark.internal.parse.cyclefinder import computeCycles
from spark.internal.repr.common_symbols import *
from spark.pylang.implementation import Imp
from spark.internal.parse.fip import *
from spark.internal.parse.pickleable_object import PickleableObject, common_pickle
from spark.internal.persist import persist_report_load_modpath
from spark.internal.persist_aux import is_resuming
from spark.internal.parse.errormsg import *
from spark.internal.parse.searchindex import setIndex, binarySearch
from spark.internal.parse.filesys import getInfoCache, FileInfo, PFileInfo


from sets import Set, ImmutableSet
debug = DEBUG(__name__)#.on()

#@-timing# from spark.internal.timer import TIMER
#@-# T_read = TIMER.newRecord("read")
#@-# T_readCache = TIMER.newRecord("readCache")
#@-# T_writeCache = TIMER.newRecord("writeCache")
#@-# T_parse = TIMER.newRecord("parse")
#@-# T_stage12 = TIMER.newRecord("stage12")
#@-# T_stage3 = TIMER.newRecord("stage3")
#@-# T_stage4 = TIMER.newRecord("stage4")

#Testing Script. Begin:
#from spark.internal.debug.chronometer import chronometer, chronometers, print_chronometers, reset_chronometers
#chronometers["stageZeroProcess"] = chronometer("stageZeroProcess")
#chronometers["stageOneTwoProcess"] = chronometer("stageOneTwoProcess")
#chronometers["stageTwoProcess"] = chronometer("stageTwoProcess")
#Testing Script. End.

# ids starting with _ are local to the SPU, not exported, nor package-visible

################################################################



# Level 0 errors occur before we can get the exprs of a SPU

class E001ParseError(ErrorMsg):
    level = F0
    argnames = ["msg"]
    format = "Parsing error: %(msg)s"

class E002FileError(ErrorMsg):
    level = F0
    argnames = ["msg"]
    format = "File error: %(msg)s"

class E003NoTerms(ErrorMsg):
    level = F0
    argnames = []
    format = "String contains no terms"

class E004MultipleTerms(ErrorMsg):
    level = F0
    argnames = []
    format = "String contains multiple terms"
    

# Level 1 errors occur after we have exprs, but before we can extract
# all the declarations, imports, etc.

class E101CircularDependencies(ErrorMsg):
    level = F1
    argNames = ["files"]
    format = "Circular dependencies: %(files)s"

class E102SpecialImportExport(ErrorMsg):
    level = F1
    argnames = ["id", "pkg"]
    format = "Exported id '%(id)s' must specially imported or declared in '%(pkg)s'"
    description = """You must not export an imported id that is not specially imported. The reason is that we want to ensure AllExportsHaveDecls."""

class E103NoDeclaration(ErrorMsg):
    level = F1
    argnames = ["id"]
    format = "No visible declaration for '%(id)s'"
    description = """Every xxx: ... or {xxx ...} top level structure is expected to be declared already"""

class E104NoStageOneMode(ErrorMsg):
    level = F1
    argnames = ["sym"]
    format = "The declaration for '%(sym)s' has no stage one mode declared"
    description = """Every xxx: ... or {xxx ...} top level structure must have a stage one mode declared"""

class E105InvalidArguments(ErrorMsg):
    level = F1
    argnames = ["msg"]
    format = "%(msg)s"
    description = "The arguments to a stage one operation must match the declaration"

class E106NoStageOneImplementation(ErrorMsg):
    level = F1
    argnames = ["sym"]
    format = "No stage one implementation exists for '%(sym)s'"

class E107ProcessingError(ErrorMsg):
    level = F1
    argnames = ["errstr", "errid"]
    format = "Processing error - %(errstr)s [%(errid)s]"

class W108DuplicateExport(ErrorMsg):
    level = WARN
    argnames = ["id"]
    format = "Ignoring duplicate export of '%(id)s'"

class W109DuplicateExportall(ErrorMsg):
    level = WARN
    argnames = []
    format = "Ignoring duplicate exportall"

class E110ExportLocal(ErrorMsg):
    level = F1
    argnames = ["id"]
    format = "Cannot export file-local id '%(id)s'"

class E111ImportUnexported(ErrorMsg):
    level = F1
    argnames = ["fromId", "pkg"]
    format = "Cannot import '%(fromId)s' from '%(pkg)s' - not exported from package file"
    description = """If a package is declared special for importing, then any symbol in an explicit import from that package must be exported in the package file itself."""

# SpecialImportRestrictions - (stage 1 test)

#  - When doing a direct special import from a package, all the exported
#    ids must be defined or specially imported into that package core
#    file.

class E112ImportDeclUnavailable(ErrorMsg):
    level = F1
    argnames = ["fromId", "pkg"]
    format = "Id '%(fromId)' is neither declared in nor specially imported into file '%(pkg)s'"

class E113AlreadyDeclared(ErrorMsg):
    level = F1
    argnames = ["id"]
    format = "Id '%(id)s' is already declared"

class E114AlreadySpeciallyImported(ErrorMsg):
    level = F1
    argnames = ["id", "sym"]
    format = "Id '%(id)s' is already specially imported: '%(sym)s'"

class E115AlreadyImported(ErrorMsg):
    level = F1
    argnames = ["id", "sym"]
    format = "Id '%(id)s' is already imported: '%(sym)s'"

class E116InvalidPackageFile(ErrorMsg):
    level = F1
    argnames = ["pkg"]
    format = "Cannot process package file '%(pkg)s'"
    description = "We need a package file to be at least OK1"

class E117NotCorePackageFile(ErrorMsg):
    level = F1
    argnames = ["file", "pkg"]
    format = "File '%(file)s' is in package '%(pkg)s' - it is not a core package file"
    description = "We can only import from a package, not a non-core file inside a different package"

class E118ChangePackage(ErrorMsg):
    level = F1
    argnames = ["pkg"]
    format = "The package was already set to '%(pkg)s'"

class E151NoConcludeEffectsAllowed(ErrorMsg):
    level = F1
    argnames = []
    format = "Only directives such as main:, import*:, export*:, and special: are allowed here"


# Level 2 errors occur while looking through the exprs to determine
# modes and usages.

# LocalsDeclared - (stage 2 test)

#  - all the local ids used in a file must be declared in the file.

class E201UndeclaredLocal(ErrorMsg):
    level = F2
    argnames = ["id"]
    format = "No declaration for local id '%(id)s'"

class E202LoadUseBeforeDeclared(ErrorMsg):
    level = F2
    argnames = ["id"]
    format = "At load time, id '%(id)s' is used before it is declared in this file"

class E203NotEnoughOuterContexts(ErrorMsg):
    level = F2
    argnames = []
    format = "There are not enough outer contexts to interpret this variable"

class E204VarUsedOutsideItsScope(ErrorMsg):
    level = F2
    argnames = []
    format = "Use of variable outside of its scope"

class E205VarUsedOutsideThisScope(ErrorMsg):
    level = F2
    argnames = ["var"]
    format = "Variable %(var)s is not known to be bound outside this scope, yet it is used elsewhere."

class W206VarMultiple(ErrorMsg):
    level = WARN
    argnames = ["var"]
    format = "Variable %(var)s appears more than once"

class W207CannotFindCSP(ErrorMsg):
    level = WARN
    argnames = []
    format = "Cannot work out where .csp file to cache the processing should go"

class W208CannotWriteCSP(ErrorMsg):
    level = WARN
    argnames = []
    format = "Error writing .csp file to cache the processing"


# Level 3 errors occur when collecting together all the stage 1 & 2
# information from the files in a package that the core file requires.

# AllFilesOK1 - (stage 3 test)

#  - All the package files of a package are at least at level OK1 and
#    pspu.allFiles contains a list of these files.

class E301InformationUnavailable(ErrorMsg):
    level = F3
    argnames = ["filename"]
    format = "Cannot get declaration information from file '%(filename)s'"

class E302IncompatibleDeclImport(ErrorMsg):
    level = F3
    argnames = ["id", "file1", "file2"]
    format = "Incompatible declaration or imports of '%(id)s' in '%(file1)s' and '%(file2)s'"
    description = """In all the pakage files of a package, an id may only be declared once, cannot be both declared and explicitly imported, and if explicitly imported in multiple files must be imported from the same package."""

# AllExportsHaveDecls - (stage 3 test)

#  - Everything exported from a package must have either a declaration
#    in the package or be specially imported into the package. This
#    ensures that pspu.allExports is a dict mapping id strings to decls.

class E303UndeclaredExport(ErrorMsg):
    level = F3
    argnames = ["id"]
    format = "No declaration or special import of exported id '%(id)s'"
    
# Level 4 errors occur when checking the files of a package against
# the declarations of things imported from other packages.

class E401BadCoreFile(ErrorMsg):
    level = F4
    argnames = ["pkg"]
    format = "Errors in core package file '%(pkg)s'"
    description = "When doing level 4 processing of a non-core file in a package, we require the core file to be OK4"
    
# NoImportConflict - (stage 4 test on package core file)

#  - None of the importalls end up importing an id that a declaration
#    declares or an explicit import or anything that another importall
#    imports.

class E402ImportallImportConflict(ErrorMsg):
    level = F4
    argnames = ["id", "pkg", "sym"]
    format = "Importall of '%(id)s' from '%(pkg)s' conflicts with import of '%(sym)s'"
class E403ImportallDeclConflict(ErrorMsg):
    level = F4
    argnames = ["id", "pkg"]
    format = "Importall of '%(id)s' from '%(pkg)s' conflicts with declaration"

class E404ImportallConflict(ErrorMsg):
    level = F4
    argnames = ["id", "pkg1", "pkg2"]
    format = "Importall of '%(id)s' from '%(pkg1)s' conflicts with importall from  '%(pkg2)s'"

class E405ImportUnexported(ErrorMsg):
    level = F4
    argnames = ["fromId", "pkg"]
    format = "Cannot import '%(fromId)s' from '%(pkg)s' - not exported"

class E406ImportConflict(ErrorMsg):
    level = F4
    argnames = ["id", "pkg"]
    format = "Cannot import '%(id)s', it is already defined in '%(pkg)s'"
    description = "A file outside a package cannot import an id that conflicts with an existing package declaration or import"

class E407DeclConflict(ErrorMsg):
    level = F4
    argnames = ["id", "pkg"]
    format = "Cannot declare '%(id)s', it is already defined in '%(pkg)s'"
    description = "A file outside a package cannot declare an id that conflicts with an existing package declaration or import"

class W408IdMissing(ErrorMsg):
    level = WARN
    argnames = ["id", "pkg", "num"]
    format = "No declaration (yet) for id '%(id)s' in package '%(pkg)s' (x%(num)d)"
    description = "If a declaration cannot be found for an id in a file outside the package, it will need to be declared at load time."
        # See if it exists unexported in an importall package

class E409IdMissing(ErrorMsg):
    level = F4
    argnames = ["id", "pkg", "num"]
    format = "No declaration for '%(id)s' in package '%(pkg)s' (x%(num)d)"
    description = "A declaration must exist for every id if the file is inside a package."

class W410ImportImportall(ErrorMsg):
    level = WARN
    argnames = ["id", "pkg"]
    format = "Id '%(id)s' is both import-ed and importall-ed from '%(pkg)s'"
    # TODO: say what files the import(all)s appear in
    
# DeclaredBeforeUse4 - (stage 4 test)

#  - If something is used *at load time* in a file, it must either be
#  declared in a different package (and load order is sorted out at
#  load time) or it must be declared in this file or the package core
#  file. It cannot be declared in a different file inside the package.

class E411LoadUseNoDecl(ErrorMsg):
    level = F4
    argnames = ["id", "pkg"]
    format = "Id '%(id)s' must be declared in this file or file '%(pkg)s' if used at load time"

class E412LoadUseNoDeclCore(ErrorMsg):
    level = F4
    argnames = ["id", "pkg"]
    format = "Id '%(id)s' must be declared in this file if used at load time"

class W413LoadUseNoDecl(ErrorMsg):
    level = WARN
    argnames = ["id", "pkg"]
    format = "Id '%(id)s' used at load time is not declared in this file or file '%(pkg)s' - assume it will be present at load time"


class E416InvalidPackageFile(E116InvalidPackageFile):
    level = F4
    # TODO: report the file it was imported into

class E417NotCorePackageFile(E117NotCorePackageFile):
    level = F4
    # TODO: report the file it was imported into

class W418ImportUnexported(ErrorMsg):   # see E405
    level = WARN
    argnames = ["fromId", "pkg"]
    format = "Cannot (yet) import '%(fromId)s' from '%(pkg)s' - not (yet) exported"


################################################################
# filename to SPU mapping

class FilenameSPU(object):
    """Implements a mapping from filename to SPU, fetching info from
    the file system as necessary."""
    __slots__ = (
        "_dict",
        "_inprogress",
        )

    def __init__(self):
        self._dict = {}
        self._inprogress = []

    def get(self, filename):
        # Always returns an SPU (creating one if necessary)
        """Do as much decl processing as possible of file if not already done.
        Return whether the decls, imports, & exports could be processed."""
        # Check to see if we are already processing this file
        spu = self._dict.get(filename)
        if spu is None:
            # check for circular dependencies
            #
            # This check should be extended to ALL calls of stageOneTwoProcess
            for i,s in enumerate(self._inprogress):
                if s.filename == filename:
                    names = [x.filename for x in self._inprogress[i:]]
                    names.append(filename)
                    files = " -> ".join(names)
                    for spu in self._inprogress[i:]:
                        spu.err(E101CircularDependencies(None, files))
                    return s
            #print "PROCESSING", spu
            # Check for an already existing .csp file
            #@-timing# T_readCache.start()
            spu = readFromCSP(filename)
            #@-timing# T_readCache.stop()
            if spu:
                spu.checkRequiredHashs()
            else:
                # Create and set the exprs of the SPU
                if filename == BUILTIN_PACKAGE_NAME:
                    spu = BuiltinFileSPU(BUILTIN_PACKAGE_NAME)
                else:
                    spu = FileSPU(filename)
                #@-timing# T_read.start()
                spu.fileUpdate(None)
                #@-timing# T_read.stop()
            # Do stage one & two processing
            if not spu.atLeast(OK2):
                try:
                    self._inprogress.append(spu)
                    #@-timing# T_stage12.start()
                    spu.stageOneTwoProcess()
                    #@-timing# T_stage12.stopstart(T_writeCache)
                    writeToCSP(spu)
                    #@-timing# T_writeCache.stop()
                finally:
                    self._inprogress.pop()
            # record the spu in _dict
            self._dict[filename] = spu
        return spu

    # TODO: tidy up the following
    
    def get3(self, filename):
        spu = self.get(filename)
        if spu.errorLevel == OK2:
            #@-timing# T_stage3.start()
            spu.stageThreeProcess()
            #@-timing# T_stage3.stop()
        return spu

    def get4(self, filename):
        spu = self.get3(filename)
        if spu.errorLevel == OK3:
            #@-timing# T_stage4.start()
            spu.stageFourProcess()
            #@-timing# T_stage4.stop()
        return spu

    def set(self, filename, spu):
        if filename in self._dict:
            raise AssertionError, "SPU is already set for %s"%filename
        if not isinstance(spu, SPU):
            raise AssertionError, "Not a SPU"
        if not spu.atLeast(NOT_RAW):
            raise AssertionError, "SPU has not been updated"
        self._dict[filename] = spu

    def delete(self, filename):
        del self._dict[filename]

    def items(self):
        return self._dict.items()
        
    def clear(self):
        self._dict.clear()


FILENAME_SPU = FilenameSPU()

################################################################
# SPU - Spark Processing Unit


INPROCESS = intern("INPROCESS")

class SPU(PickleableObject):
    __stateslots__ = (
        "filename",             # string
        "_exprs",
        # during stage 1 these are used
        "_currentPackageName",
        # These are filled during stage 1
        "main_name",                  # the main: action
        "_declImport", # dict mapping id string to local decl, special imported decl, or symbol
        "_importalls", # set of package name strings
        "_exports", # set of idstrings exported (include None for all during stageOne)
        "_cache",          # cache of id string -> decl or symbol used
        "specials",             # set of packages required for stage1
        "needed",      # set other files/packages needed to be loaded
        "undeclaredLoadUse", # (exprs whose functor is)/ids undeclared at load time based on stage 1
        "errors",
        "errorLevel",
        # stage three info for package core file
        "allFiles", # all required files minus those in a different package
        "allExports",                   # dict mapping id to decl
        "allDeclImports",
        "allImportAlls",
        "allCache",                     # does not include local
        "allDecls",
        # stage four info
        "decls", # map id used to Decl or list of Exprs (if Decl unknown)
        )
    __slots__ = __stateslots__ + (
        "__weakref__",
        #"_processed",           # stage of processing
        # After successful open and read of file, these are set
        #"_text",
        # added by Shahin:
        #"sourceWasUsed",
        # end added by Shahin
        "index",                        # expr index of first expr
        )

    indexCompound = True
    
    def __init__(self, filename):
        if not isString(filename):
            raise AssertionError, "Filename should be a string: %r"%filename
        self.filename = filename
        #self._text = None
        self.errors = []
        self.errorLevel = RAW
        self.index = None
        self._currentPackageName = None

    def update(self, err, exprs):
        del self.errors[:]
        self._exprs = exprs
        self.errorLevel = OK0
        if err:
            self.err(err)
        else:
            self.__restore__()
        if not self.atLeast(OK0):
            printErrors(self, True)
        return self

    def __restore__(self):
        if self._exprs is not None:
            selfref = ref(self)
            for expr in self._exprs:
                expr.parentref= selfref
            setIndex(self, 0)
        # Note that we only persist information up to level 2 processing
        self.errorLevel = min(self.errorLevel, OK2)

    def atLeast(self, stage):
        if self.errorLevel >= stage:
            return self
        else:
            return None

    def err(self, err):
        if err.level is not None:
            self.errorLevel = min(self.errorLevel, err.level)
        self.errors.append(err)
        
    def __getitem__(self, index):
        return self._exprs[index]

    def __len__(self):
        return len(self._exprs)

    def __nonzero__(self):
        return True


    ################################################################
    # Stage 1 processing
    #
    # Process imports, exports, declarations

    def stageOneSetup(self):
        self.main_name = None
        self._currentPackageName = None
        self._declImport = {}
        self._exports = Set()
        self.specials = Set()
        self.specials.add(BUILTIN_PACKAGE_NAME)
        self.needed = Set()
        self._cache = {}
        self._importalls = Set()
        self._importalls.add(BUILTIN_PACKAGE_NAME)
        self.undeclaredLoadUse = []

    def stageOneFinish(self):
        # ENSURE CurrentPackageSet
        cp = self._currentPackageName or self.filename
        self._currentPackageName = cp
        # ENSURE ExportallsResolved
        exports = self._exports
        if None in exports:
            exports.remove(None)
            for (id, declSym) in self._declImport.items():
                if isinstance(declSym, Decl) \
                       and not id.startswith(LOCAL_ID_PREFIX) \
                       and not id in exports:
                    exports.add(id)
        # TEST E102SpecialImportExport
        # TODO: eliminate this if not needed - should be covered by ExportsDeclared
        for id in exports:
            declSym = self.findCacheId(id, False)
            if isSymbol(declSym) and declSym.modname != cp:
                # Not declared in this file or in this package and not
                # specially imported.
                self.err(E102SpecialImportExport(None, id, cp))
        # TEST E201UndeclaredLocal
        for id in self._cache:
            if id.startswith(LOCAL_ID_PREFIX) \
                   and id not in self._declImport:
                self.err(E201UndeclaredLocal(None, id))
        # TEST E202LoadUseBeforeDeclared
        # and change undeclaredLoadUse from a list of exprs to a set of idnames
        if self.undeclaredLoadUse:
            undeclared = Set()
            for expr in self.undeclaredLoadUse:
                idname = expr.functor.name
                declSym = self._declImport.get(idname)
                if isinstance(declSym, Decl):
                    self.err(E202LoadUseBeforeDeclared(expr, idname))
                else:
                    # These should be checked at stage four
                    undeclared.add(idname)
        else:
            undeclared = EMPTY_SET
        self.undeclaredLoadUse = undeclared
                    

    def stageOneTwoProcess(self, usage=PRED_UPDATE, allowStageOne=True, activity=LOADTIME):
        """Perform all the imports, exports, declarations, etc. that should
        give you all the declarations you need for stage two.
        Return True if no fatal errors occurred."""
        # This depends on :
        #   self
        #   the package spu (stage 1)
        #   and specially imported spus (stage 1)
        if not self.atLeast(OK0):
            return False
        #Testing Script. Begin:
#        global chronometers
#        chronometers["stageOneTwoProcess"].start()
        #Testing Script. End.        
        del self.errors[:] # remove all prior errors
        self.errorLevel = PROCESSING2
        self.stageOneSetup()
        for f in self.specials:
            self._validatePackageOrError(None, f)
        context = Context(self, None, None)
        for i,expr in enumerate(self._exprs): # TODO: check if/why we need i (DNM)
            # StageTwo part
            if self.atLeast(OK1) \
                   or isinstance(expr, ExprStructureColon) \
                   or isinstance(expr, ExprStructureBrace): # only do this if no bad error
                freevars = expr.validate(context, EMPTY_SET, activity, usage)
                # TODO - should check freevars rather than ignoring it
            # StageOne part
            #
            # This has to be able to work as well as possible without
            # exprs having being validated
            if allowStageOne:
                if self.stageOneProcessExpr(expr, False):
                    break               # on fatal error
        self.stageOneFinish()
        #Testing Script. Begin:
#        chronometers["stageOneTwoProcess"].stop()
        #Testing Script. End.
        if self.atLeast(PROCESSING2):
            self.errorLevel = OK2
            return True
        else:
            printErrors(self, True)
            return False
        # DNM - The following is delayed until a successful load of the file
        # SPU_RECORD.install(self)

    def stageOneProcessExpr(self, expr, noConcludeEffectsAllowed):
        "Perform stageOne effects for expr, returning True if a fatal error occurred"
        from spark.lang.builtin import NullConcludeImp
        if isinstance(expr, ExprList):
            for subexpr in expr:
                if self.stageOneProcessExpr(subexpr, True): # for now, disallow any conclude effects
                    return True
        elif isinstance(expr, ExprStructureColon) \
                 or isinstance(expr, ExprStructureBrace):
            idname = expr.functor.name
            #print "--processing--", expr
            #debug("processing %s", expr)
            #if True:
            try:
                decl = self.findCacheId(idname, False)
                if not isinstance(decl, Decl):
                    self.err(E103NoDeclaration(expr, idname))
                    return False
                mode = decl.optMode(STAGE_ONE_KIND)
                if mode is None:
                    self.err(E104NoStageOneMode(expr, decl.asSymbol()))
                    return False
                # check signature
                elts = mode.orderedElements(expr, keynameExpr)
                if isinstance(elts, basestring):
                    self.err(E105InvalidArguments(expr, elts))
                    return False
                imp = decl.getImp()
                if not imp:
                    self.err(E106NoStageOneImplementation(expr, \
                                                          decl.asSymbol()))
                elif noConcludeEffectsAllowed \
                         and not isinstance(imp, NullConcludeImp):
                    self.err(E151NoConcludeEffectsAllowed(expr))
                else:
                    if imp.stageOne(self, expr):
                        # There was a fatal processing that was handled
                        return True
            #else:
            except ProcessingError, e: # raising an exception terminates the processing
                errid = NEWPM.recordError()
                self.err(E107ProcessingError(expr, str(e), errid))
                return True
        elif noConcludeEffectsAllowed:
            self.err(E151NoConcludeEffectsAllowed(expr))
        return False

    def addUndeclaredLoadUse(self, expr):
        """Report that the functor of expr was used as loadtime before being declared"""
        self.undeclaredLoadUse.append(expr)

    def stageThreeProcess(self):
        """For a package file, this should aggregate package
        information. For other files, it does nothing."""
        # This depends upon:
        #   self (stage 2 - really only needs stage 1)
        #   spus in package (stage 1)
        if not self.atLeast(OK2):
            return
        # TODO: should remove any F3 errors
        self.errorLevel = PROCESSING3
        if self._currentPackageName != self.filename:
            self.allFiles = None
            self.allExports = None
            self.allDeclImports = None
            self.allImportAlls = None
            self.allCache = None
            self.errorLevel = OK3
            return
        # Aggregate information
        # Work out all SPUs required by core file that are in the package
        # TEST AllFilesOK1
        spus = []
        #print "COMPUTING allRequires FOR", self
        def addSPU(spu, parentSPU):     # NOTE: parentSPU not used!!!
            if spu not in spus:
                if not spu.atLeast(OK1):
                    self.err(E301InformationUnavailable(None, spu.filename))
                    spus.append(spu)
                elif spu._currentPackageName == self.filename:
                    spus.append(spu)
                    for f in spu.needed:
                        addSPU(FILENAME_SPU.get(f), spu)
                    for f in spu.specials:
                        addSPU(FILENAME_SPU.get(f), spu)
        addSPU(self, self)
        if not self.atLeast(PROCESSING3):
            printErrors(self, True)
            return
        # ENSURE AllImportAllsSet
        # ENSURE AllExportsSet
        # ENSURE AllDeclImportsSet
        declImports = {}
        importAlls = Set()
        for spu in spus:
            importAlls.union_update(spu._importalls)
            for (id, declSym) in spu._declImport.items():
                oldDeclSym = declImports.get(id)
                if oldDeclSym is None:
                    declImports[id] = declSym
                elif oldDeclSym != declSym:
                    # duplicate declaration or import
                    # find other SPU
                    for spu1 in spus:
                        if id in spu1._declImport:
                            f1 = spu1.filename
                            break
                    f2 = spu.filename
                    self.err(E302IncompatibleDeclImport(None, id, f1, f2))
        if not self.atLeast(PROCESSING3):
            printErrors(self, True)
            return
        # ENSURE AllCacheSet
        cache = declImports.copy()
        for spu in spus:
            for (id, declSym) in spu._cache.items():
                # TODO: check all alternatives are handled correctly
                # TODO: check for incompatible special imports
                # Ensure specially imported usages are recorded as decls
                # and all other non-local usages are recorded.
                if isinstance(declSym, Decl) or \
                       (id not in cache and not id.startswith(LOCAL_ID_PREFIX)):
                    cache[id] = declSym
        # TEST AllExportsHaveDecls
        # Check that all exports have decls
        exports = {}
        for spu in spus:
            for id in spu._exports:
                if id not in exports:
                    decl = cache.get(id)
                    if not isinstance(decl, Decl):
                        self.err(E303UndeclaredExport(None, id))
                    else:
                        exports[id] = decl
        if not self.atLeast(PROCESSING3):
            printErrors(self, True)
            return
        self.allFiles = [s.filename for s in spus]
        self.allExports = exports
        self.allDeclImports = declImports
        self.allImportAlls = importAlls
        self.allCache = cache
        if self.atLeast(PROCESSING3):
            self.errorLevel = OK3
        else:
            printErrors(self, True)


    def stageFourDecl(self, id, expr, pspu):
        """If we can find a decl for id, return it,
        otherwise record an error and return None"""
        # look for (non-local) decl from package or local decl from file
        x = pspu.allDecls.get(id) or self.decls.get(id)
        if isinstance(x, Decl):  # known decl (packge or local)
            return x
        elif isinstance(x, list):     # previously failed to find decl
            if expr:
                x.append(expr)
            return None
        # else: x is None, i.e., not declared and not seen before
        if expr:
            self.decls[id] = [expr]
        else:
            self.decls[id] = []
        #G.breakpoint(id=id, expr=expr, self=self, pspu=pspu)
        #M.exitableConsole.exitableConsole()
        return None

    def stageFourFindImportSPU(self, fromPackage, pcache):
        """Find the SPU associated with fromPackage, if it exists and
        is well defined. Cache results in pcache, recording an error
        for the first time a bad package is found."""
        if fromPackage in pcache:
            return pcache[fromPackage]
        spu = FILENAME_SPU.get3(fromPackage)
        if not spu.atLeast(OK3):
            spu = None
            #err = "package '%s' is not well defined" % fromPackage
            self.err(E416InvalidPackageFile(None, fromPackage))
        # ASSUME CurrentPackageSet
        elif spu._currentPackageName != fromPackage:
            #err = "'%s' is not a package, but a file in package '%s'" % (fromPackage, spu._currentPackageName)
            self.err(E417NotCorePackageFile(None, fromPackage, spu._currentPackageName))
            spu = None
        pcache[fromPackage] = spu
        return spu

    def stageFourCalcAllDecls(self, pcache):
        # check that all importall packages are well defined
        # leave the check for import packages to each file
        # TEST ImportallsAtOK3
        
        # calculate allDecls: a dict maping each (non-local) id
        # declared in or imported or importalled into one of the
        # package files to a Decl
        allDecls = {}
        for (idname, declImport) in self.allDeclImports.items():
            self._addDecl(allDecls, pcache, idname, declImport, True)
        for pkg in self.allImportAlls:
            spu = self.stageFourFindImportSPU(pkg, pcache)
            if spu:
                exports = spu.allExports
                #conflicts = setIntersection(exports, allDecls)
                conflicts = ImmutableSet(exports).intersection(allDecls)
                if conflicts:
                    exports = exports.copy()
                    for id in conflicts:
                        declImport = self.allDeclImports.get(id)
                        if declImport is None:
                            # Conflict with another importall
                            # find other package
                            for pkg2 in self.allImportAlls:
                                spu2 = self.stageFourFindImportSPU(pkg2, pcache)
                                if spu2 and id in spu2.allExports:
                                    break
                            self.err(E404ImportallConflict(None, id, pkg, pkg2))
                        elif isinstance(declImport, Decl):
                            # conflict with declaration
                            self.err(E403ImportallDeclConflict(None, id, pkg))
                        elif declImport.id != id or declImport.modname != pkg:
                            # conflict with explicit import
                            self.err(E402ImportallImportConflict(None, id, pkg, declImport))
                        else:
                            # importall of an explicitly imported id
                            # Don't warn for the now
                            #self.err(W410ImportImportall(None, id, pkg))
                            pass
                        del exports[id]
                allDecls.update(exports)
        return allDecls

    def _addDecl(self, decls, pcache, idname, declImport, inside):
        if isSymbol(declImport):
            pkg = declImport.modname
            spu = self.stageFourFindImportSPU(pkg, pcache)
            if spu:
                decl = spu.allExports.get(declImport.id)
                if not decl:
                    if inside:
                        self.err(E405ImportUnexported(None, declImport.id, pkg))
                    else:
                        self.err(W418ImportUnexported(None, declImport.id, pkg))
                    return None
            else:
                return None
        else:
            decl = declImport
        decls[idname] = decl
        return decl
            

    def stageFourProcess(self):
        """Validate SPU w.r.t. everything it imports"""
        # This depends upon:
        #   self (stage 2)
        #   package (stage 3)
        #   packages imported by package and used here (stage 3)
        # For every symbol used:
        #   If imported, ensure you are allowed to import it (otherwise F4)
        #   If declaration available, check usages (otherwise F4)
        #   If not available, record usages (and warn/F4)
        
        
        # get relevant declaration
        if not self.atLeast(OK3):
            return
        # TODO: should remove any F4 errors
        self.errorLevel = PROCESSING4
        
        package = self._currentPackageName
        pcache = {}
        if package == self.filename:
            pspu = self
            # for package core file merge the information from the other files
            self.allDecls = self.stageFourCalcAllDecls(pcache)
        else:
            # for non-core file, get the core spu
            pspu = FILENAME_SPU.get4(package)
            if not pspu.atLeast(OK4):
                self.err(E401BadCoreFile(None, package))
            else:
                self.allDecls = None
        # Set self.decls to all decls used in self, but not included
        # in pspu.allDecls
        insidePackage = (self.filename in pspu.allFiles)
        if self.atLeast(PROCESSING4):
            decls = {}
            if insidePackage:
                #inside - only need local decls and imports
                for (idname, declImport) in self._declImport.items():
                    if idname.startswith(LOCAL_ID_PREFIX):
                        self._addDecl(decls, pcache, idname, declImport, True)
            else:
                # outside
                for (idname, declImport) in self._declImport.items():
                    oldDecl = pspu.allDecls.get(idname)
                    newDecl = self._addDecl(decls, pcache, idname, declImport, False)
                    if oldDecl and oldDecl != newDecl:
                        if isSymbol(declImport):
                            self.err(E406ImportConflict(None, idname, package))
                        else:
                            self.err(E407DeclConflict(None, idname, package))
            self.decls = decls
        # Exit if errors
        if not self.atLeast(PROCESSING4):
            printErrors(self, True)
            return
        # Check that usages are valid, adding the declaration of each
        # symbol used to (self.)decls, or if no declaration can be found, add
        # a list of exprs that use the symbol.
        for expr in self._exprs:
            expr.checkUsages(self, pspu)
        # Note - at this point decls will also contains a
        # list of exprs for any id that is not declared.
        for (idname, declExprs) in decls.items():
            if isinstance(declExprs, list):
                if declExprs:
                    expr = declExprs[0]
                else:
                    expr = None
                num = len(declExprs)
                if insidePackage:
                    self.err(E409IdMissing(expr, idname, package, num))
                else:
                    self.err(W408IdMissing(expr, idname, package, num))
        # Exit if some error
        if not self.atLeast(PROCESSING4):
            printErrors(self, True)
            return
        # TEST DeclaredBeforeUse4
        for idname in self.undeclaredLoadUse:
            decl = self.stageFourDecl(idname, None, pspu)
            if decl:
                if decl.asSymbol().modname == package:
                    id = decl.asSymbol().id
                    if self.filename == package:
                        self.err(E412LoadUseNoDeclCore(None, id, package))
                    elif insidePackage:
                        self.err(E411LoadUseNoDecl(None, id, package))
                    else:
                        self.err(W413LoadUseNoDecl(None, id, package))
                # else: Decl in is another package - sort out at load time
            # else: No Decl - there would already be an error/warning

        if self.atLeast(PROCESSING4):
            self.errorLevel = OK4
        printErrors(self, True)         # print any warnings

    def prePostFiles(self):
        """Files required to be loaded before and before-or-after this file"""
        # ASSUME OK4
        pre = []
        # Add the package
        # ASSUME CurrentPackageSet
        cp = self._currentPackageName
        if self.filename != cp:
            pre = [cp]
        else:
            pre = []
        # Any file declaring something used at load time should be
        # loaded before
        if self.undeclaredLoadUse:
            pspu = FILENAME_SPU.get3(cp)
            for idname in self.undeclaredLoadUse:
                # find the file/package where idname is declared
                decl = self.stageFourDecl(idname, None, pspu)
                if decl is None:
                    raise Exception("File %s uses totally unknown id '%s' at load time"%(self.filename, idname))
                # assume that this was declared in the imported package
                p = decl.asSymbol().modname
                if p == cp:
                    # Required identifier idname is in the same
                    # package, but not defined in the package
                    # file. The only time this is allowed (according
                    # to DeclaredBeforeUse4) is if self is not inside
                    # the package. Make sure the entire package is
                    # loaded first.
                    if self.filename in pspu.allFiles:
                        # This should already be picked by DeclaredBeforeUse4 test
                        raise Exception("This violates assumption DeclaredBeforeUse4 file '%s' id '%s'"%(self.filename, idname))
                    for f in pspu.allFiles:
                        pre.append(f)
                elif p not in pre:
                    pre.append(p)
        # Add the specials and needed
        for f in self.specials:
            if f not in pre:
                pre.append(f)
        post = [f for f in self.needed if f not in pre]
        return (pre, post)

    ################################################################
    # Methods that can be called in stageOne processing (other than errors)

    def setExport(self, expr, idStr):
        if idStr in self._exports:
            if idStr:
                self.err(W108DuplicateExport(expr, idStr))
            else:
                self.err(W109DuplicateExportall(expr))
        elif idStr and idStr.startswith(LOCAL_ID_PREFIX):
            self.err(E110ExportLocal(expr, idStr))
        else:
            self._exports.add(idStr)

    def setSpecial(self, expr, package):
        self.specials.add(package)

    def setImportOne(self, expr, idname, package, fromId):
        sym = Symbol(package + "." + fromId)
        if package not in self.specials:
            self.needed.add(package)
            decl = None
        else:
            # get SPU of package if special
            packageSPU = self._validatePackageOrError(expr, package)
            # get exported declaration from package SPU if we have it
            decl = packageSPU and packageSPU.idFindDeclSym(fromId, True)
            if packageSPU and not decl:
                self.err(E111ImportUnexported(expr, fromId, package))
            # TEST SpecialImportRestrictions
            if decl and isSymbol(decl):
                self.err(E112ImportDeclUnavailable(expr, fromId, package))
        oldDeclSym = self.idFindDeclSym(idname, False)
        if oldDeclSym != decl \
           and self._alreadyKnownError(oldDeclSym, idname, sym, expr):
            return
        self._declImport[idname] = sym
        # Make sure we see this decl or symbol when resolving
        self.setCacheId(idname, decl or sym)

    def _alreadyKnownError(self, oldDeclSym, idname, sym, expr):
        if oldDeclSym is None:
            return False
        elif isinstance(oldDeclSym, Decl):
            # decl or different special import
            p = oldDeclSym.asSymbol().modname
            if p == self._currentPackageName or p == self.filename:
                # Declaration from self or package core file
                self.err(E113AlreadyDeclared(expr, idname))
            else:
                # special import
                # VIOLATED DontOverrideSpecialImport (for import)
                self.err(E113AlreadyDeclared(expr, idname)) # , oldDeclSym
        else: # isSymbol(oldDeclSym)
            # a non-special import
            if oldDeclSym != sym:
                self.err(E115AlreadyImported(expr, idname, oldDeclSym))
            else:
                # could warn about special import overriding old
                # import or duplicate import
                return False
        return True

    def setDecl(self, expr, idname, modeStrings, sigkeys=None, keysRequired=None, \
                imp=None, combiner=None):
        oldDeclSym = self.idFindDeclSym(idname, False)
        if self._alreadyKnownError(oldDeclSym, idname, None, expr):
            return
        sym = self.findCacheId(idname, True) # generate a symbol
        decl = Decl(sym, modeStrings, sigkeys, keysRequired, imp, combiner)
        self._declImport[idname] = decl
        self.setCacheId(idname, decl) # so cache points to Decl not symbol

    def setImportAll(self, expr, package):
        package = intern(str(package))
        if package in self.specials:
            pspu = self._validatePackageOrError(expr, package)
            if pspu:
                self._importalls.add(package)
        else:
            self.needed.add(package)
            self._importalls.add(package)


    def _validatePackageOrError(self, expr, package):
        """Ensure that package is atLeast(OK1) and return the SPU.
        Otherwise, record and Error and return None"""
        fileSPU = FILENAME_SPU.get(package)
        if not fileSPU.atLeast(OK1):
            self.err(E116InvalidPackageFile(expr, package))
            return None
        filePackage = fileSPU._currentPackageName
        if filePackage != package:
            self.err(E117NotCorePackageFile(expr, package, filePackage))
            return None
        else:
            return fileSPU

    def setConstantDecl(self, expr, idname):
        """Declaration of an identifier that is only used as a constant."""
        self.setDecl(expr, idname, [" ="]) # bogus mode to avoid errors

    def setPackage(self, expr, pnameStr):
        cp = self._currentPackageName
        # TODO: we could test that this is the first expr in the SPU
        # and then remove BUILTIN_PACKAGE_NAME from specials and
        # _importalls.
        if cp:
            # Package set - do not change package
            if pnameStr != cp:
                self.err(E118ChangePackage(expr, pnameStr))
        elif pnameStr != self.filename:
            # Package not previously set - set the package
            self._currentPackageName = pnameStr
            self._validatePackageOrError(expr, pnameStr)
            # TODO: If validation fails we may as well quite here
        else:
            self._currentPackageName = pnameStr
            

    def setRequires(self, expr, fileString):
        self.needed.add(fileString)

    def setMain(self, expr, actionId):
        # TODO: Eventually convert main: to an ordinary predicate
        self.main_name = str(actionId)

#     ################################################################
#     # Stage 2 processing

#     def stageTwoProcess(self):
#         if not ( S_DECL_PROCESSABLE <= self._processed): raise AssertionError
#         if self._processed >= S_SEMANTICS_PROCESSABLE:
#             return True
#         elif self._processed >= S_SEMANTICS_PROCESSING:
#             return False
#         #Testing Script. Begin:
# #        global chronometers
# #        chronometers["stageTwoProcess"].start()
#         #Testing Script. End.        
#         #self._cache.clear()
#         self._processed = S_SEMANTICS_PROCESSING
#         context = Context(self, None, None)
#         for expr in self._exprs:
#             freevars = context.validate(expr, EMPTY_SET, LOADTIME, PRED_UPDATE)
#             #print expr.annotated()
#             # TODO: what to do with freevars
#         if printErrors(self):
#             self._processed = S_SEMANTICS_UNPROCESSABLE
#             #Testing Script. Begin:
# #            chronometers["stageTwoProcess"].stop()
#             #Testing Script. End.   
#             return False
#         elif self.errors:
#             self._processed = S_SEMANTICS_PROCESSABLE
#         else:
#             self._processed = S_SEMANTICS_CLEAN
#         SPU_RECORD.install(self)
#         #Testing Script. Begin:
# #        chronometers["stageTwoProcess"].stop()
#         #Testing Script. End.   
#         return True

    ################################################################

    def generateSymbol(self, id):
        if id.startswith(LOCAL_ID_PREFIX):
            prefix = self.filename or ""
        else:
            prefix = self._currentPackageName or self.filename or ""
        return Symbol(prefix + "." + id)

    def findCacheId(self, id, generate):
        """Look in the cache or call idFindDeclSym on the SPU to see if we
        have a decl or symbol. If not found and generate is true, then
        construct an appropriate local symbol. If you don't find or
        generate anything, return None, otherwise make sure it is in
        the cache."""
        cached = self._cache.get(id)
        if cached:
            return cached
        found = self.idFindDeclSym(id, False)
        if not found and generate:
            found = self.generateSymbol(id)
        if found:
            self._cache[id] = found
        return found

    def setCacheId(self, id, decl):
        """Set the cached declSym for id to decl.  Useful for setting
        a Symbol cache entry to a Decl cache entry once an id is
        declared and also for special imports of individual ids and"""
        old = self._cache.get(id)
        if old == decl:
            pass
        elif isinstance(old, Decl):
            raise AssertionError, "Cannot reset a Decl cache entry"
        else:
            self._cache[id] = decl
            
    
    def idFindDeclSym(self, id, exportedOnly):
        """For an id, X in this SPU F with package P
        If previously:
         declared in this SPU return Decl for F.X or P.X.
         special import(all)ed in this SPU return Decl.
         special import(all)ed in the package SPU return Decl.
         explicitly imported from I.X in the package SPU return I.X.
         explicitly imported from I.X in this SPU return I.X.
        Else return None."""
        id = str(id)
        declsym = self._declImport.get(id)
        if isSymbol(declsym):
            # explicitly imported, replace with Decl or Symbol from
            # _cache if an entry exists
            declsym = self._cache.get(id) or declsym
        if exportedOnly and not id in self._exports:
            # NOTE: This assumes that self has done stageOneFinish()
            return None
        if declsym:
            return declsym
        if id.startswith(LOCAL_ID_PREFIX):
            return None              # we will never importall a _x id
        for impall in self._importalls:
            if impall in self.specials:
                declsym = FILENAME_SPU.get(impall).idFindDeclSym(id, True)
                if declsym:
                    return declsym
        # Look in parent if there is one
        package = self._currentPackageName
        if package and package != self.filename:
            packageSPU = FILENAME_SPU.get(package)
            if not packageSPU.atLeast(OK2):
                raise LowError("package file %s is not available"%package)
            return FILENAME_SPU.get(package).idFindDeclSym(id, False)
        else:
            return None
        
    


    def getSPU(self):
        return self

    def get_modpath(self):   # for compatability, should be deprecated
        return Symbol(self.filename)

class TextSPU(SPU):
    __stateslots__ = (
        "_text",
        )
    __slots__ = __stateslots__

    def __getstate__(self):
        state = SPU.__getstate__(self)
        state.append(self._text)
        return state

    def __setstate__(self, state):
        self._text = state.pop()
        SPU.__setstate__(self, state)

    def getText(self):
        return self._text
    
    def textUpdate(self, err, text):
        self._text = text
        exprs = None
        if not err:
            #Testing Script. Begin:
    #        #global chronometers
    #        #chronometers["stageZeroProcess"].start()
            #Testing Script. End.
            from spark.internal.parse.sparkl_parser import parseSPARKL
            try:
                exprs = parseSPARKL(self._text, self.sourceName(), EXPR_CONSTRUCTOR)
            except AnyException, e:
                errid = NEWPM.recordError()
                err = E001ParseError(None, "[%d] %s"%(errid, e))
                exprs = None
            #Testing Script. Begin:
    #        #chronometers["stageZeroProcess"].stop()
            #Testing Script. End.   
        return self.update(err, exprs)

    def exprLocation(self, expr):
        from spark.internal.exception import find_line, expandtabs
        (linenum, charnum, line) = find_line(self._text, expr.start)
        (offset, modline) = expandtabs(charnum, line)
        return "%3d|%s>>>%s"%(linenum+1, modline[:offset], modline[offset:])

    def sourceName(self):
        return str(self)

# def countFatalErrors(errorList):
#     "Return a count of the number of fatal errors"
#     fatalcount = 0
#     for err in errorList:
#         if isinstance(err, ErrorResultF):
#             fatalcount += 1
#     return fatalcount

def printError(obj, error, file=None):
    expr = error.getExpr(obj)
    print >> file, error.getErrString()
    if expr != None:
        print >> file, obj.exprLocation(expr)
    

def printErrors(obj, ifWarning=False, file=None):
    """If there are fatal errors (or warnings if ifWarning is True)
    print them and return the number of fatal errors.
    Obj is an object with .errors attribute and
    .sourceName() and .exprLocation(expr) methods."""
#     if hasattr(obj, "printed"):
#         print "Already printed", obj
#     else:
#         obj.printed = True
    fatalcount = 0
    for err in obj.errors:
        if err.level is not None:
            fatalcount += 1
    if obj.errors and (fatalcount or ifWarning):
        errors = list(obj.errors)
        warncount = len(errors) - fatalcount
        print >> file, "##### %s - %s %s"%(obj.sourceName(),\
                                 plural(fatalcount, "", "1 ERROR", "ERRORS"), \
                                 plural(warncount, "", "1 WARNING", "WARNINGS"))
        errors.sort()
        for error in errors:
            printError(obj, error, file)
    return fatalcount
        
        
        
class FileSPU(TextSPU):
    __stateslots__ = (
        "_hash",                  # hash of stage one & two processing
        "_required_hashs",           #  dict mapping filename to _hash
        )
    __slots__ = __stateslots__    
    def __str__(self):
        return "FILE:%s"%self.filename
    def __repr__(self):
        return "<%s>"%self.__str__()

    def fileUpdate(self, err):
        if err:
            return self.textUpdate(err, None)
        else:
            # get latest info
            info = getInfoCache().getInfo(FileInfo, self.filename, True)
            if info.errorMsg:
                err = E002FileError(None, info.errorMsg)
                return self.textUpdate(err, None)
            else:
                return self.textUpdate(None, info.text)
        
    def textChanged(self):
        info = getInfoCache().getInfo(FileInfo, self.filename, True)
        return self.getText() != info.text



    def checkRequiredHashs(self):
        for filename, hashval in self._required_hashs.items():
            if FILENAME_SPU.get(filename)._hash != hashval:
                print ".csp file for %s relies on another version of %s"%(self.filename, filename)
                del self.errors[:]
                self.errorLevel = OK0
                return

def writeToCSP(spu):
        if not spu.atLeast(OK1):
            return
        spu._required_hashs = None
        spu._hash = None
        print "Saving .csp file for", spu.filename, "...", 
        pickled = common_pickle.dumps(spu, -1)
        spu._hash = md5.new(pickled).hexdigest()
        # set the _required_hashs
        required_hashs = {}
        if spu._currentPackageName != spu.filename:
            pspu = FILENAME_SPU.get(spu._currentPackageName)
            required_hashs[pspu.filename] = pspu._hash
            for s in pspu.specials:
                required_hashs[s] = FILENAME_SPU.get(s)._hash
        for s in spu.specials:
            required_hashs[s] = FILENAME_SPU.get(s)._hash
        spu._required_hashs = required_hashs
        # Find out where to write .csp file
        pfile = getInfoCache().getInfo(PFileInfo, spu.filename, True)
        if pfile.path is None:
            spu.err(W207CannotFindCSP(None))
            print "error"
            return
        # Create the headers:
        text_hash = md5.new(spu._text).hexdigest()
        requires = ["%s/%s"%filehash for filehash in spu._required_hashs.items()]
        requires.sort()
        try:
            cspFile = open(pfile.path, 'wb')
            cspFile.write("#SPARK Cache file - DO NOT EDIT\n")
            cspFile.write("file: %s/%s\n"%(spu.filename, spu._hash))
            cspFile.write("sourcehash: %s\n"%text_hash)
            cspFile.write("requires: %s\n"%(", ".join(requires)))
            cspFile.write(pickled)
            cspFile.write("\n# END OF FILE#\n")
            cspFile.close()
        except:
            errid = NEWPM.displayError()
            spu.err(W2078CannotWriteCSP(None))
        print "done"
  
def readFromCSP(filename):
    """Try to read in SPU from cached .csp file.
    Return None if you can't.
    Set the error level appropriately"""
    fileinfo = getInfoCache().getInfo(FileInfo, filename, True)
    if not fileinfo.text:
        return
    text = fileinfo.text
    pfileinfo = getInfoCache().getInfo(PFileInfo, filename, True)
    if not pfileinfo.text:
        return None
    cspFile = StringIO(pfileinfo.text)
    def readIn(prefix):
        line = cspFile.readline()
        if not line.startswith(prefix):
            print "Error reading csp file, expecting %r found %r"%(prefix, line)
            raise AssertionError
        return line[len(prefix):-1]
    try:
        readIn("#SPARK")
        lineFile = readIn("file: ")
        text_hash1 = readIn("sourcehash: ")
        required = readIn("requires: ")
    except AssertionError:
        return None
    [filename1, hash1] = lineFile.split("/")
    if filename1 != filename:
        print "Incorrect filename"
        return None
    if text_hash1 != md5.new(text).hexdigest():
        print "Source has changed - .csp file out of date for %s"%filename
        return None
    spu = common_pickle.load(cspFile)
    cspFile.close()
    # At this point we can use at least some of the .csp file
    spu._hash = hash1
    required_hashs = {}
    if required:                        # avoid splitting required=''
        for filehash in required.split(", "):
            [filename2, hash2] = filehash.split("/")
            required_hashs[filename2] = hash2
    spu._required_hashs = required_hashs
    return spu
    

class BuiltinFileSPU(FileSPU):
    __slots__ = ()
    def stageOneSetup(self):
        FileSPU.stageOneSetup(self)
        self._importalls = Set()
        self.specials = Set()
        self.setDecl(None, "declare{}", ["1=j:+++++++++"],
                     ["modes:", "keys:", "keysRequired:", "imp:", "combiner:", "properties:", "argnames:", "doc:", "features:"],
                     ["modes:", "imp:"],
                     imp="spark.lang.builtin.DeclareBrace")


class PseudoFileSPU(TextSPU):
    __stateslots__ = (
        "initPackage",
        )
    __slots__ = __stateslots__
    
    def __init__(self, initPackage):
        filename = "#%d"%getNewIdNum()
        self.initPackage = initPackage
        TextSPU.__init__(self, filename)

    def __str__(self):
        return "PSEUDOFILE:%s"%self.filename

    def __repr__(self):
        return "<%s>"%self.__str__()

    def if_OK2_insert_info_FILENAME_SPU(self):
        if self.atLeast(OK0):
            self.stageOneTwoProcess()
            if self.atLeast(OK2):
                FILENAME_SPU.set(self.filename, self)
                return True
        return False

    def getExprs(self):
        return self._exprs

    def stageOneSetup(self):
        TextSPU.stageOneSetup(self)
        if self.initPackage:
            self.setPackage(None, self.initPackage)



class StringSPU(TextSPU):
    __stateslots__ = (
        "initPackage",
        )
    __slots__ = __stateslots__
    
    def __init__(self, initPackage):
        filename = "#%d"%getNewIdNum()
        self.initPackage = initPackage
        TextSPU.__init__(self, filename)

    def stageOneSetup(self):
        TextSPU.stageOneSetup(self)
        if self.initPackage:
            self.setPackage(None, self.initPackage)

    def __str__(self):
        return "<string>"

    def process(self, usage):
        """Process single expr according to usage.
        Return free variables if no fatal errors occurred."""
        if not self.atLeast(OK0):
            return None
        if len(self._exprs) == 1:
            #Testing Script. Begin:
    #        global chronometers
    #        chronometers["stageOneTwoProcess"].start()
            #Testing Script. End.        
            self.errorLevel = PROCESSING2
            self.stageOneSetup()
            context = Context(self, None, None)
            expr = self._exprs[0]
            freevars = expr.validate(context, EMPTY_SET, LOADTIME, usage)
            #Testing Script. Begin:
    #        chronometers["stageOneTwoProcess"].stop()
            #Testing Script. End.
            if self.atLeast(PROCESSING2):
                self.errorLevel = OK2
                return freevars
        elif len(self._exprs) == 0:
            self.err(E003NoTerms(None))
        else:
            self.err(E004MultipleTerms(None))
        return None

# The following is replaced by self[0]
#     def getExpr(self):
#         return self._exprs[0]

################################################################



def setBootstrap():
    pass


################################################################
################
####
#
# Contexts
#
# Temporary object to handle validation of exprs.
# Records where variables are used
class Context(object):
    __slots__ = (
        "_obj",
        "spu",
        "_parent",
        "_varScope", # dict mapping variable to occurrence count or obj
        )

    def __init__(self, spu, obj, parentContext):
        self._obj = obj
        self._parent = parentContext
        self.spu = spu
        self._varScope = {}             # map var to list of usages and scope

    subContextClass = None     # use same class when making subContext

    def subContext(self, obj):
        cls = (self.subContextClass or self.__class__)
        return cls(self.spu, obj, self)

    def setVarScope(self, var, obj):
        # If var is local to this context, then 
        #print "setVarScope%r"%((var, obj),)
        if var.outerVersion() is None:
            self._varScope[var].append(obj)

    def recordVarUsage(self, obj, var):
        #print "recordVarUsage%r"%((obj, var),)
        outervar = var.outerVersion()
        if outervar is None:            # local to this context
            varScope = self._varScope.get(var)
            if varScope is None:
                varScope = []
                self._varScope[var] = varScope
            varScope.append(obj)
        elif self._parent is None:
            self.spu.err(E203NotEnoughOuterContexts(expr))
        else:
            self._parent.recordVarUsage(obj, outervar)


    def checkVarUsages(self):
        for var, varScope in self._varScope.items():
            scope = None
            count = 0
            for index, expr in enumerate(varScope):
                if isinstance(expr, ExprVariable):
                    count = count + 1
                    if scope:
                        self.spu.err(E204VarUsedOutsideItsScope(expr))
                        self.spu.err(E205VarUsedOutsideThisScope(scope, var))
                        return
                elif not scope:
                    scope = expr
                    if str(var).startswith("$_"):
                        if count > 1:           # more than one use before scope
                            self.spu.err(W206VarMultiple(varScope[1], var))
                    else:
                        if count <= 1:         # only one use before scope
                            pass # removed for Pauline - DNM
                            #self.recordError(WARN, varScope[0], "Variable %s appears only once"%var)


#     def recordResult(self, obj, vbbefore, activity, freevars):
#         #depth = obj.getDepth()
#         #print "%s%s/%s/%s %s"%("."*depth, obj.usage, obj.functor or "-", str(obj.impKey), obj)
#         #print "INFO: usage %s, vbbefore %s, activity %s, freevars %s: %s"%(structure.usage, vbbefore, activity, freevars, structure.annotated())
#         pass

################################################################

# Interface for source objects


################################################################

################################################################

_default_module = None

def set_default_module(m):
    if not (m is None or isinstance(m, SPU)): raise AssertionError
    global _default_module
    if m is None:
        print "Not changing default module"
    elif m != _default_module:
        print "Setting the default module to", m.get_modpath().name
        _default_module = m

def get_default_module():
    return _default_module

# def modpath_is_installed(modpath):
#     spu = FILENAME_SPU.get(str(modpath))
#     return spu.atLeast(OK3)

def ensure_modpath_installed(modpath):
    spu = FILENAME_SPU.get4(str(modpath))
    return spu.atLeast(OK4)
#     spu = NAMESPACES.processFile(str(modpath))
#     return spu

def drop_modpath(modpath):
    raise Unimplemented()

def clear_all_modules():
    SPU_RECORD.clear()
    FILENAME_SPU.clear()
    setBootstrap()

def moduleNamed(namestring):
    raise Unimplemented()

def moduleNamedInverse(module):
    raise Unimplemented()

def init_builtin():
    setBootstrap()


# def load_file_into_agent(file, agent):
#     spu = NAMESPACES.processFile(file, S_SEMANTICS_PROCESSABLE)
#     if not spu:
#         return False
#     groups = computeCycles(file, lambda f:NAMESPACES.spus[f].dependsOnList())
#     #print "groups=", groups
#     def loadFile(file, neededBy):
#         """Load file if it is not already installed.
#         Print an error message if you could not.
#         Return whether the file is now loaded."""
#         #print "Looking to load", file, "loadedFileEvents=", agent.loadedFileEvents
#         #if file in agent.loadedFileEvents:
#         if agent.fileLoaded(file):
#             return True
#         spu = NAMESPACES.processFile(file)
#         if not spu:
#             return False            # message printed by processFile is enough
#         # Find circularly-dependent group that file is in
#         group = groups.get(file) or (file,)
#         # Check all files in group can be processed
#         groupSpus = []
#         for groupFile in group:
#             groupSpu = NAMESPACES.processFile(groupFile)
#             if not groupSpu:
#                 if groupFile != file:
#                     print "Could not install %s%s because the circulary-dependent file %s had errors"%(file, neededBy, groupFile)
#                 else:
#                     print "Could not install %s%s because it had errors"%(file, neededBy, groupFile)
#                 return False
#             groupSpus.append(groupSpu)
#         # Check dependencies files in a circularly dependent group
#         failed = None
#         for groupSpu in groupSpus:
#             if groupSpu == spu:
#                 nb = " needed by %s"%file
#             else:
#                 nb = " needed by %s through %s"%(file, groupSpu.filename)
#             for f in groupSpu.dependsOnList():
#                 if f not in group and not loadFile(f, nb):
#                     failed = f
#         if failed:
#             print "Could not install file %s%s because %s could not be installed"%(file, neededBy, failed)
#             return False
#         # install the group together
#         print "INSTALLING FILE %s%s"%(file, neededBy)
#         printErrors(spu, True)
#         try:
#             success = load_decls_into_agent(spu, agent)
#         except LocatedError, e:
#             errid = NEWPM.displayError()
#             print "ERROR LOADING DECLS INTO AGENT FOR FILE %s%s"%(file, neededBy)
#             return False
#         if not success:
#             print "FAILED LOADING DECLS INTO AGENT FOR FILE %s%s"%(file, neededBy)
#             return False
#         for groupSpu in groupSpus:
#             if groupSpu != spu:
#                 print "INSTALLING FILE %s circularly-dependent on %s"%(groupSpu.filename, file)
#                 if not load_decls_into_agent(groupSpu, agent):
#                     return False
#                 printErrors(groupSpu, True)
#         for groupSpu in groupSpus:
#             if not load_facts_into_agent(groupSpu, agent):
#                 return False
#             from spark.internal.init import is_persist_state
#             if is_persist_state():
#                 persist_report_load_modpath(agent, groupSpu.filename)
#         return True
#     return loadFile(file, "")


def load_file_into_agent(rootfile, agent):
    "Return whether successful"

    # Determine the files needed to load rootfile (in order)
    seq = []                            # files to load in order
    set = Set(seq)                      # files loaded, bad, or in seq
    waiting = {} # map each file (not in set) to a set containing (at
                 # least) all files that need to be loaded before
                 # this file that are not also in set.
    errors = []

    def add(file, fromFile):
        if file not in waiting and file not in set:
            spu = FILENAME_SPU.get4(file)
            if not spu.atLeast(OK4):    # bad
                if fromFile == None:
                    msg = "Invalid file '%s' cannot be loaded"%file
                else:
                    msg = "Invalid file '%s' used by '%s'"%(file, fromFile)
                errors.append(msg)
                set.add(file)
            elif agent.fileLoaded(file): # loaded
                set.add(file)
            else:
                (pre, post) = spu.prePostFiles()
                prior = Set(pre)
                waiting[file] = prior
                for f in prior:
                    add(f, file)
                for f in post:
                    add(f, file)
    add(rootfile, None)

    # Move files from waiting to seq if they have no remaining priors
    added = Set()
    while waiting:
        added.clear()
        for (file, prior) in waiting.items():
            # remove all elements of prior that are in set
            prior.difference_update(set)
            if not prior:
                seq.append(file)
                set.add(file)
                added.add(file)
        for file in added:
            del waiting[file]
        if not added:                   # circular dependencies remain
            for (file, prior) in waiting.items():
                x = " & ".join(prior)
                errors.append("Cannot load '%s', need to load %s first"%(file,x))
                waiting.clear()

    # TODO: check that for every file in seq outside a package: every
    # undeclaredLoadUse is already defined in agent, every missing id
    # is already defined in agent or in one of the other files to
    # load, and that every use of a missing id matches the
    # declaration.

    if errors:
        print "ERROR LOADING", rootfile
        for err in errors:
            print " ", err
        return False
    #print "FOR LOADING %s: %s"%(rootfile, ", ".join(seq))
    
    #TODO: See if we can keep the declarations and facts of a file
    #being asserted together

    # The declarations need to be loaded before the facts so that we
    # can get the right cue symbol name for a procedure for a symbol
    # foo declared/imported by another file
    spus = [FILENAME_SPU.get(filename) for filename in seq]
    try:
        for spu in spus:
            filename = spu.filename
            SPU_RECORD.install(spu)
            print "LOADING DECLARATIONS FOR", spu
            if not load_decls_into_agent(spu, agent):
                print "FAILED LOADING FILE %s INTO AGENT"%filename
                return False
            from spark.internal.init import is_persist_state
            if is_persist_state():
                persist_report_load_modpath(agent, filename)
        for spu in spus:
            filename = spu.filename
            print "LOADING FACTS FOR", spu
            if not load_facts_into_agent(spu, agent):
                print "FAILED LOADING FILE %s INTO AGENT"%filename
                return False
    except LocatedError, e:
        errid = NEWPM.displayError()
        print "ERROR LOADING FILE %s INTO AGENT"%filename
        return False
    return True

BRACE_FACT_FUNCTORS = (Symbol("defprocedure{}"), Symbol("defadvice{}"))

def toBeAssertedWithDecls(expr):
    "Should this expr be asserted with the decls in the first pass?"
    return isinstance(expr, ExprStructureBrace) \
           and expr.functor not in BRACE_FACT_FUNCTORS

def load_decls_into_agent(spu, agent):
    events = agent._events
    if (events): raise AssertionError, \
       "Events list is not empty before loading decls %s:\n%s"%(spu, events)
    if (agent.fileLoaded(spu.filename)): raise AssertionError, \
       "File has already been loaded, at least partially %s"%spu
    for (id, declsym) in spu._declImport.items():
        if isinstance(declsym, Decl):
            agent.addDecl(declsym)
        else:
            asSym = spu.generateSymbol(id)
            #print "  adding import", asSym, "=", declsym
            agent.addImport(asSym, declsym)
    for impall in spu._importalls:
        if impall not in spu.specials: # impKeys for specials always 
            fromSPU = FILENAME_SPU.get(impall) # assume OK3
            for (id,decl) in fromSPU.allExports.items():
                asSym = spu.generateSymbol(id)
                # ASSUME AllExportsHaveDecls
                # Keep this indirect (i.e., via fromSym) to aid relinking
                fromSym = decl.asSymbol()
                #print "  adding", asSym, "=", fromSym, "through importall"
                agent.addImport(asSym, fromSym)
    bindings = SPUBindings(agent, spu)
    for expr in spu._exprs:
        if toBeAssertedWithDecls(expr):
            if is_resuming():
                # Only assert the implementation
                imp = bindings.bImp(agent, expr)
                #print "Setting imp for expr", expr, imp
                if hasattr(imp, 'concludeImp'):
                    imp.concludeImp(agent, bindings, expr)
            else:
                #print "asserting", expr
                predUpdate(agent, bindings, expr)
    #agent.loadedFileEvents[spu.filename] = tuple(events)
    (asserted, retracted) = factChanges(agent, events)
    agent.addfact(P_LoadedFileFacts, (spu.filename, asserted, retracted))
    del events[:]
    return True

def factChanges(agent, events):
    from spark.pylang.defaultimp import AddFactEvent, RemoveFactEvent
    asserted = List([e.getStructure(agent) for e in events \
                     if isinstance(e, AddFactEvent)])
    retracted = List([e.getStructure(agent) for e in events \
                      if isinstance(e, RemoveFactEvent)])
    return (asserted, retracted)

def load_facts_into_agent(spu, agent):
    events = agent._events
    if (events): raise AssertionError, \
       "Events list is not empty before loading facts %s:\n%s"%(spu, events)
    bindings = SPUBindings(agent, spu)
    for expr in spu._exprs:
        if not toBeAssertedWithDecls(expr):
            predUpdate(agent, bindings, expr)
    #agent.loadedFileEvents[spu.filename] += tuple(events)
    oldfact = agent.fileLoaded(spu.filename)
    if not (oldfact): raise AssertionError
    (asserted, retracted) = factChanges(agent, events)
    agent.removefact(P_LoadedFileFacts, oldfact)
    newasserted = oldfact[1] + asserted
    newretracted = oldfact[2] + retracted
    lfffact = (spu.filename, newasserted, newretracted)
    agent.addfact(P_LoadedFileFacts, lfffact)
    del events[:]
    # Write out file of "file load facts" if persisting
    from spark.internal.init import is_persist_state
    if is_persist_state():
        all_facts = newasserted + createList(Structure(P_LoadedFileFacts, lfffact))
        from spark.internal.persist import computeSPUPersistFacts, writeSPUPersistIEFacts
        iefacts = computeSPUPersistFacts(agent, spu, all_facts)
        del events[:]
        writeSPUPersistIEFacts(agent, spu.filename, spu.index, iefacts)
    return True


def unload_SPU_from_agent(spu, agent):
    filename = spu.filename
    #events = agent.loadedFileEvents[filename]
    oldfact = agent.fileLoaded(filename)
    if (agent._events): raise AssertionError, \
       "Events list is not empty before unloading SPU %s"%spu
    for struct in oldfact[1]:           # asserted fact structures
        #print "Retracting", struct
        agent.removefact(struct.functor, struct)
#     from spark.internal.repr.varbindings import ValueZB
#     for event in events:
#         if isinstance(event, AddFactEvent):
#             functor = event.goalsym()
#             args = event.getArgs(agent)
#             imp = agent.getImp(functor)
#             zb = ValueZB(args)
#             print "Retracting", functor, args
#             imp.retractall(agent, zb, zb)
#         else:
#             print "IGNORING EVENT %s"%event
    #if (agent._events): raise AssertionError, \
    #    "Events list is not empty after unloading SPU %s\n%s"%(spu, agent._events)
    #del agent.loadedFileEvents[filename]
    agent.removefact(P_LoadedFileFacts, oldfact)
    lfofact = agent.factslist1(P_LoadedFileObjects, filename)
    agent.removefact(P_LoadedFileObjects, lfofact)
    del agent._events[:]

def agent_reload_all(agent):
    # NOTE: This is *very* simplistic - the only criterion for
    # dropping and reloading a file is "has it's source
    # changed". There is no concept of dependencies between
    # files. Dropping a file consists of retracting the facts that
    # were asserted when loading the file, which may not be
    # enough. Changes in declarations are not handled.
    from spark.internal.engine.agent import Agent
    from spark.internal.common import BUILTIN_PACKAGE_NAME
    if not (isinstance(agent, Agent)): raise AssertionError
    #filenames = tuple(agent.loadedFileEvents)
    facts = agent.factslist0(P_LoadedFileFacts)[:] # ensure we have a copy
    # For all FileSPUs that are not PseudoFileSPUs
    # Unload facts from agent and remove SPU
    if (agent._events): raise AssertionError, \
       "Events list is not empty before reloading files"
    #for filename in filenames:
    print "Checking for source files that have changed since loaded"
    getInfoCache().newTimestamp()  # new timestamp for filesystem checking
    for fact in facts:
        filename = fact[0]
        if filename != BUILTIN_PACKAGE_NAME:
            spu = FILENAME_SPU.get(filename)
            if isinstance(spu, FileSPU) and spu.textChanged():
                print "UNLOADING FILE", filename
                #unload_SPU_from_agent(spu, agent)
                for struct in fact[1]: # asserted fact structures
                    #print "Retracting", struct
                    agent.removefact(struct.functor, struct)
                agent.removefact(P_LoadedFileFacts, fact)
                FILENAME_SPU.delete(filename)
    del agent._events[:]
    _dump_bad_spus()
    # Reprocess all filenames
    for filename in [f[0] for f in facts]:
        if not agent.fileLoaded(filename):
            load_file_into_agent(filename, agent)

def _dump_bad_spus():
    # Remove all spus with errors
    for (filename, spu) in FILENAME_SPU.items():
        if isinstance(spu, FileSPU) and not spu.atLeast(OK2):
            
            print "Eliminating", filename, "which had errors"
    
        
    
################################################################

from spark.internal.repr.varbindings import BindingsInt
class ExprBindings(ConstructibleValue, BindingsInt):
    __slots__ = ()


class StandardExprBindings(ExprBindings):
    __slots__ = (
        "_variables",            # var -> value, varname -> constraint
        )
    def __init__(self):
        ExprBindings.__init__(self)
        self._variables = {}

    def setVariables(self, dict):
        if (self._variables): raise AssertionError
        self._variables.update(dict)

    ################
    # ConstructibleValue methods
    
    # def constructor_args(self): [] # use default
    def state_args(self):
        return (tuple(self._variables.items()),)
    def set_state(self, agent, items):
        self.setVariables(dict(items))

    ################
    # term methods
    def bTermEval(self, agent, expr):
        imp = agent.getImp(expr.impKey)
        try:
            result = imp.call(agent, self, expr)
            if result is None:
                raise LocatedError(expr, "Implementation returned None")
            return result
        except NotLocatedError, e:
            errid = NEWPM.recordError()
            raise CapturedError(expr, errid, "evaluating")
        
    def bTermEvalP(self, agent, expr):
        return expr.usage == TERM_EVAL or \
               (isinstance(expr, ExprLocalVariable) and self.uniquelyConstrained(expr._value))

    def bTermMatch(self, agent, expr, value):
        imp = agent.getImp(expr.impKey)
        try:
            if expr.usage == TERM_EVAL:
                return imp.call(agent, self, expr) == value
            else:
                return imp.match_inverse(agent, self, expr, value)
        except NotLocatedError, e:
            errid = NEWPM.recordError()
            raise CapturedError(expr, errid, "matching")

    def bQuotedEval(self, agent, expr):
        imp = agent.getImp(expr.impKey)
        return imp.quotedEval(agent, self, expr)

    def bQuotedMatch(self, agent, expr, value):
        imp = agent.getImp(expr.impKey)
        return imp.quotedMatch(agent, self, expr, value)
        
    def bEntity(self, agent, expr):
        try:
            return agent.getDecl(expr.resolvedSymbol).asSymbol()
        except LowError, e:
            errid = NEWPM.recordError()
            raise e.error(expr, errid)

    def bImp(self, agent, expr):
        return agent.getImp(expr.impKey)
    

    ################

    def _getSPU(self):                  # UNUSED?
        raise self._exception("_getSPU")

    ################
    # methods used by exprs to deal with variables

    # Ordinary variable bindings are recorded in self._variables using
    # the variable as the key.
    # Constraints on a variable, v, are also recorded in self._variables
    # using the getConstraintKey(v), the string name of v, as the key.
    # Constraints are represented by a tuple (SPARK List):
    # An even-length tuple is of the form
    # (bindings1, zitem1, ... bindingsn, zitemn)
    # and means that the value must be matched against bindings1+zitem1, etc.
    # An odd-length tuple is of the form
    # (value, bindings1, zitem1, ..., bindingsn, zitemn)
    # where value is the value that the variable is constrained to have.

    def getVariableValue(self, agent, variable):
        "Get the value of the variable, assuming it should already be bound"
        try:
            return self._variables[variable]
        except KeyError:
            raise LowError("Variable %s is known to be unbound!"%variable)

    getCapturedValue = getVariableValue

    def getVariableValues(self, agent):
        "Returns all currently bound variable,value pairs - PLUS VARIABLES PREVIOUSLY BOUND BUT CURRENTLY UNBOUND DUE TO FAILURE"
        variables = self._variables
        return [(var, variables[var]) \
                for var in variables\
                if isVariable(var)]

#     def setVariableValue(self, agent, variable, value):
#         self._variables[variable] = value
#         return True

    def matchVariableValue(self, agent, variable, value):
        """Attempt to bind variable to value.
        There may be constraints on the variable, so the bindings may fail.
        Return whether it was successful."""
        constraint = self._variables.get(getConstraintKey(variable))
        if constraint and \
               not matchValueToConstraint(agent, value, constraint, True):
            return False
        self._variables[variable] = value
        return True

    setVariableValue = matchVariableValue # no need for separate method - DNM

    def setConstraint(self, agent, variable, bindings, zitem):
        """Add a constraint to the given variable.
        If the constraint is known to be not satisfiable, return False.
        Otherwise, add the constraint and return True."""
        # Test whether this is a value constraint (i.e., zitem is evaluable)
        value = termEvalOpt(agent, bindings, zitem)
        # Get any existing constraint
        constraintKeyName = getConstraintKey(variable)
        oldConstraint = self._variables.get(constraintKeyName)
        if not oldConstraint:
            # No existing constraint
            if value is None:
                newConstraint = (bindings, zitem)
            else:
                newConstraint = (value,)
        elif oddLength(oldConstraint):
            # There is an existing value constraint
            oldValue = oldConstraint[0]
            if value is None:
                # Not a new value constraint, check it matches existing value
                if termMatch(agent, bindings, zitem, oldValue):
                    # Value satisfies new constraint, so add constraint
                    newConstraint = oldConstraint + (bindings, zitem)
                else:
                    # Value does not satisfy constraint
                    return False
            elif value == oldValue:
                # New value constraint matches old value constraint
                # so we don't need to change anything
                return True
            else:
                # New value constraint doesn't match old value constraint
                return False
        else:
            # No existing value constraint
            if value is None:
                # New constraint not a value, so add it to end
                newConstraint = oldConstraint + (bindings, zitem)
            elif matchValueToConstraint(agent, value, oldConstraints, False):
                # Everything matched new value constraint, add it
                newConstraint = (value,) + oldConstraint
            else:
                # New value constraint doesn't match old constraints
                return False
        # Now set variable constraint and value as necessary
        self._variables[constraintKeyName] = newConstraint
        if value is not None:
            self._variables[variable] = value
        return True
            
    def uniquelyConstrained(self, variable):
        return oddLength(self._variables.get(getConstraintKey(variable), ()))

    def constraintString(self, expr): # For debugging
        if isinstance(expr, ExprLocalVariable):
            variable = expr.asValue()
            constraintList = self._variables.get(getConstraintKey(variable), ())
            if oddLength(constraintList):
                return str(variable) + "=" + value_str(constraintList[0])
            else:
                return str(variable) + ":" + str(constraintList)
        else:
            return str(expr.asValue())

    constructor_mode = ""

installConstructor(StandardExprBindings)

# Function to get the key for the constraint on a variable from the variable
getConstraintKey = str

def oddLength(x):
    "Does x have an odd length?"
    return len(x) % 2

# Function to match a value to a set of constraints
def matchValueToConstraint(agent, value, constraints, testValueConstraint):
    """Match/rematch the value to the given constraints.
    Return whether all matches were successful.
    Optionally test any existing value constraint.
    This can be used to check if a value satisfies the constraints and also
    to rematch the constraints if something may have changed the bindings"""
    index = len(constraints) - 2
    if testValueConstraint and index % 2:
        # We want to check any value constraint and there is one
        if value != constraints[0]:
            return False
    while index >= 0:
        if not termMatch(agent, constraints[index], constraints[index+1], value):
            return False
        index -= 2
    return True


class SPUBindings(StandardExprBindings):
    __slots__ = (
        "_spu",
        )

    def __init__(self, agent, spu):
        #cache = agent.getCache(spu.filename)
        StandardExprBindings.__init__(self)
        if isinstance(spu, int):
            #self._spu = SPU_RECORD.indexToSPU(spu)
            self._spu = binarySearch(SPU_RECORD, spu)
        else:
            self._spu = spu

    def _getSPU(self):                  # UNUSED?
        return self._spu

    def copy(self):
        c = self.__class__(0, self._spu)
        c.setVariables(self._variables)
        return c

    ################
    # ConstructibleValue methods
    
    def constructor_args(self):
        index = self._spu.index
        if not index:
            raise AttributeError, "SPU has not been installed yet"
        return [0, index] # ignore agent, but arg must be persistable
    constructor_mode = "XX"

installConstructor(SPUBindings)




##### 

def getPackageDecls(agent, packagename):
    """Find all the declarations visible in package packagename"""
    spu = FILENAME_SPU.get4(packagename)
    if spu.atLeast(OK4):
        if spu.allDecls is not None:
            return spu.allDecls.values()
        else:
            raise LowError("Error processing package %s - allDecls is None", \
                           packagename)
    else:
        raise LowError("Error processing package %s - errorLevel=%d", \
                       packagename, spu.errorLevel)


################################################################
################
####
#
# Persistence of SPUs
#
# The global variable SPU_RECORD, an instance of SPURecord, keeps
# track of every SPU that may contain declarations and/or exprs that
# may appear in closures. This amounts to all FileSPUs that have
# reached stage 2 processing and specified StringSPU's that are
# successfully .process-ed.
#
# As each SPU is .install-ed into the SPURecord, every Expr that it
# contains is assigned an "index", a unique integer that identifies
# the Expr (this is position of the Expr in a pre-order traversal of
# Exprs within the recorded SPUs). This allows the Exprs to be
# referenced by their indices using the builtin function idExpr (see
# Expr.inverse_eval and idExpr in spark/internal/parse/expr.py and
# SPURecord.getExpr).
#
# If the states of the agents are being persisted, then as each SPU is
# .install-ed into the SPURecord, a pickled version of the SPU is
# saved in the persistence src/ directory with the name
# SPUnnnnn.persist.
#
# When we want to restore the state of the agents, we must first
# restore the NAMESPACES structure and all the old SPUs. The
# SPURecord.restore method reads in all the SPUs from the persistence
# src/ directory, rebuilding the SPURecord and Namespaces objects.

_TOP_INDEX = 1
_MIN_INDEX = _TOP_INDEX + 1

class SPURecord(object):
    __slots__ = (
        "next_index",
        "spus",
        )
    index = _TOP_INDEX
    indexCompound = True
    
    def __init__(self):
        self.next_index = _MIN_INDEX
        self.spus = []

    def clear(self):
        self.next_index = _MIN_INDEX
        self.spus = []
        from spark.internal.init import is_persist_state
        if is_persist_state():
            self.eraseBinFiles()

    def restore(self):
        if not (self.next_index == _MIN_INDEX and not self.spus): raise AssertionError
        spunumber = 0
        while self.existsBinFile(spunumber):
            spu = self.readBinFile(spunumber)
            ispunumber = self._install(spu)
            if not (ispunumber == spunumber): raise AssertionError
            #print "ADDING", ispunumber, spu, spu.filename
            FILENAME_SPU.set(spu.filename, spu)
            spunumber += 1

    def _install(self, spu):
        """Adds SPU to the list of saved SPUs, set the indices of exprs in
        the spu, and return the spunumber."""
        if spu.index: raise AssertionError
        index = setIndex(spu, self.next_index)
        spunumber = len(self.spus)
        self.spus.append(spu)
        self.next_index = index
        return spunumber

    def install(self, spu):
        "Install self into SPU_RECORD if it hasn't already been installed"
        if not spu.index:
            spunumber = self._install(spu)
            from spark.internal.init import is_persist_state
            if is_persist_state():
                self.writeBinFile(spunumber, spu)

    def filename(self, spunumber):
        from spark.internal.persist import get_persist_src_dir
        return os.path.join(get_persist_src_dir(), "SPU%05d.persist"%spunumber)

    def writeBinFile(self, spunumber, spu):
        filename = self.filename(spunumber)
        if not (spu.atLeast(OK2)): raise AssertionError, \
           "File %s is not processable"%filename
        #print "Writing %s %s %s"%(filename, spu, spu._processed)
        binfile = open(filename, "wb")
        s = common_pickle.dumps(spu, -1)
        binfile.write(s)
        binfile.close()

    def readBinFile(self, spunumber):
        filename = self.filename(spunumber)
        #print "Reading %s %s"%(filename, spunumber)
        binfile = open(filename, "rb")
        spu = common_pickle.load(binfile)
        binfile.close()
        return spu

    def eraseBinFiles(self):
        spunumber = 0
        filename = self.filename(spunumber)
        while os.path.exists(filename):
            print "Removing", filename
            os.remove(filename)
            spunumber += 1
            filename = self.filename(spunumber)

    def existsBinFile(self, spunumber):
        filename = self.filename(spunumber)
        return os.path.exists(filename)

#     def getExpr(self, index):
#         return recursiveBinarySearch(self.spus, index)
#         # first find the SPU by binary search
#         spu = binarySearch(self.spus, index)
#         # then find the expr within the SPU
#         expr = binarySearch(spu._exprs, index)
#         while expr.index != index:
#             expr = binarySearch(expr, index)
#         return expr

#     def spuToIndex(self, spu):
#         index = spu.index
#         if not index: raise AssertionError, \
#            "The index of the SPU is not set yet"
#         return index

#     def indexToSPU(self, index):
#         return binarySearch(self.spus, index)

    def __getitem__(self, index):
        return self.spus[index]

    def __len__(self):
        return len(self.spus)

    def __nonzero__(self):
        return True

SPU_RECORD = SPURecord()

################################################################

# Error 

################################################################
"""
Validation:

TODO:

Create stage 3 linkage step:
   3a - consolidate packages, check for duplication
   3b - validate each file against the packages it uses

Create loader (of a 3b file) handle linkage either by adding extra
   entries where something is imported or making the imp table keep
   references A.B.X -> Symbol(C.D.X) and following the chains at run
   time.  Loader must load special imports first and then post other
   imports to todo queue.


We can optimize things a bit if we can sort out USES_KEYWORDS
Decl has no keywords and does not allow them
Decl has keywords
Decl treats keyword arguments as ordinary structures
CUE_LIST_DECL?

LOADING

allexports(P) = union E(x) for x in C(P(F))

load(F):
- for F' in C(P(F)) in order starting with P(F) run(F')
- if F not in C(P(F)) run(F)

run(F):
- ensure special imports/special importalls are loaded
- perform assertions in F:
    decls go in _symbolDI[sym]=DI
    imports symf as sym (check symf.id in allexports(symf.modname))
       if _symbolDI[symf]=DIf then _symbolDI[str(sym)]=DIf
       else _symbolDI[str(sym)]=symf
    importall(P') = import P'.id as P.id for id in allexports(P')
- 

L(F) = L1(F) if F = P(F)
L(F) = L2(F) if F != P(F) and F in C(P)
L1 - filename=packagename
L2 - filename in C=canononical files of package
L3 - filename not in canonical files of package

L1 -> run(F), then Lensure F loaded
Load declaration into _symbolDI sym->decl
Load import  into _symbolDI sym->sym
append importalls into _symbolDI[modnamestring].importalls
append exports into _symbolDI[modnamestring].exports

package -
- compute canonical collection of files
- accumuate 

all exports should be decls

"""

################################################################
"""
ImportallsAtOK3 - (stage 4 test)

 - Each package that has been importall-ed by a file must have reached
   stage OK3

CurrentPackageSet - (stage 1 result)

 - spu._currentPackageName is set to a package name and is not None
 
ExportallsResolved - (stage 1 result)

 - spu.exports no longer contains None, corresponding to an exportall,
   but instead has an explicit enumeration of all exported ids.

LocalsDeclared - (stage 1 test)

 - all the local ids used in a file must be declared in the file.

 
DontOverrideSpecialImport - (stage 1)

 - If something has already been imported as special, a non-special
   import should not override it.

DeclaredBeforeUse1 - (stage 1 test)

 - If something is used *at load time* in a file it must be declared
   before that use.




AllCacheSet - (stage 3 result)

 - Every (non-local) id used in a package file of a package has an
   entry in pspu.allCache. This is:
     a Decl for an id declared in a package file,
     a Decl for a specially imported id (either explicit or implicit),
     a symbol for an explicitly imported id, or
     a package symbol (i.e., modname = package) for other ids.

AllImportAllsSet - (stage 3 result)

 - pspu.allImportAlls is a set of all packages importall-ed by some
   package file in a package.

AllExportsSet - (stage 3 result)

 - pspu.allExports is a set of all ids exported by some package file
   of a package.

AllDeclImportsSet - (stage 3 result)

 - pspu.allDeclImports is a dict mapping any id declared in a package
   file of the package to the declaration and mapping any symbol
   explicitly imported (special or non special) to a symbol with
   modname = from package and id = from id.

ConservativeImportalls - (stage 4 test)

 - Any symbol accessed via importall should be accessed via an
   importall in the file or the package core file.

"""
################################################################
