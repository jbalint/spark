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
################################################################
# Source/FileSource API
################################################################

class Source:
    def __init__(self, sourcename, string):
        self._sourcename = sourcename
        self._string = string

    def string(self):
        "Return something with getitem and getslice operators like a string"
        return self._string

    def find_line(self, index):
        """For the index into string, return the line number (0-based)
        character within line (0-based), and the line itself (no newline)."""
        string = self._string
        line_start_index = string.rfind('\n',0,index)+1
        line_end_index = string.find('\n',index)
        if line_end_index < 0:
            line_end_index = len(string)
        lineindex = string.count('\n',0,index)
        line = string[line_start_index:line_end_index]
        charindex = index - line_start_index
        return (lineindex, charindex, line)

    def msg_string(self, start, end, marker, message):
        errloc = self.error_location_string(start, end, marker)
        return "%s\n%s\n%s" % (self._sourcename, errloc, message)

    def error_location_string(self, context_index, error_index, marker):
        """Return a string describing the location of an error."""
        (clinenum, ccharnum, cline) = self.find_line(context_index)
        (elinenum, echarnum, eline) = self.find_line(error_index)
        (coffset, cmodline) = expandtabs(ccharnum, cline)
        (eoffset, emodline) = expandtabs(echarnum, eline)
        if context_index == error_index:
            return "%3d| %s\n     %s%s"%(elinenum+1, emodline," "*eoffset, marker)
        elif clinenum == elinenum:
            mark = " "*coffset + "-"*(eoffset-coffset)
            return "%3d| %s\n     %s%s"%(elinenum+1, emodline, mark, marker)
        else:
            mark1 = " "*coffset + "-"*(len(cmodline)-coffset)
            mark2 = "-"*eoffset
            if clinenum + 1 == elinenum:
                format = "%3d| %s\n     %s\n%3d| %s\n     %s%s"
            else:
                format = "%3d| %s\n     %s...\n%3d| %s\n  ...%s%s"
            return  format % (clinenum+1, cmodline, mark1,
                              elinenum+1, emodline, mark2, marker)

def expandtabs(charindex, line):
    """Expand the tabs in line. Return the equivalent character
    index to charindex and the expanded line."""
    expandedline = line.expandtabs()
    prefix = line[:charindex].expandtabs()
    expandedcharindex = len(prefix)
    return (expandedcharindex, expandedline)

class FileSource(Source):
    def __init__(self, filename):
        f = open(filename, 'rb')
        string = f.read()
        f.close()
        Source.__init__(self, "File %s"%filename, string)
