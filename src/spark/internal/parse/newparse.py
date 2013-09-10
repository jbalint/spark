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

from spark.internal.parse.processing import init_builtin
# from spark.internal.common import PM, DEBUG
# from spark.internal.exception import LowError
# from spark.internal.persist import persist_unit, persist_module

# import os
# import sys

# from spark.internal.source_locator import get_source_locator
# from spark.internal.parse.basicvalues import Symbol, isSymbol
# from spark.internal.repr.common_symbols import BUILTIN_MODPATH
# from spark.internal.repr.newterm import *
# from spark.internal.repr.newkinds import *
# from spark.internal.repr.newbuild import build_expr, HasSymInfo
# from spark.internal.repr.varbindings import NULL_EXPR_BINDINGS
# from spark.internal.repr.expr import Expr
# from spark.internal.repr.predexpr import PredExpr, SimplePredExpr
# from spark.internal.parse.basicvalues import ValueInt, value_str, Structure
# pm = PM(__name__)
# debug = DEBUG(__name__)#.on()

# # def parse(rule, text, info):
# #     P = SPARK(SPARKScanner(text), info)
# #     return wrap_error_reporter(P, rule)

# def parse(rule, text, unit):
#     """internal parse handler. this should not be called externally"""
#     return parseTerms(rule, text, unit)

# def read_file(abspathname, filename):       # test routine
#     module = None
#     file = open(filename, 'rb')
#     text = file.read()
#     file.close()
#     unit = SparklFileUnit(module, Symbol(abspathname), text, filename)
#     return parse("main", text, unit)

# ################################################################
# # Load ID map/counter
# #
# # Each _saved_ SparklUnit object has a unique load id (sequentially
# # increasing) that is used to determine how to resume modules
# # correctly. It is also used in generating IDs for SPARK objects

# # - we don't have to persist/resume this as the persistence layer
# #   implicitly initializes this by fixing the modpath load order
# #   on resume.
# SPARKL_UNITS={}
# MAX_LOADID=-1

# def _save_sparkl_unit(unit, forceLoadid):
#     """if forceLoadid > -1, then it will be used as the loadid instead. Otherwise, a monotonically
#     increasing loadid will be assigned. Returns the loadid assigned to the unit"""
#     global MAX_LOADID
#     if forceLoadid > -1:
#         SPARKL_UNITS[forceLoadid] = unit
#         if forceLoadid > MAX_LOADID:
#             MAX_LOADID = forceLoadid
#         return forceLoadid
#     else:
#         MAX_LOADID += 1
#         SPARKL_UNITS[MAX_LOADID] = unit
#         return MAX_LOADID

# def fromIdGetUnit(id):
#     return SPARKL_UNITS[id]

# ################################################################
# # Sparkl Unit object
# #
# # Represents a file or other unit of SPARK-L text source 

# class SparklUnit(object):
#     __slots__ = (
#         "_module",
#         "_externals",           # list of used modules and imports
#         "_includes",            # list of included filepaths
#         "_filepath",            # absolute path of the file
#         "_text",                # text of file
#         "_exprs",               # exprs of file (includes syminfos)
#         "_syminfos",            # dict: idname -> syminfo
#         "_export_pathexprs",    # list of pathexprs
#         "_export_dict",         # dict: idname -> syminfo
#         # the id of unit: this is not necessarily unique (can reload a unit)
#         "unitid",
#         # order in which this unit was loaded (unique per _saved_ SparklUnit object)        
#         "loadid",               
#         "_nextExprId",
#         "_processedExprs", # like _exprs but includes processed closures
#        )

#     def __init__(self, module, filepath, text, unitid, saveSparklUnit, forceLoadid=-1):
#         if not (isinstance(module, Module)): raise AssertionError
#         if not (isSymbol(filepath)): raise AssertionError
#         self._module = module
#         self._externals = []
#         self._includes = []
#         self._text = text
#         self._exprs = []
#         self._filepath = filepath
#         self._syminfos = {}
#         self._export_pathexprs = []
#         self.unitid = unitid
#         self._nextExprId = 1
#         self._processedExprs = []
#         if saveSparklUnit:
#             self.loadid = _save_sparkl_unit(self, forceLoadid)
#             persist_unit(module, self)
#         else:
#             self.loadid = -1 #unsaved sparklunits always get ID -1

#     def getNextExprId(self):
#         id = self._nextExprId
#         self._nextExprId = id + 1
#         return id

#     def getCurrentExprId(self):
#         return self._nextExprId -1

