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
#* "$Revision:: 155                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#

import sys
import traceback
import os
from spark.internal.version import *
from spark.internal.common import NEWPM

from spark.internal.engine.agent import Agent
from spark.internal.parse.processing import ensure_modpath_installed
from spark.internal.parse.basicvalues import Symbol

from spark.internal.repr.common_symbols import *
from spark.lang.builtin import requiredargnames, restargnames
from spark.internal.standard import *
from spark.internal.parse.usages import ACTION_DO, TERM_EVAL, PRED_SOLVE
from spark.internal.parse.processing import getPackageDecls

# To fix problem with running python under emacs on windows
sys.stderr = sys.stdout

testagent = None
default_module = "spark.util.misc"

all_symbols = []
#excludes = ["spark.tests.", "spark_examples.", "processes.", "spark.dnmold", "spark.io.oaa_test", "spark.old"]
excludes = ["spark.io.oaa_test"]

NOSPARKDOC = "NOSPARKDOC" # file to indicate not to process this directory
##############################################################
#    UTILITIES
##############################################################

def get_files():
    """get list of spark modules on the system path"""
    list = []
    for p in sys.path:
        if p is '':              # '' in path should be treated as '.'
            p = "."
        if os.path.isdir(p):
            get_files_sub(p, '', list)
    list.sort()
    return list
            
def get_files_sub(dir, modbase, list):
    """spider the directory for .spark files,
    appending the list of found modules to the list.  filter
    out any modules that match our exclusion list"""
    print "crawling ",dir
    if os.path.isfile(os.path.join(dir,NOSPARKDOC)):
        # ignore any directory containing a file NOSPARKDOC
        return
    files = os.listdir(dir)
    for f in files:
        path = os.path.join(dir, f)
        if os.path.isfile(path):
            modname = None
            if f.endswith('.spark'):
                submod = f[0:-6]
                if submod == "_module":
                    modname = modbase[:-1]
                else:
                    modname = modbase+f[0:-6]
            if modname and not modname in list:
                #filter using our exclusion list
                for el in excludes:
                    if modname.startswith(el):
                        break
                else:
                    #found a module
                    list.append(modname)
                    
        #recurse on subdirectories
        elif os.path.isdir(path) and f != 'CVS':
            get_files_sub(path, modbase+f+'.', list)

def new_agent():
    """starts up the SPARK agent that we use to parse the modules"""
    global testagent
    testagent = Agent("A")

def get_outputfilename(modname):
    """get the name of the file that the module is being documented in"""
    return modname+".html"

def get_outputfile(modname):
    """open a file for the module to output documentation to"""
    f = os.path.join('..', 'doc')    
    f = os.path.join(f, 'sparkdoc')
    f = os.path.join(f, get_outputfilename(modname))
    return open(f, 'w')

# get the footer for frames navigation pages
def get_header_framesnav(title):
    return '<html><head><title>SPARKDOC: '+title+"""</title>
<link rel="stylesheet" href="styles.css" type="text/css" />
</head>
<body>
"""

# get the footer for frames navigation pages
def get_footer_framesnav():
    return "</body></html>"

def get_header(modname):
    """print the header of the documentation page for the specified module"""
    nav_module = None
    splits = modname.split('.')
    if splits and len(splits) > 0:
        nav_module = ''
        modprefix = ''
        for i in range(len(splits)-1):
            if modprefix == '':
                modprefix = splits[i]
            else:
                modprefix = modprefix+'.'+splits[i]                
            nav_module='<a href="'+get_outputfilename(modprefix)+'">'+modprefix+'</a>.'
        nav_module = nav_module+splits[-1]
    else:
        nav_module = 'All Modules'

    from time import strftime, localtime
    timestr = strftime("%d %b %Y %I:%M%p", localtime())
    header = '<html><head><title>SPARKDOC: '+modname+"""</title>
<link rel="stylesheet" href="styles.css" type="text/css" />
</head>
<body>
<h1>SPARK Documentation</h1>
<div class="author">
Module Name: SPARK ("""+nav_module+""")<br />
Organization(s): SRI International<br />
Generated On: """+timestr+"""<br />
<br />
</div>
<div id="breadcrumbs">
<a target="_top" href="../index.html">SPARK documentation</a> > <a href="index-noframes.html">SPARKDOC</a> > """+nav_module+'</div>'
    return header

def get_footer(modname):
    """print footer of documentation page, includes lots of extra lines
    so that anchor tags can jump to the correct element"""
    return '</div>' + '<br />'*20 + '</body></html>'

