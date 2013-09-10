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
#* "$Revision:: 111                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
import os.path
import sys

# Routines to keep track of file system information
# An Info is information about something
# - a DirInfo contains a listing of a directory
# - a FileInfo contains the contents of a .spark file
# - a PFileInfo contains the contents of a processed .spark file
#
# A Cache is a mapping from spark names of the form "a.b.x" to the
# corresponding Info objects. E.g., the DirInfo for "a.b.x" contains
# the directory listing of <root>/a/b/x/ for some <root> in sys.path,
# whereas the FileInfo contains the contents of the file
# <root>/a/b/x/_module.spark or <root>/a/b/x.spark.
#
# The relevant method is Cache.getInfo(InfoClass, name, current). If
# Current is None, this will only look in the cache and not do any
# file system operations to create a new Info. If current is False, it
# will use any existing information that is cached, but will look in
# the file system if the information isn't cached. If current is True,
# then the file system is checked to make sure that the information in
# a cached Info is up-to-date and if it isn't, the Info is updated
# with the latest information from the file system.
#
# If there is some problem with getting the information, then the
# errorMsg field of the Info will be set to an ErrorString explaining
# the problem.
#
# The idea is to have access to either the most recently cached or the
# most up-to-date information, where up-to-date means cached since the
# last time the Cache timestamp was incremented. Timestamp is probably
# a bad word to use as it more of a revision number than a time.

# Possible extension: tweak the path manipulation and
# stat/listdir/read to allow for accessing things beyond the ordinary
# file system (zip files, ftp, http, external KB, learned procedure
# info, ...). Maybe use different subtypes of PathString. Possibly add
# new RootInfo-like classes. Possibly add Cache.addRootInfo method.

# Possible extension: added new info classes, e.g., PythonFileInfo for
# *.py files (add "valid python package" bit to DirInfo),

class ErrorString(str):
    """A string that indicates an error message rather than a valid path"""
    __slots__ = ()

class PathString(str):
    """A string that indicates a valid path"""
    __slots__ = ()

UNINITIALIZED = ErrorString("uninitialized")

class Info(object):
    __slots__ = (
        "name",                         # string name "a.b.c"
        "timestamp",                    # timestamp of this Info
        "path",                         # path to object
        "errorMsg",             # an ErrorString or None (if no error)
        "stat",                         # relevant stat information 
        )

    def __init__(self, name):
        self.name = name
        self.setInfoBasedOnPath(-1, UNINITIALIZED)

    def setInfoBasedOnPath(self, timestamp, path):
        self.timestamp = timestamp
        if isinstance(path, ErrorString):
            self.path = None
            self.errorMsg = path
        else:
            self.path = path
            try:
                rawstat = os.stat(path)
                stat = (rawstat.st_size, rawstat.st_mtime)
                if self.stat != stat:
                    self.stat = stat
                    self.setContents(path)
                    self.errorMsg = None
                return
            except OSError, e1:
                self.errorMsg = ErrorString(e1.strerror)
        self.setContents(None)
        self.stat = None

    def determinePath(self, cache, name, parent, x): # ABSTRACT
        """Given a cache, a name a.b.x, and a parent Container,
        work out the path to the relevant file/directory.
        Return an ErrorString if there is some problem"""

    def setContents(self, path):        # ABSTRACT
        """Set the contents from path, or default contents for
        None, or raise an OSError."""


class DirInfo(Info):                    # Also a "Container"
    __slots__ = (
        "_elements",
        )

    def determinePath(self, cache, name, parent, x):
        return parent.getElementPath(x, True)

    def setContents(self, path):
        self._elements = ()             # default
        if path:
            self._elements = os.listdir(path)

    # "Container" methods

    def cannotFindError(self, thing):
        "Construct an error string for not being able to find thing in this dir"
        if self.errorMsg:
            return self.errorMsg
        else:
            return ErrorString("Cannot find %s in %s"%(thing, self.path))

    def getElementPath(self, baseString, required):
        """Get the path of the unique element baseString.
        Return None if it doesn't exist and required is False.
        Return an ErrorString if there is some error."""

        if baseString in self._elements:
            return PathString(os.path.join(self.path, baseString))
        elif self.errorMsg:
            return self.errorMsg
        elif required:
            return self.cannotFindError(baseString)
        else:
            return None


class RootInfo(DirInfo):
    __slots__ = ()

    def __init__(self, path):
        DirInfo.__init__(self, "")
        self.path = PathString(path)

    def determinePath(self, cache, name, parent, x): # Not actually needed
        return self.path

    def update(self, timestamp):
        if self.timestamp != timestamp:
            self.setInfoBasedOnPath(timestamp, self.path)


SPARK_EXT = ".spark"
MODULE_SPARK = "_module" + SPARK_EXT
CACHE_EXT = ".csp"