#     def addProcessedExpr(self, expr):
#         # mostly added in order but not always
#         processed = self._processedExprs
#         self._processedExprs.append(expr)
    
#     def required_modpaths(self):
#         return [ext.get_modpath() for ext in self._externals]

#     def get_module(self):
#         return self._module

#     def get_filepath(self):
#         return self._filepath

#     def get_filename(self):             # default
#         return self._filepath.name

#     def get_exprs(self):
#         return self._exprs
    
#     def get_text(self):
#         return self._text

#     def idname_syminfo(self, idname):
#         return self._syminfos.get(idname, None)
    
#     def path_syminfo(self, path):
#         """If there is a unique known symbol associated with the term
#         via a using or import, return it.  If there is none, return
#         None. If there are multiple, raise an exception.  This relies
#         on the imported and used modules having all their symbols
#         declared, but does not require this module's symbols to be
#         declared."""

#         idname = path.id
#         modname = path.modname
#         if modname is None:
#             syminfo = self._syminfos.get(idname, None)
#             for external in self._externals:
#                 a_syminfo = external.idname_syminfo(idname)
#                 if a_syminfo is not None:
#                     if syminfo is None:
#                         syminfo = a_syminfo
#                     elif syminfo != a_syminfo:
#                         raise LowError("%s is ambiguous, could be %s or %s",\
#                                        idname, syminfo.symbol().name, \
#                                        a_syminfo.symbol().name)
#             return syminfo
#         else:
#             syminfo = None
#             if modname == self._module.get_modpath().name:
#                 return self._syminfos.get(idname, None)
#             else:
#                 for external in self._externals:
#                     if modname == external.get_modpath().name:
#                         return external.idname_syminfo(idname)
#             raise LowError("Cannot access module of path %s here", path.name)

#     def parse_and_build(self):
#         terms = parse("main", self._text, self)
#         for term in terms:
#             if isinstance(term, TaggedItem):
#                 expr =  build_expr(STATEMENT, term)
#             elif isinstance(term, BraceTerm):
#                 expr =  build_expr(STATEMENT, term)
#             elif isinstance(term, ParenTerm):
#                 expr =  build_expr(PREDEXPR, term)
#             else:
#                 raise term.error("Expecting a command, statement, or fact")
#             self.add_expr(expr)

#     def add_using(self, module):
#         self._externals.append(module)

#     def add_includes(self, filepath):
#         self._includes.append(filepath)

#     def add_import(self, module, syminfos):
#         modpath = module.get_modpath()
#         for external in self._externals:
#             if external.get_modpath() == modpath:
#                 break
#         else:
#             #print "Importing %s into %s"%(modpath.name, self._filepath.name)
#             external = ImportExternal(modpath)
#             self._externals.append(external)
#         for syminfo in syminfos:
#             external.add_syminfo(syminfo)

#     def add_syminfo(self, syminfo):
#         symbol = syminfo.symbol()
#         modname = self._module.get_modpath().name
#         if symbol.modname != modname:
#             raise LowError("Attempting to define symbol %s in module %s", \
#                            symbol, modname)
#         if self._syminfos.has_key(symbol.id):
#             raise LowError("Attempting to redefine symbol %s", symbol)
#         debug("Adding syminfo %s", syminfo)
#         self._syminfos[symbol.id] = syminfo

#     def add_exports(self, pathexprs):
#         self._export_pathexprs = self._export_pathexprs + list(pathexprs)
        
#     def process_exports(self): # do this after all units parsed and built
#         export_dict = {}
#         for pathexpr in self._export_pathexprs:
#             if pathexpr is None:        # special case for exportall
#                 # export all local declarations
#                 for syminfo in self._syminfos.values():
#                     sym = syminfo.symbol()
#                     try:
#                         if export_dict[sym.id] != syminfo:
#                             raise LowError("Id %s already exported as %s"%(sym.id,sym))
#                     except KeyError:
#                         export_dict[sym.id] = syminfo
#                 continue
#             syminfo = self.path_syminfo(pathexpr.get_value())
#             if syminfo is None:
#                 raise pathexpr.error("No declaration found")
#             sym = syminfo.symbol()
#             try:
#                 if export_dict[sym.id] != syminfo:
#                     raise LowError("Id %s already exported as %s"%(sym.id,sym))
#             except KeyError:
#                 export_dict[sym.id] = syminfo
#         self._export_dict = export_dict
        
#     def get_exports(self):
#         "Return a dict mapping idname to syminfos"
#         return self._export_dict