def sym_cmp(arg1, arg2):
    """for sorting"""
    return cmp(arg1.id, arg2.id)

def syminfo_cmp(arg1, arg2):
    """for sorting"""
    return cmp(arg1.symbol().id, arg2.symbol().id)

#XXX: Delete (expr_cmp)
    #if isinstance(arg1, HasSymInfo) and isinstance(arg2, HasSymInfo):
    #    return cmp(arg1.get_syminfo().symbol().id,
    #               arg2.get_syminfo().symbol().id)

def decl_cmp(arg1, arg2):
    """for sorting two Decls by symbol id"""
    return cmp(arg1.asSymbol().id,
               arg2.asSymbol().id)


##############################################################
#    GENERATE THE MAIN INDICIES
##############################################################

def generate_indexes(modules):
    generate_index_frames(modules)
    generate_indexes_mainframe(modules)
    

##############################################################
#    GENERATE THE FRAME NAVIGATION INDICIES
##############################################################

def generate_index_frames(modules):
    #copy over our index file template
    indexfile = open('../src/sparkdoc.index.html', 'r').read()
    f = get_outputfile('index')
    f.write(indexfile)
    f.close()
    generate_all_modules_framesnav(modules)

def generate_all_modules_framesnav(modules):
    f = get_outputfile('frames-all-modules')
    f.write(get_header_framesnav("SPARK Modules"))
    f.write("""<b><a target="symbolslist" href="frames-all-symbols.html">All modules</a></b><br />
<br />
<b>Modules</b>
<br />""")
    for mod in modules:
        f.write('<a target="symbolslist" href="%s">%s</a><br />'%(get_outputfilename('frames-all-symbols-'+mod), mod))
    f.write(get_footer_framesnav())
    f.close()

##############################################################
#    MODULE INDICIES FOR NON-FRAMES DISPLAY
##############################################################

def generate_indexes_mainframe(modules):
    """generate the list of modules indicies for display in the main
    frame (or standalone)"""
    generate_index_mainframe(modules, '')
    prefixes = []
    for mod in modules:
        splits = mod.split('.')
        if splits and len(splits) > 0:
            modprefix = ''
            for i in range(len(splits)-1):
                if modprefix == '':
                    modprefix = splits[i]
                else:
                    modprefix = modprefix+'.'+splits[i]                
        
                if not modprefix in prefixes:
                    prefixes.append(modprefix)
                    generate_index_mainframe(modules, modprefix)

def generate_index_mainframe(modules, prefix):
    """generate a listing of modules matching the specified prefix for
    display in the main frame (or standalone)"""
    if len(prefix) == 0:
        f = get_outputfile('index-noframes')
        f.write(get_header('Auto-generated documentation'))
    else:
        f = get_outputfile(prefix)
        f.write(get_header(prefix))
        
    if len(prefix) == 0:
        f.write('<h2>List of SPARK Modules</h2>')
        f.write('<div class="entry">'+\
                '<p>The following is a list of auto-generated documentation for all SPARK modules.</p>')
        f.write('<p><a href="'+get_outputfilename('all-symbols')+'">Alphabetical listing of symbols</a></p>')        
    else:
        f.write('<h2>List of SPARK Modules ('+prefix+'*)</h2>')
        f.write('<div class="entry">'+\
                '<p>The following is a list of auto-generated documentation for SPARK modules in '+prefix+'*.</p>')
        f.write('<p><a href="'+get_outputfilename('all-symbols-'+prefix)+'">Alphabetical listing of symbols</a></p>')

    prefixes = []    
        
    for mod in modules:
        if mod.startswith(prefix):        
            idx = mod.rfind('.')
            if idx > -1:
                curr_prefix = mod[0:idx]
                if not curr_prefix in prefixes:
                    if len(prefixes) > 0:
                        f.write('</ul>')
                    f.write('</div>'
                            '<h3><a href="'+get_outputfilename(curr_prefix)+'">'+curr_prefix+'</a></h3>'+\
                            '<div class="entry">'+\
                            '<ul>')
                    prefixes.append(curr_prefix)


                f.write('<li><a href="'+get_outputfilename(mod)+'">'+mod+'</a></li>')

    f.write('</ul>')
    f.write(get_footer('Auto-generated documentation'))
    f.close()

##############################################################
#    SYMBOL INDICIES 
##############################################################