class FileInfo(Info):
    __slots__ = (
        "text",
        )

    def determinePath(self, cache, name, parent, x):
        xSpark = x + SPARK_EXT
        filePath = parent.getElementPath(xSpark, False)
        if isinstance(filePath, ErrorString):
            return filePath
        dirPath = parent.getElementPath(x, False)
        if isinstance(dirPath, ErrorString):
            return dirPath
        elif dirPath:
            if filePath:
                # Temporarily allow x.spark to overrule x/_module.spark
                return filePath
                return ErrorString("Found both %s and %s"%(dirPath, filePath))
            dirInfo = cache.getInfo(DirInfo, name, True)
            return dirInfo.getElementPath(MODULE_SPARK, True)
        elif not filePath:
            return parent.cannotFindError("%s or %s"%(x, xSpark))
        else:
            return filePath

    def setContents(self, path):
        self.text = None               # default
        if path:
            f = open(path, 'rb')
            self.text = f.read()
            f.close()

class PFileInfo(FileInfo):
    __slots__ = ()
    
    def determinePath(self, cache, name, parent, x):
        path = FileInfo.determinePath(self, cache, name, parent, x)
        if isinstance(path, ErrorString):
            return path
        else:
            return PathString(path[:-len(SPARK_EXT)] + CACHE_EXT)

################################################################

        
class Cache(object):                    # Also a "Container"
    __slots__ = (
        "_rootInfos",                       # list of RootInfos
        "_map",                    # map info class to dict:name->info
        "_rootsText",                   # text for error messages
        "timestamp",                    # current timestamp for cache
        )

    # Public interface

    def __init__(self, roots):
        myroots = []
        # Try to eliminate obvious duplicates
        for root in roots:
            #prevent spark/bin from being on path
            if root == '.':
                continue
            normpath = os.path.normpath(root)
            if normpath not in myroots:
                myroots.append(normpath)
        self._rootInfos = [RootInfo(myroot) for myroot in myroots]
        self._rootsText = ", ".join(myroots)
        self.timestamp = 0
        self._map = {}
        ## Ensure other attributes are set
        #self.getRoot("spark")

    def newTimestamp(self):
        timestamp = self.timestamp + 1
        self.timestamp = timestamp
        return timestamp

    def getInfo(self, cls, name, current):
        """Get info from _map[cls], creating a new instanceif necessary.
        current = None: if cached, use it, otherwise return None
        current = False: if cached, use it, otherwise create a new one
        current = True: always get the latest information
        """
        name = str(name)
        d = self._map.get(cls)
        if d is None:           # this class not previously looked for
            if not issubclass(cls, Info):
                raise TypeError("argument must be a subclass of Info: %r"%cls)
            d = {}
            self._map[cls] = d
        info = d.get(name)
        if info is None: # this name not previously checked for
            if current is None:
                return None
            info = cls(name)
            d[name] = info
        else:
            if info.timestamp == self.timestamp or not current:
                return info
        # update info
        components = name.split(".")    # [A, B, X]
        x = components[-1]
        # Attempt to find:
        #   parent = self (for top level item) or DirInfo for A.B
        if len(components) == 1:
            parent = self
        else:
            parentName = ".".join(components[:-1])
            parent = self.getInfo(DirInfo, parentName, True) 
        path = info.determinePath(self, name, parent, x)
        info.setInfoBasedOnPath(self.timestamp, path)
        return info

    # "Container" methods

    def cannotFindError(self, thing):
        "Construct an error string for not being able to find thing in roots"
        return ErrorString("Cannot find %s in %s"%(thing, self._rootsText))
    
    def getElementPath(self, baseString, required):
        """Get the unique path of element baseString in some root directory.
        Return None if no <root>/<baseString> exists.
        Return an ErrorString if multiple <root>/<baseString> exist."""
        timestamp = self.timestamp
        found = []
        for rootInfo in self._rootInfos:
            rootInfo.update(timestamp)
            if not rootInfo.errorMsg:
                path = rootInfo.getElementPath(baseString, False)
                # if rootInfo is valid, then path is not an ErrorString
                if path:
                    # If baseString contains no "." then only consider dirs
                    if "." in baseString or os.path.isdir(path):
                        found.append(path)
        if not found:
            if required:
                return self.cannotFindError(baseString)
            else:
                return None
        elif len(found) > 1:
            msg = "Ambiguous: %s appears as %s"%(baseString, ", ".join(found))
            return ErrorString(msg)
        else:
            return found[0]

def getInfoCache():
    global _INFO_CACHE
    if _INFO_CACHE == None:
        _INFO_CACHE = Cache(sys.path)
    return _INFO_CACHE

_INFO_CACHE = None
