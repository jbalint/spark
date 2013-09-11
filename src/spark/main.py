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
#TODO: we currently don't have the ability to pass arguments into
#an interpreter script, i.e. "spark -exec script args" throws
#away args. the command line interpreter will need some notion
#of command line arguments in order to add this feature

import optparse
import ConfigParser as configparser
import sys
import os
#import threading

from spark.internal.version import *
from spark.internal.version import VERSION
from spark.internal.common import NEWPM, DEBUG
from spark.internal.init import init_spark
from spark.internal.standard import *
from spark.internal.debug.interpreter import *
from spark.internal.debug.tcp_server import *
from spark.internal.debug.debugger import load_module, debugger_cleanup, new_agent, EC_ARGS_ERROR, EC_LOAD_ERROR, EC_DONE
from spark.internal.debug.trace import set_log_file
from spark.util.misc import getSparkHomeDirectory

from spark.internal.parse.basicvalues import Symbol

debug = DEBUG(__name__).on()

# To fix problem with running python under emacs on windows
sys.stderr = sys.stdout

runAgent = None
defaultModule = None
exitcode = 0

_opts = None
def getConfig():
    "Return the ConfigParser object containing the SPARK configuration"
    return _opts

DEFAULT_DEFAULT_MODULE = "spark.lang.builtin"

#'defaults' used in configuration file reading
_CONFIG_DEFAULTS = {'sparkhome' : getSparkHomeDirectory(),
                    'logdir'    : '',
                    'user'      : (os.environ.get('LOGNAME') or
                                   os.getlogin() or
                                   ''),
                    'home'      : (os.environ.get('HOME', None) or
                                   os.environ.get('USERPROFILE', None) or 
                                   os.getenv('HOME') or
                                   ''),
                    'cwd'       : os.getcwd()}


# Define section and option constants
SPARK="spark"
DEFAULTS="defaults"
PERSIST_STATE="persistState"
PERSIST_DIR="persistdir"
PERSIST_INTENTIONS="persistIntentions"
RESUME_STATE="resumeState"
EXECUTE_MAIN="executeMain"
PYTHON_MODE="pythonMode"
COVERAGE_MODE="coverageMode"
INTERACTIVE_MODE="interactive"
DEBUGGER_MODE="debuggerMode"
SPARK_CLI="sparkCLI"
PRINT_OPTS="printOpts"
LOG_FILENAME="logFilename"
SCRIPT_FILENAME="scriptFilename"
STDOUT_BUFFERED="stdoutBuffered"
LOGDIR="logdir"
TCP_SERVER_MODE="tcpServerMode"

#Needed for handling options given as command line args
_DEFAULT_CONFIG_FILE = "%(sparkhome)s/config/spark.cfg"
# TODO: chenge the following because __file__ does not change if the $py.class file is moved
#_DEFAULT_VALUES_FILE = os.path.join(os.path.dirname(__file__), "defaults.cfg")
_DEFAULT_VALUES_FILE = os.path.join(M.spark.__path__[0], "defaults.cfg")
OPTPARSER = optparse.OptionParser(description="Run the SPARK agent system",
                                  version="SPARK v. 0.99",
                                  usage="spark [options] [module [args...]]\n use option --help for help")
#Available options
OPTPARSER.add_option("--configfile", 
                     action="store",
                     dest="configfile",
                     default=_DEFAULT_CONFIG_FILE,
                     help="configuration file to use")
OPTPARSER.add_option("--nosparkconfig",
                     action="store_const",
                     dest="configfile",
                     const="",
                     help="Do not use the configuration file")
OPTPARSER.add_option("--persist", 
                     action="store_true", 
                     dest=PERSIST_STATE,
                     help="enable persistence")
OPTPARSER.add_option("--resume", 
                     action="store_true",
                     dest=RESUME_STATE,  
                     help="enable resuming state")
OPTPARSER.add_option("-r", "--run", 
                     action="store_false",
                     dest=SPARK_CLI,
                     help="no command-line interpreter")
OPTPARSER.add_option("--persist-nointentions", 
                     action="store_false", 
                     dest=PERSIST_INTENTIONS, 
                     help="Do not keep intentions")