#     def add_expr(self, expr):
#         if expr is None:
#             return
#         if isinstance(expr, HasSymInfo):
#             try:
#                 self.add_syminfo(expr.get_syminfo())
#             except LowError, err:
#                 pm.set()
#                 raise err.error(expr)
#         elif not isinstance(expr, Expr):
#             raise LowError("Cannot add this to the unit's exprs %r", expr)
#         self._exprs.append(expr)

#     def load_decls_into_agent(self, agent):
#         debug("Loading decls into agent %s", agent)
#         for expr in self.get_exprs():
#             debug("  loading expr %s", expr)
#             if isinstance(expr, HasSymInfo):
#                 syminfo = expr.get_syminfo()
#                 debug("  Loading syminfo %s", syminfo)
#                 agent.set_syminfo(syminfo)

#     def load_facts_into_agent(self, agent):
#         debug("Loading facts into agent %s", agent)
#         for expr in self.get_exprs():
#             debug("  loading expr %s", expr)
#             if isinstance(expr, PredExpr):
#                 debug("  Loading fact %s", expr)
#                 try:
#                     expr.predexpr_conclude(agent, NULL_EXPR_BINDINGS)
# #                     if isinstance(expr, SimplePredExpr) \
# #                        and expr.predsym.id == "InformCalled":
# #                         from spark.internal.common import mybreak
# #                         expr1 = expr
# #                         try:
# #                             raise Exception("BREAK %s"%expr)
# #                         except AnyException:
# #                             pm.setprint()
#                 except LowError, err:
#                     pm.set()
#                     raise err.error(expr)


# ################################################################
# # ImportExternal

# class ImportExternal(object):
#     """An object that keeps track of all symbol imported from one module
#     into another."""
#     __slots__ = (
#         "_modpath",                        # name of module imported from
#         "_dict",                    # dict mapping idname to symbols
#         )
    
#     def __init__(self, modpath):
#         self._modpath = modpath
#         self._dict = {}
        
#     def get_modpath(self):
#         return self._modpath
    
#     def add_syminfo(self, syminfo):
#         self._dict[syminfo.symbol().id] = syminfo
        
#     def idname_syminfo(self, idname):
#         "Get syminfo if idname is imported from this module"
#         return self._dict.get(idname, None)

#     def __str__(self):
#         return "<Import %s>"%self._modpath.name

#     def __repr__(self):
#         return self.__str__()

# ################################################################
# #        
            
# class SparklFileUnit(SparklUnit):
#     __slots__ = (
#         "_filename",
#         )
#     def __init__(self, module, filepath, text, filename):
#         #saveSparklUnit=True (we always save FileUnits)
#         SparklUnit.__init__(self, module, filepath, text, filepath.name, True)
#         self._filename = filename

#     def get_filename(self):
#         return self._filename

# class SparklStringUnit(SparklUnit):
#     __slots__ = ()
#     idnumber = 0
#     def __init__(self, module, text, saveSparklUnit=False, forceLoadid=-1):
#         modpath = module.get_modpath()
#         newid = SparklStringUnit.idnumber + 1
#         SparklStringUnit.idnumber = newid
#         SparklUnit.__init__(self, module, modpath, text, "string%d" % newid, saveSparklUnit, forceLoadid)
#         modunit = module.get_sparkl_unit()
#         self._externals = modunit._externals
#         self._includes = modunit._includes

#     def get_filename(self):
#         return "<string input>"

# ################################################################
# #
# class Module(ValueInt):
#     __slots__ = (
#         "_modpath",
#         "_sparklUnits",                     # list of SPARK-L units
#         "_used_by_modpaths",            # list of modpaths that use/import this
#         "main_name",                   # name of main action
#         )
#     def __init__(self, modpath):
#         self._modpath = modpath
#         self._sparklUnits = []
#         self._used_by_modpaths = []
#         self.main_name = None

#     def inverse_eval(self):
#         return Structure(Symbol("spark.lang.builtin.moduleNamed"), \
#                               (self._modpath.name,))
#     def value_str(self):
#         return ","+value_str(self.inverse_eval())
#     def idname_syminfo(self, idname):
#         "Get a syminfo for idname if declared in any SPARK-L unit in this module"
#         for unit in self._sparklUnits:
#             syminfo = unit.idname_syminfo(idname)
#             if syminfo is not None:
#                 return syminfo
#         return None

#     def get_modpath(self):
#         return self._modpath

#     def get_sparkl_unit(self, filepath=None):
#         filepath = (filepath or self._modpath)
#         for unit in self._sparklUnits:
#             if unit.get_filepath() == filepath:
#                 return unit
#         return None

