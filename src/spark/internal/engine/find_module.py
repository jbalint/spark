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
#* "$Revision:: 131                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.version import *
import types
from spark.internal.exception import LowError

#from spark.internal.persist import persist_module
#from spark.internal.persist_aux import is_resuming, PERSIST_SPARK
#from spark.internal.parse.newparse import PATH_TO_MODULE, INPROGRESS, get_builtin_module, Module, BUILTIN_MODPATH
from spark.internal.parse.basicvalues import Symbol

#
# Routines for loading and keeping track of Module objects
#

#from spark.internal.parse.processing import modpath_is_installed

#
# Loading modules
#

def find_install_module(modname):
    """this is mostly a legacy hook and has been superceded by ensure_modpath_installed"""
    return ensure_modpath_installed(Symbol(modname))

from spark.internal.parse.processing import ensure_modpath_installed

#
# Unloading modules
#

from spark.internal.parse.processing import drop_modpath
    
from spark.internal.parse.processing import clear_all_modules

#from spark.internal.parse.processing import drop_all_modules

# def moduleNamed(namestring):
#     if not isinstance(namestring, basestring):
#         raise LowError("Module name must be a string, not %r" % namestring)
#     mod = PATH_TO_MODULE.get(Symbol(namestring), None)
#     if mod is None:
#         raise LowError("Module named %s is not loaded" % namestring)
#     return mod

# def moduleNamedInverse(module):
#     if not isinstance(module, Module):
#         return None
#     return module.get_modpath().name