OPTPARSER.add_option("--persistdir", 
                     action="store",
                     dest=PERSIST_DIR,
                     help="location to store state")
OPTPARSER.add_option("--nomain", 
                     action="store_false",
                     dest=EXECUTE_MAIN,
                     help='ignore "main:" declarations')
# Not likely to be needed
OPTPARSER.add_option("-s", "--iscript",
                     action="store", 
                     dest=SCRIPT_FILENAME, 
                     help="run the interpreter script file")
# This should eventually be removed
OPTPARSER.add_option("--log", 
                     action="store",
                     dest=LOG_FILENAME,
                     help="name of log file")
OPTPARSER.add_option("--logdir", 
                     action="store",
                     dest=LOGDIR,
                     help="set the directory where logs are stored")
OPTPARSER.add_option("--printopts", 
                     action="store_true",
                     dest=PRINT_OPTS,
                     help="Print options that have been set")
OPTPARSER.add_option("--python",
                     dest=PYTHON_MODE,
                     help="Drop into the Python command line",
                     action="store_true")
OPTPARSER.add_option("--coverage",
                     dest=COVERAGE_MODE,
                     help="Run coverage checking",
                     action="store_true")
OPTPARSER.add_option("--tcp-server",
                     dest=TCP_SERVER_MODE,
                     help="Run TCP server instead of command loop",
                     action="store_true",
                     default=False)
OPTPARSER.add_option("--debugger",
                     action="store_true",
                     dest=DEBUGGER_MODE,
                     help="Use debugger on error during startup")
# This doesn't seem useful - Is it used?
# OPTPARSER.add_option("--loadonly",
#                      action="store_true",
#                      help="Do not run module, only load")
OPTPARSER.add_option("--noninteractive",
                     action="store_true",
                     dest=INTERACTIVE_MODE,
                     help="No questions interrupting work")
OPTPARSER.add_option("--unbuffered", 
                     action="store_false",
                     dest=STDOUT_BUFFERED,
                     help="Output not buffered")
##XXX -exec disabled b/c it's not useful until we can pass in interpreter args
# OPTPARSER.add_option("--exec",
#                      action="store_true",
#                      dest="execMode",
#                      help="execute the interpreter script w/o specifying a module")


def init(logFilenameArg, defaultModuleSpecified, **params):
#     # Do not add in CWD to sys.path
#     cwd = os.getcwd()
#     if cwd not in sys.path:
#         sys.path = [cwd] + sys.path

    #initialize logging
    if logFilenameArg is not None:
        try:
            set_log_file(open(logFilenameArg, 'w'))
        except:
            print "ERROR: log file open failed, logging is disabled. Please verify the log file path is correct."

    init_spark(**params)
    #persist=persistState, resume=resumeState, persistIntentions=persistIntentionState

    global runAgent            
    runAgent = new_agent(runAgent, step_init_fn, PRINT_TRACE)
    
    #if we have loaded from persist data, we still override switch to the
    #default module specified on the command line. this has the nice behavior
    #that if there is no persisted data, SPARK loads normally. we also
    #switch to the default module if we did not load from persisted data
    #print "ready to load default module", runAgent.loaded_from_persist_data, defaultModuleSpecified
    if not runAgent.loaded_from_persist_data or defaultModuleSpecified:
        return load_module(runAgent, defaultModule)
        #from pdb import runcall
        #runcall(load_module, runAgent, defaultModule)

def step_init_fn(agent):
    """default stepper for console SPARK"""
    return StepController(agent)

#iscriptArg is the name of a file containing
#commands to run at startup
#interactive_mode specifies whether or not we accept
#SPARK interpreter commands from the command line.
def interpreter_loop(iscriptArg, interactiveMode, tcpServerMode, logFilenameArg):
    """main loop for the SPARK interpreter"""
    global mod
    initialCommands = []
    if iscriptArg is not None:
        try:
            fIscript = open(iscriptArg, 'r')
        except IOError:
            print "ERROR: Unable to open interpreter script file '%s'"%iscriptArg
            return
        initialCommands = fIscript.readlines()

    if tcpServerMode:
        start_server_thread(runAgent)

    exit = False
    while not exit:                            # loop until interrupted
        
        if len(initialCommands) == 0:
            if not interactiveMode:
                return
            
            #grab commands from the command line
            try:
                next = raw_input('spark>>> ')   # catch 'EOF' instead of breaking
            except EOFError:             # do exit on end of input
                print "\nEND of file"
                next = "exit"
            next = next.strip()
        else:
            #use commands from the interpreter script
            next = initialCommands.pop().strip()
            if len(next) == 0:
                continue
            print next

        if next and next != "" and next != "disconnect":
            exit = process_command(runAgent, next)
                  
