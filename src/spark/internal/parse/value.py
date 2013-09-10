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
#* "$Revision:: 460                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from spark.internal.version import *
from spark.internal.parse.pickleable_object import PickleableObject
from spark.internal.parse.stringbuffer import StringBuffer

class Value(PickleableObject):
    """An object representing a SPARK value (other than those based on
    built-in python types).

    A Value subclass should define: append_value_str and inverse_eval.

    Subclasses of Value to be pickled should follow the
    PickleableObject protocol, defining __restore__ and specifying
    __stateslots__.
    """

    __stateslots__ = ()
    __slots__ = __stateslots__

    def __str__(self):
        # Absent any other method, use the SPARK representation
        return str(self.append_value_str(StringBuffer()))

    def __repr__(self):
        # Absent any other method, use the SPARK representation.
        # If it doesn't start with '<', then stick it inside <S...>
        strRepresentation = self.__str__()
        if strRepresentation.startswith("<"):
            return strRepresentation
        else:
            return "<S|%s>"%strRepresentation

    def append_value_str(self, buf):
        """Appends the SPARK string representation of self to buf,
        returning buf.

        By convention, use a <...> representation for an object that
        is not parseable by the SPARK parser.
        """
        return buf.append("<%s.append_value_str not implemented>"%self.__class__.__name__)

    def inverse_eval(self):
        """Return a structure that when evaluated returns self.

        All the elements of this should things whose printed
        representation is parseable by the SPARK parser.
        """
        raise Unimplemented("inverse_eval")
