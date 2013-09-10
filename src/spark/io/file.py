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
from spark.internal.parse.basicvalues import *

# When a FileWrapper is created, it opens a file object using the same
# parameters and redirects all the file method calls on itself to the
# underlying file object. The FileWrapper object also maintains a
# _seekDone attribute that is True if we have done a seek to somewhere
# other than the end of the file.

# When you persist a FileWrapper, the initialization arguments
# (constructor_args()) are the same as the initialization args given
# to create the FileWrapper, except that "!" is prepended to the
# mode. The state arguments (state_args()) indicate the position
# within the file. If we have done a seek to somewhere other than the
# end of the file, we encode this by saving the position as a negative
# number (-1 - position).

# On resuming, (__init__()) we use the original mode to open the
# underlying file, except in the case of a write, where instead of
# overwriting the file, we now need to append to the file. In setting
# the file position (set_state(agent, fileposition)) what we do
# depends upon the mode: For reading, we just seek to the same
# position, assuming the file is the same as it used to be.  For a
# FileWrapper originally created with write mode (now using an
# underlying file created with append mode), we seek the end of the
# file, raising an exception if _seekDone had been set or if the
# length of the file has changed.  For a FileWrapper originally
# created with append mode, we don't care what the current file length
# is. We just append to it.


UNDERLYING_MODE = { "r":"r", "rb":"rb", \
                    "w":"w", "wb":"wb", \
                    "a":"a", "ab":"ab", \
                    "!r":"r", "!rb":"rb", \
                    "!w":"a", "!wb":"ab", \
                    "!a":"a", "!ab":"ab"}
               

class FileWrapper(ConstructibleValue):
    __slots__ = (
        "_desc",                         # file descriptor
        "_mode",
        "_bufsize",
        # When writing to a file, it is important to know whether we
        # are at the end of the file or not.
        "_seekDone",                    # whether a seek has been done
        )

    # The following duplicate the underlying file methods and attributes

    def __init__(self, filename, mode="r", bufsize=-1):
        ConstructibleValue.__init__(self)
        underlyingMode = UNDERLYING_MODE.get(mode)
        if underlyingMode is None:
            raise IOError("invalid mode: %s"%mode)
        self._desc = open(filename, underlyingMode, bufsize)
        self._bufsize = bufsize
        self._mode = mode.strip("!")
        self._seekDone = False

    def close(self):
        self._desc.close()

    def flush(self):
        self._desc.flush()

    def isatty(self):
        return self._desc.flush()

    def fileno(self):
        return self._desc.fileno()

    def read(self, size=-1):
        return self._desc.read(size)

    def readline(self, size=-1):
        return self._desc.readline(size)

    def readlines(self, size=None):
        if size is None:
            return self._desc.readlines()
        else:
            return self._desc.readlines(size)

    def xreadlines(self):
        return self._desc.xreadlines()
    
    def seek(self, offset, whence=0):
        # If we are going anywhere other than the end of the file then
        # set _seekDone. If we are going to the end of the file, unset
        # _seekDone.
        self._seekDone = not (whence == 2 and offset == 0)
        return self._desc.seek(offset, whence)

    def tell(self):
        return self._desc.tell()

    def truncate(self, size=None):
        if size is None:
            return self._desc.truncate()
        else:
            # if size > current pos then we can assume that a seek has
            # been done and we don't need to set _seekDone
            return self._desc.truncate(size)

    def write(self, str):
        self._desc.write(str)

    def writelines(self, sequence):
        self._desc.writelines(sequence)

    def _getClosed(self):
        return self._desc.closed
    closed = property(_getClosed)

    def _getMode(self):
        return self._mode
    mode = property(_getMode)

    def _getName(self):
        return self._desc.name
    name = property(_getName)

    def _getSoftspace(self):
        return self._desc.softspace
    def _setSoftspace(self, value):
        self._desc.softspace = value
    softspace = property(_getSoftspace, _setSoftspace)

    # ConstructibleValue methods for persistence

    cvcategory = "File"
    constructor_mode = "VVV"
    def cvname(self):
        return "%s:%s"%(self.name, self._mode)
        
    def constructor_args(self):
        return [self.name, "!"+self._mode, self._bufsize]

    def state_args(self):
        self._desc.flush()
        # encode _seekDone in sign of fileposition
        fileposition = self._desc.tell()
        if self._seekDone:
            return (-1 - fileposition,)
        else:
            return (fileposition,)

    def restoreError(self, msg):
        return IOError("cannot safely restore file %s, open for writing: %s"\
                       %(self._desc.name, msg))

    def set_state(self, agent, fileposition):
        desc = self._desc
        if fileposition < 0:
            self._seekDone = True
            fileposition = -1 - fileposition
        else:
            self._seekDone = False
        if self._mode.startswith("r"):
            # Assume the file is the same
            desc.seek(fileposition)
        elif self._mode.startswith("w"):
            if self._seekDone:
                raise self.restoreError("not at EOF")
            desc.seek(0, 2)             # go to EOF
            eofpos = desc.tell()
            if eofpos < fileposition:
                raise self.restoreError("file is now shorter")
            elif eofpos > fileposition:
                raise self.restoreError("file is now longer")
        elif self._mode.startswith("a"):
            # Don't worry if the file is different
            pass
        else:
            raise self.restoreError("invalid mode")

installConstructor(FileWrapper)