def main(*argv):
    """Main command line processing - returns exitcode integer or an exception."""
    global exitcode, defaultModule

    exitcode = 0
    defaultModule = None
    # Update sys.path to include spark_modules contents
    addSparkModules()
    #arguments for the module itself
    moduleArgs = []
    
    optargs = list(argv)
    if len(argv) == 0:
        print "No arguments to main()"
    elif (argv[0].endswith('sparkrun.py') \
          or argv[0].endswith('sparkload.py')):
        del optargs[0]
    else:
        print "Argument to main() does not start with ...spark{run,load}.py:", argv[0]
    try:
        clopts, clargs = OPTPARSER.parse_args(optargs)
        #print clopts
        #print clargs
    except SystemExit, e:
        return EC_DONE
    except AnyException, e:
        print e
        OPTPARSER.print_usage()
        OPTPARSER.print_help()
        exitcode = EC_ARGS_ERROR
        return exitcode

    # Create config (parser) object
    opts = configparser.SafeConfigParser(_CONFIG_DEFAULTS)
    global _opts
    _opts = opts
    opts.add_section(SPARK)
    opts.add_section(DEFAULTS)

    # Parse defaults file and config file if it exists
    try: 
        opts.readfp(open(_DEFAULT_VALUES_FILE))
    except:
        print "Cannot read/parse standard defaults file:", _DEFAULT_VALUES_FILE
        print "exiting"
        return EC_LOAD_ERROR
    if clopts.configfile != "":
        opts.read(clopts.configfile)
        
    # Copy command line argument values over the top of the config
    for (optname, optval) in clopts.__dict__.items():
        # Note: Every command line option already has a default in defaults.cfg
        if optval is not None:          # only override if option set
            opts.set(SPARK, optname, str(optval)) # reconvert to string
    
    if not opts.getboolean(SPARK, STDOUT_BUFFERED):
        sys.stdout=nobuffer(sys.stdout)
        print "Output is unbuffered"
    
    if not opts.getboolean(SPARK, EXECUTE_MAIN):
        print "Execution of main: disabled"

    if opts.getboolean(SPARK, PYTHON_MODE):
        import code
        code.interact()
        exitcode = EC_DONE

    if opts.getboolean(SPARK, COVERAGE_MODE):
        import coverage
        coverage.start()

    defaultModuleSpecified = False
    if len(clargs) > 0:
        defaultModule = clargs[0]
        defaultModuleSpecified = True
        moduleArgs = clargs[1:]

