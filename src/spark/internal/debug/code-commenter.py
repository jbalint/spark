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
#Use this code to comment/uncomment certain parts of codes programmatically.
import os, sys

COMMENT_STARTING_FLAG = "#Testing Script. Begin:"
COMMENT_ENDING_FLAG = "#Testing Script. End."
COMMENTER_USAGE = "Usage:\n" + \
                  "\t-r: recursive\n" + \
                  "\t-dir [dir]: starting directory (default is \"..\")\n" + \
                  "\t-file [file]: only this file (overrides the -dir option)\n" + \
                  "\t-ext [extension]: file extensions (default is .py)\n" + \
                  "\t-tag [comment-tag]: comment tag (defualt is \"#\ for python files\")\n" + \
                  "\t-uncomment: removes the comment tags (default is commeting)\n"

def generateFileList(startingDir, subDir, extension):
    file_list = []
    if subDir:
        def add_file(extension, directory, names):
            for name in names:
                if name.endswith(extension):
                    file_list.append(os.path.join(directory, name))
        os.path.walk(startingDir, add_file, extension)
    else:
        files = os.listdir(startingDir)
        for afile in files:
            fullname = os.path.join(startingDir, afile)
            if os.path.isfile(fullname) and fullname.endswith(extension):
                file_list.append(fullname)
    return file_list

def toggleComments(afile, commenting, comment_tag):
    global COMMENT_STARTING_FLAG, COMMENT_ENDING_FLAG
    changed = False
    try:
        desc = file(afile)
        newlines = []
        lines = desc.readlines()
        inside = False
        for line in lines:
            if line.find(COMMENT_STARTING_FLAG) > -1:
                inside = True
            elif line.find(COMMENT_ENDING_FLAG) > -1:
                inside = False
            elif inside:
                if commenting and line[0]!=comment_tag:
                    line = comment_tag + line
                    changed = True
                elif (not commenting) and line[0]==comment_tag:
                    line = line[1:]
                    changed = True
            newlines.append(line)
        desc.close()
        if changed:
            desc = file(afile, "w")
            desc.writelines(newlines)
            desc.close()
            return "Succeeded"
    except:
        return "Failed"
    return "Unchanged"

if __name__ == "__main__":
    startingDir = ".."
    subDir = False
    extension = "py"
    comment_tag = "#"
    commenting = True
    afile = None
    _usage = False
    i = 1
    while i<len(sys.argv):
        arg = sys.argv[i]
        if arg == "-r":
            subDir = True
        elif arg == "-ext":
            i = i + 1
            extension = sys.argv[i]
        elif arg == "-dir" or arg =="-directory":
            i = i + 1
            startingDir = sys.argv[i]
        elif arg == "-tag":
            i = i + 1
            comment_tag = sys.argv[i]
        elif arg == "-file":
            i = i + 1
            afile = sys.argv[i]
        elif arg == "-uncomment":
            commenting = False
        elif arg == "-h" or arg == "-help" or arg == "/?" or arg == "-usage":
            _usage = True  
        else:
            print "Error in the arguments.\n"
            _usage = True
        i = i + 1
    if _usage:
        print COMMENTER_USAGE
        sys.exit(1)
    if not extension.startswith("."):
        extension = "." + extension
    startingDir = os.path.abspath(startingDir)
    files = (afile,)
    if afile is None:
        files = generateFileList(startingDir, subDir, extension)
    print "Processing %s files..."%len(files)
    for afile in files:
        if commenting:
            print "Commenting "+ afile+ "...",
        else:
            print "Uncommenting "+ afile+ "...",
        print toggleComments(afile, commenting, comment_tag)