def generate_all_symbols_indexes(modules):
    generate_all_symbols_indexes_mainframe(modules)
    generate_all_symbols_indexes_framesnav(modules)    
    
##############################################################
#    SYMBOL INDICIES FOR NON-FRAMES DISPLAY
##############################################################

def generate_all_symbols_indexes_mainframe(modules):
    """generates alphabetical symbol listings for all subsets
    of modules, e.g. spark.*, task_manager.*, etc..."""
    global all_symbols
    all_symbols.sort(sym_cmp)
    
    generate_all_symbols_index_mainframe('')
    prefixes = []
    for mod in modules:
        idx = mod.rfind('.')
        if idx > -1:
            modprefix = mod[0:idx]
            if not modprefix in prefixes:
                prefixes.append(modprefix)
                generate_all_symbols_index_mainframe(modprefix)

def generate_all_symbols_index_mainframe(prefix):
    """generates alphabetical listings of the symbols for a specified
    subset of modules, defined by the prefix"""
    global all_symbols
    if len(prefix) == 0:
        f = get_outputfile('all-symbols')
        f.write(get_header('Alphabetical listing of symbols'))
    else:
        f = get_outputfile('all-symbols-'+prefix)
        f.write(get_header(prefix))
        
    if len(prefix) == 0:
        f.write('<h2>Alphabetical listing of all SPARK symbols</h2>')
        f.write('<div class="entry">'+\
                '<p>The following is a list of auto-generated documentation for all SPARK symbols')
    else:
        f.write('<h2>Alphabetical listing of SPARK symbols ('+prefix+'*)</h2>')
        f.write('<div class="entry">'+\
                '<p>The following is a list of auto-generated documentation for SPARK symbols in modules '+prefix+'*')
        
    f.write('<ul>')
    for sym in all_symbols:
        if sym.modname.startswith(prefix):        

            f.write('<li><b><a href="'+get_outputfilename(sym.modname)+ anchorLink(sym.id)+'">'+sym.id+'</a></b> in <a href="'+get_outputfilename(sym.modname)+'">'+sym.modname+'</a></li>')

    f.write('</ul>')

    f.write(get_footer('Auto-generated documentation'))
    f.close()

##############################################################
#    SYMBOL INDICIES FOR FRAMES DISPLAY
##############################################################
    
def generate_all_symbols_indexes_framesnav(modules):
    """generates alphabetical symbol listings for all subsets
    of modules, e.g. spark.*, task_manager.*, etc..."""
    global all_symbols
    all_symbols.sort(sym_cmp)
    
    generate_all_symbols_index_framesnav('')
    for mod in modules:
        generate_all_symbols_index_framesnav(mod)

def generate_all_symbols_index_framesnav(prefix):
    """generates alphabetical listings of the symbols for a specified
    subset of modules to be displayed in a frame, defined by the prefix"""
    global all_symbols
    if len(prefix) == 0:
        f = get_outputfile('frames-all-symbols')
        f.write(get_header_framesnav('Alphabetical listing of symbols'))
    else:
        f = get_outputfile('frames-all-symbols-'+prefix)
        f.write(get_header_framesnav(prefix+" symbols"))
        
    if len(prefix) == 0:
        f.write('<b>All SPARK symbols</b>')
    else:
        f.write('<b><a target="mainframe" href="'+get_outputfilename(prefix)+'">'+prefix+'*</b>')
    f.write("<p>")
    for sym in all_symbols:
        if sym.modname.startswith(prefix):        

            f.write('<a target="mainframe" href="'+get_outputfilename(sym.modname)+anchorLink(sym.id)+'">'+sym.id+'</a><br />')
    f.write("</p>")
    f.write(get_footer_framesnav())
    f.close()

def anchorLink(symId):
    return '#' + anchorName(symId)

def anchorName(symId):
    """HTML links are not case-sensitive, so we have to modify upper/lowercase symbols to distinguish them"""
    if symId[:1].isupper():
        return symId
    else:
        return '__'+symId

##############################################################
#    DOCUMENT A SINGLE SYMBOL (FRAMES+NOFRAMES)
##############################################################

def get_fact(agent, factSym, impSym):
    facts = agent.factslist1(factSym, impSym)
    if facts:
        return facts[0][1]
    else:
        return None
    