#     #swap up the arguments if we are in execMode
#     if opts.get(SPARK,'execMode'):
#         print "Exec mode activated, main: will be disabled"
#         opts.set(SPARK, 'iscriptArg', defaultModule)
#         defaultModule = None
#         if opts.get(SPARK, 'iscriptArg') in ("", None):
#             exitcode = EC_ARGS_ERROR
#         #exec main has no meaning in exec script mode
#         opts.set(SPARK, 'executeMain', False)

    if defaultModule is None:
        defaultModule = DEFAULT_DEFAULT_MODULE

    if exitcode:
        if exitcode == EC_ARGS_ERROR:
            print "Invalid arguments"
            OPTPARSER.print_usage()
            OPTPARSER.print_help()
        return exitcode

    #assert args[0] == __file__ # __file__ not defined in jython
    #script_dir = os.path.dirname(os.path.abspath(args[0]))
    #sys.path.append(os.path.join(script_dir, "src"))

    if opts.getboolean(SPARK, SPARK_CLI):
        try:
            from spark import svnrevision
            version = svnrevision.version
        except:
            version = "unknown"
        print
        print "Welcome to the SPARK interpreter v %s alpha (svn revision %s)"%(VERSION,version)
        print 'Type "help" without quotes to see available commands'
        print
    
    if opts.getboolean(SPARK, PRINT_OPTS):
        print "Options:"
        opts.write(sys.stdout)
        print ' - Module:\t\t\t%s'%defaultModule
        if moduleArgs is not None:
            print " - Module Args:\t\t\t", moduleArgs

    if opts.get(SPARK, LOGDIR) is not None:
        opts.set(DEFAULTS, LOGDIR, opts.get(SPARK, LOGDIR))
        
    init_result = 0
    try:
        init_result = init(opts.get(SPARK, LOG_FILENAME) or None, # "" -> None
                           defaultModuleSpecified,
                           persist=opts.getboolean(SPARK, PERSIST_STATE),
                           resume=opts.getboolean(SPARK, RESUME_STATE),
                           persistDir=opts.get(SPARK, PERSIST_DIR),
                           interactive=opts.get(SPARK, INTERACTIVE_MODE),
                           persistIntentions=opts.getboolean(SPARK, PERSIST_INTENTIONS),
                           logParams=dict(opts.items(DEFAULTS)))

        #only run the SPARK main if:
        # - we are not resuming from a SPARK persisted state
        # - the user has specified command line longoptions to do so
        # - no errors thus far
        if opts.getboolean(SPARK, EXECUTE_MAIN) and not exitcode:
            err = execute_spark_main(runAgent, moduleArgs)
            if err is not None:
                raise err #pass to outside handler

        #if not (opts.get(SPARK, 'loadOnly') or exitcode):
        if not exitcode:
            interpreter_loop(opts.get(SPARK, SCRIPT_FILENAME) or None,
                             opts.getboolean(SPARK, SPARK_CLI), 
                             opts.getboolean(SPARK, TCP_SERVER_MODE),
                             opts.get(SPARK, LOG_FILENAME) or None)
        elif init_result == None or init_result == 0:
            exitcode = EC_LOAD_ERROR
    
    except AnyException, e:
        errid = NEWPM.displayError()
        import traceback
        traceback.print_exc()
        if opts.getboolean(SPARK, DEBUGGER_MODE):
            import pdb
            pdb.post_mortem(sys.exc_info()[2])
        #NEWPM.pm(errid)
        return e #pass up to Java

    # Workaround for bugs in OAA 2.3.2
    mod = sys.modules.get("spark.io.oaa")
    if mod:
        # disconnect/stop OAA if it has been loaded
        mod.oaaStop(runAgent)
        # Try to kill off rogue OAA 2.3.2 thread
        try:
            from jarray import zeros
            from java.lang import Thread
            threads = zeros(Thread.activeCount(), Thread)
            num = Thread.enumerate(threads)
            #print num, "active Java threads on exiting SPARK:"
            for t in threads:
                #print " ", t, ("NOT DAEMON", "daemon")[t.isDaemon()]
                if t.name == "pool-1-thread-1":
                    print "Explicitly stopping thread pool-1-thread-1"
                    t.stop()
        except ImportError:
            pass

    dispose(runAgent)
    debugger_cleanup()
    return exitcode

def getProperty(joptname,penvname):
    "Retrieve options from registry or value from environment"
    try:
        from java.lang import System
#         print "System.getProperty(%r)=%r"%(joptname, System.getProperty(joptname))
        return System.getProperty(joptname)
#         from org.python.core import PySystemState
#         return PySystemState.registry.get(joptname)
    except ImportError:
        import os
        return os.getenv(penvname)

def addSparkModules():
    """Look for spark_modules in ancestor directories."""
    spark_modules_dir = getProperty("spark.modules", "SPARK_MODULES")
    if spark_modules_dir == None:
        return
    try:
        subdirs = os.listdir(spark_modules_dir)
    except:
        print "spark.modules directory is not listable:", spark_modules_dir
        subdirs = ()
    print "Adding spark modules in", spark_modules_dir
    for subdir in subdirs:
        subpath = os.path.join(spark_modules_dir, subdir, "src", "spark")
        if os.path.exists(os.path.join(subpath, subdir)):
            #print "Adding spark_module", subpath
            sys.path.append(subpath)

class nobuffer:
    """Flushes a file stream every time a write is called"""
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)
