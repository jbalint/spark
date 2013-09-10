import code
import sys
import traceback
import pdb

try:
    from java.lang import Exception as JavaException
except:
    JavaException = None

__all__ = ['runPyConsole', 'runPyDebugger', 'applyDebugging']

def tracebackLines(type, value, tb):
    tblist = traceback.extract_tb(tb)
    del tblist[:1]
    lines = traceback.format_list(tblist)
    if JavaException and isinstance(value, JavaException):
        #value.printStackTrace()
        jlines = []
        for t in value.getStackTrace():
            #print "t.className=", t.className
            if (t.className.startswith("sun.reflect")):
                break
            else:
                line = "\tat %s\n"%(t,)
                jlines.append(line)
        lines.extend(reversed(jlines))
    if lines:
        lines.insert(0, "Traceback (most recent call last):\n")
    lines[len(lines):] = traceback.format_exception_only(type, value)
    return lines


class ModifiedConsole(code.InteractiveConsole):
    __slots__ = ()

    def showtraceback(self):
        """Display the exception that just occurred.

        We remove the first stack item because it is our own code.

        The output is written by self.write(), below.

        """
        try:
            type, value, tb = sys.exc_info()
            sys.last_type = type
            sys.last_value = value
            sys.last_traceback = tb
            lines = tracebackLines(type, value, tb)
            map(self.write, lines)
        finally:
            tblist = tb = None

    def interact(self, banner=None, ps1=None, ps2=None):
        """Closely emulate the interactive Python console.

        The optional banner argument specify the banner to print
        before the first interaction; by default it prints a banner
        similar to the one printed by the real Python interpreter,
        followed by the current class name in parentheses (so as not
        to confuse this with the real interpreter -- since it's so
        close!).

        """
        if ps1 is None:
            try:
                ps1 = sys.ps1
            except AttributeError:
                ps1 = ">>> "
        if ps2 is None:
            try:
                ps2 = sys.ps2
            except AttributeError:
                ps2 = "... "
        cprt = 'Type "help", "copyright", "credits" or "license" for more information.'
        if banner is None:
            self.write("Python %s on %s\n%s\n(%s)\n" %
                       (sys.version, sys.platform, cprt,
                        self.__class__.__name__))
        else:
            self.write("%s\n" % str(banner))
        more = 0
        while 1:
            try:
                if more:
                    prompt = ps2
                else:
                    prompt = ps1
                try:
                    line = self.raw_input(prompt)
                except EOFError:
                    self.write("\n")
                    break
                else:
                    if not more and line == "exit":
                        break
                    more = self.push(line)
            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                more = 0

def runPyConsole(locals=None, filename="<console>", ps1=None, ps2=None):
    console = ModifiedConsole(locals, filename)
    try:
        console.interact("Entering Python Console (type exit to exit)", ps1, ps2)
    finally:
        console.write("Leaving Python Console\n")

def runPyDebugger(exc_info = None):
    if exc_info is None:
        exc_info = (sys.last_type, sys.last_value, sys.last_traceback)
    try:
        print "Entering Python Debugger"
        lines = tracebackLines(*exc_info)
        map(sys.stdout.write, lines)
        pdb.post_mortem(exc_info[2])
    finally:
        print "Leaving Python Debugger"

def applyDebugging(function, *args, **keyargs):
    try:
        return function(*args, **keyargs)
    except:
        runPyDebugger(sys.exc_info())

    