def doc_symbol(mod, usage, f):
    """generates documentation for the specified symbol.  this is a
    subroutine of doc_module"""
    f.write('<div class="entry">')
    f.write('<dl>')
    modname = mod.get_modpath().name
    global all_symbols
    decls = [d for d in getPackageDecls(testagent, mod.filename)]
    decls.sort(decl_cmp)
    for decl in decls:
        sym = decl.asSymbol()

        if sym.modname == modname and decl.optMode(usage):
            all_symbols.append(sym)
            args = ' <span class="args">'
            required = requiredargnames(testagent, sym)
            if required:
                args = args + '$' + ' $'.join(required)
            restargs = restargnames(testagent, sym)
            if restargs:
                args = args+' <em>rest: '+ ' '.join(restargs)+'</em>'
            args = args + "</span>"
            
            f.write('<dt><a name="'+anchorName(sym.id)+'"></a><b>'+sym.id+'</b>'+args+'</dt>')

            f.write('<dd>')
            doc = get_fact(testagent, P_Doc, sym)
            if doc:
                f.write(doc+'<br />')

            features = get_fact(testagent, P_Features, sym)
            if features:
                f.write('<b>Features:</b> '+htmlStr(features)+'<br />')

            properties = get_fact(testagent, P_Properties, sym)
            if properties:
                f.write('<b>Properties:</b> '+htmlStr(properties)+'<br />')

            f.write('</dd>')
                        
    f.write('</dl>')
    f.write('</div>')

def htmlStr(string):
    return str(string).replace('<', '&lt;')
    
##############################################################
#    DOCUMENT A SINGLE MODULE (FRAMES+NOFRAMES)
##############################################################
                        
def doc_module(module_name):
    """generates the documentation page for the specified module"""
    print "doc_module: ", module_name
    try:
        mod = ensure_modpath_installed(module_name)
        testagent.load_modpath(Symbol(module_name))
    except:
        print "Cannot load %s, may be part of another module"%(module_name)
        return
    
    #old: modname = mod.get_modpath().name
    modname = mod.filename
    
    has_actions = False
    has_predicates = False
    has_functions = False
    #old: syminfos = mod.get_sparkl_unit().get_exports().values()
    #new
    decls = getPackageDecls(testagent, mod.filename)
    #old: for syminfo in syminfos:
    for decl in decls:
        if decl is None:
            continue
        sym = decl.asSymbol()
        if sym.modname == modname:
            if decl.optMode(ACTION_DO):
                has_actions = True
            elif decl.optMode(PRED_SOLVE):
                has_predicates = True
            elif decl.optMode(TERM_EVAL):
                has_functions = True
    
    f = get_outputfile(module_name)
    f.write(get_header(module_name))
    f.write('<h2>Listing for module '+module_name+'</h2>'+\
            '<div class="entry">'+\
            '<p>This is auto-generated documentation.</p>'+\
            '<h4>Contents:</h4>'+\
            '<ul>')
    if has_actions:
        f.write('<li><a href="#actions">Actions</a></li>')
    if has_predicates:
        f.write('<li><a href="#predicates">Predicates</a></li>')
    if has_functions:
        f.write('<li><a href="#functions">Functions</a></li>')
        
    f.write('</ul></div>')

    if has_actions:
        f.write('<h3><a name="actions"></a><a href="#actions">Actions</a></h3>')
        doc_symbol(mod, ACTION_DO, f)
    if has_predicates:
        f.write('<h3><a name="predicates"></a><a href="#predicates">Predicates</a></h3>')    
        doc_symbol(mod, PRED_SOLVE, f)
    if has_functions:
        f.write('<h3><a name="functions"></a><a href="#functions">Functions</a></h3>')    
        doc_symbol(mod, TERM_EVAL, f)

    f.write(get_footer(module_name))
    f.close()

##############################################################
#    MAIN
##############################################################
                        

#the -test option runs sparkdoc on only a single module
#but does generate the actual indicies
def main(argv):
    from spark.internal.init import init_spark
    params = {}
    init_spark(**params) #no persist resume
    if len(argv) > 1:
        if argv[1] == "-test":
            new_agent()
            modules = get_files()
            generate_indexes(modules)
            doc_module(default_module)
            generate_all_symbols_indexes(modules)            
            return
            
    new_agent()
    modules = get_files()
    print "====================", modules
    generate_indexes(modules)
    print "===================="
    for mod in modules:
        print "===================="
        doc_module(mod)

    #generate all symbols must run last
    generate_all_symbols_indexes(modules)


if __name__ == "__main__":
    try:
        print "main(%r)"%sys.argv
        main(sys.argv)
    except:
        errid = NEWPM.displayError()
        
    sys.exit()