#     def parse_and_build_source(self, filepath):
#         if not self.get_sparkl_unit(filepath):
#             # find and read file
#             must_find_file = get_source_locator()
#             filename = must_find_file(filepath)
#             text = open(filename, 'rb').read() # may raise exception
#             # construct and add unit
#             unit = SparklFileUnit(self, filepath, text, filename)
#             self._sparklUnits.append(unit)
#             if _BUILTIN_MODULE == self:  # avoid circular refs
#                 from spark.lang.builtin import EXPRS
#                 for expr in EXPRS:
#                     unit.add_expr(expr)
#                 #persist_unit(unit)
#             else:
#                 unit.add_using(_BUILTIN_MODULE)
#             # parse and build Exprs
#             unit.parse_and_build()

#     def _install(self):
#         modpath = self._modpath
#         done = False
#         try:
#             PATH_TO_MODULE[modpath] = INPROGRESS
#             self.parse_and_build_source(modpath)
#             # All declarations should now be known
#             for unit in self._sparklUnits:
#                 for expr in unit.get_exprs():
#                     if isinstance(expr, Expr):
#                         #print "Processing"
#                         expr.process(())
#                 unit.process_exports()

#             PATH_TO_MODULE[modpath] = self
#             done = True
#         finally:
#             if done:
#                 for unit in self._sparklUnits:
#                     for uses_modpath in unit.required_modpaths():
#                         mod = PATH_TO_MODULE[uses_modpath]
#                         mod._used_by_modpaths.append(modpath)
#             else:
#                 del PATH_TO_MODULE[modpath]

#     def get_used_by_modpaths(self):
#         return self._used_by_modpaths[:] # make a copy

#     def _uninstall(self):
#         modpath = self._modpath
#         if self._used_by_modpaths:
#             raise LowError("Cannot uninstall module %s - it is used by %s", \
#                            modpath, self._used_by_modpaths)
#         print "Dropping SPARK module", modpath.name
#         for unit in self._sparklUnits:
#             # unrecord the used_by links
#             for uses_modpath in unit.required_modpaths():
#                 uses_mod = PATH_TO_MODULE[uses_modpath]
#                 uses_mod._used_by_modpaths.remove(modpath)
#             # assume any Python module of the same name should be dropped
#             sourcepath = unit.get_filepath()
#             if sourcepath and sourcepath.name: # not None or Symbol("")
#                 try:
#                     del sys.modules[sourcepath.name]
#                     print " Dropping python module", sourcepath.name
#                 except KeyError:
#                     pass

#         del self._sparklUnits[:]
#         del PATH_TO_MODULE[modpath]

#     def load_into(self, agent):
#         """load the declarations and facts into the agent knowledge base."""
#         # load the syminfos first
#         for unit in self._sparklUnits:
#             for modpath in unit.required_modpaths():
#                 agent.load_modpath(modpath)
#             unit.load_decls_into_agent(agent)
            
#         for unit in self._sparklUnits:
#             unit.load_facts_into_agent(agent)
            
#     def parse_string(self, exprkind, text, varnames, saveSparklUnit=False, forceLoadid=-1):
#         unit = SparklStringUnit(self, text, saveSparklUnit, forceLoadid)
#         term = parse("term_end", text, unit)
#         expr = build_expr(exprkind, term)
#         expr.process(varnames)
#         return expr, unit

#     def __str__(self):
#         return "<Module %s>"%self._modpath.name

#     def __repr__(self):
#         return self.__str__()
        
# ################################################################


# PATH_TO_MODULE = {}     # maps modpath to INPROGRESS (in progress) or Module

# INPROGRESS = intern("INPROGRESS")

# # The following needs to be made threadsafe
# def symbol_get_syminfo(symbol):
#     modname = symbol.modname
#     if modname is None:
#         raise LowError("Cannot get symbol info for symbol %r - no module", \
#                        symbol)
#     module = PATH_TO_MODULE.get(Symbol(modname), None)
#     if module is INPROGRESS:
#         raise LowError("Circular use of module %s"%modpath)
#     if module is None:
#         raise LowError("Module of symbol %r is not installed", symbol)
#     syminfo = module.idname_syminfo(symbol.id)
#     if syminfo is None:
#         raise LowError("Symbol %r is not defined in module %s",symbol,modname)
#     return syminfo

# _NODEFAULT=[]

# _BUILTIN_MODULE = None

# def get_builtin_module():
#     return _BUILTIN_MODULE

# def init_builtin():
#     global _BUILTIN_MODULE
#     _BUILTIN_MODULE = Module(BUILTIN_MODPATH)
