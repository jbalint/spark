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
import string

from spark.internal.version import *
from spark.internal.exception import InvalidArgument

################################################################
# Set operations

# Exprs keep track of sets of variables, the implementation of these
# sets is internal to this file. External to this file, these sets can
# be accessed using "in" as a test or iterator.  I.e., 'for x in set:'
# or 'if x in set:'

# Implemented as sorted tuples of elements.
# Could also be implemented as dicts. 

class _BITS(object):
    __slots__ = ()

    def __getitem__(self,i):
        return bit(i)

BITS = _BITS() # like [1, 2, 4, 8, 16, ...]

class _IBITS(object):
    __slots__ = ()

    def __getitem__(self,i):
        return (i, bit(i))

IBITS = _IBITS() # like [(0,1), (1,2), (2,4), (3,8), (4,16), ...]

def rbitstring(bitmap, str01, length=None):
    char_list = []
    for i,bit in IBITS:
        if length:
            if length <= i:
                break
        else:
            if bitmap < bit:
                break
        char_list.append(str01[bool(bit & bitmap)])
    return "".join(char_list)

def logbitp(index, bitmap):
    return bool(bit(index)&bitmap)

def bitmap_indices(bitmap):
    "Return a list of the indices of bits that are one"
    if bitmap < 0:
        raise InvalidArgument("bitmap must be positive")
    bit_indices = []
    for i,bit in IBITS:
        if bitmap < bit:
            return bit_indices
        if bit & bitmap:
            bit_indices.append(i)
    raise Exception("Can never reach here") # satisfies pychecker

def integer_length(bitmap):
    if bitmap < 0:
        bitmap = ~bitmap
    for i,bit in IBITS:
        if bitmap < bit:
            return i
    raise Exception("Can never reach here") # satisfies pychecker
##     len = 0
##     while bitmap:
##         len = len + 1
##         bitmap = bitmap >> 1
##     return len

def logcount(bitmap):
    "Return number of 1's for positive sets, number of 0's for negative set"
    count = 0
    if bitmap < 0:
        bitmap = ~bitmap
    while bitmap:
        count = count + (bitmap & 1)
        bitmap = bitmap >> 1
    return count

def bit(n):
    if n < 31:                          # necessary until Python 2.4
        return 1<<n
    else:
        return 1L<<n # py_checker - this is supposed to return different types

class Domain(object):
    __slots__ = (
        "_elements",             # members of the domain as a sequence
        "_type",
        "_cache",
        )

    def __init__(self, type=None):
        self._elements = []
        self._type = type
        self._cache = None

    def __str__(self):
        return "D{%s}"%string.join([str(x) for x in self.elements()], ",")

    def __repr__(self):
        return "Domain(%r,%r)"%(self._elements, self._type)

    def _check_type(self, element):
        if self._type and not isinstance(element, self._type):
            raise InvalidArgument("Invalid element for domain")

    def clear_cache(self):
        self._cache = None

    def create_set(self, bitmap):
        """factory method for creating sets that caches, as we end up creating
        ~30 sets/domain"""
        if not self._cache:
            self._cache = {}
        if self._cache.has_key(bitmap):
            return self._cache[bitmap]
        else:
            s = _Set(bitmap, self)
            self._cache[bitmap] = s
            return s

    def singleton(self, element):
        "Make a set containing a single element."
        self._check_type(element)
        return self.create_set(bit(self._index_append(element)))
                    
    # Emulates a sequence

    def __contains__(self, element):
        return element in self._elements

    def __getitem__(self, index):
        """Return the index-th element of the domain.
        self[_] is the inverse of self.index(_)."""
        return self._elements[index]
    
    def __len__(self):
        "Return the number of elements currently in the domain."
        return len(self._elements)

    def index(self, element):
        return self._elements.index(element)
        
    def append(self, element):
        "Add a new element to the domain, must be distinct"
        if element in self._elements:
            raise InvalidArgument("Element already in domain")
        self._check_type(element)
        self._elements.append(element)

    # End of sequence emulation

    def elements(self):
        return self._elements[:]        # copy

    def _index_append(self, element):
        "Append element if not present and return the index of element"
        _elements = self._elements
        try:
            return _elements.index(element)
        except ValueError:
            self._check_type(element)
            next = len(_elements)
            _elements.append(element)
            return next

    def makeset(self, elements=()):
        """Make a set containing elements.
        self.makeset(_) is the inverse of self.elements(_)"""
        bitmap = 0
        for element in elements:
            bitmap = bitmap | bit(self._index_append(element))
        return self.create_set(bitmap)

    def makeset_from_bitmap(self, bitmap):
        """Construct a set given a bitmap for the elements on the set"""
        return self.create_set(bitmap)


class _Set(object): #immutable set objects
    __slots__ = (
        "_bitmap",                       # integer representing elements
        "_domain",                      # optional domain
        )

    def __init__(self, bitmap, domain):
        self._bitmap = bitmap
        self._domain = domain

    # Emulate a sequence

    def __len__(self):
        return logcount(self._bitmap)

    def __nonzero__(self):
        return bool(self._bitmap)

    def index(self, element):
        singleton = bit(self._domain.index(element))
        if singleton & self._bitmap:
            return logcount((singleton-1) & self._bitmap)
        else:
            return ValueError(element)

    def __getitem__(self, index):
        if index < 0:
            index = len(self) + index
        bitmap = self._bitmap
        for i,mask in IBITS:
            if mask & bitmap:
                if index > 0:
                    index = index - 1
                else:
                    return self._domain[i]
            elif bitmap < mask:
                raise IndexError("Index greater than set size")
        raise Exception("Can never reach here") # satisfies pychecker
    # End of sequence emulation

    def elements(self):
        bitmap = self._bitmap
        result = []
        for index,mask in IBITS:
            if mask & bitmap:
                result.append(self._domain[index])
            elif bitmap < mask:
                break
        return result
        

    def bitmap(self):
        return self._bitmap

    def make_positive(self):
        "Takes a negative bitmap and restructs it to the current domain"
        if self._bitmap >= 0:
            return self
        domain = self._domain
        #return _Set(self._bitmap & (bit(len(domain))-1), domain)
        return domain.create_set(self._bitmap & (bit(len(domain))-1))
    
    #def __iand__(self, other):
    #    if self._domain is not other._domain:
    #        raise InvalidArgument("Domains do not match")
    #    self._bitmap = self._bitmap & other._bitmap

    def andInverted(self, other):
        #if self._domain is not other._domain:
        #    raise InvalidArgument("Domains do not match")
        #return _Set(self._bitmap & ~other._bitmap, self._domain)
        return self._domain.create_set(self._bitmap & ~other._bitmap)

    #def iandInverted(self, other):
        #if self._domain is not other._domain:
        #    raise InvalidArgument("Domains do not match")
    #    self._bitmap = self._bitmap & ~other._bitmap

    def __and__(self, other):
        #if self._domain is not other._domain:
        #    raise InvalidArgument("Domains do not match")
        #return _Set(self._bitmap & other._bitmap, self._domain)
        return self._domain.create_set(self._bitmap & other._bitmap)

    #def __ior__(self, other):
        #if self._domain is not other._domain:
        #    raise InvalidArgument("Domains do not match")
    #    self._bitmap = self._bitmap | other._bitmap
    #    return self

    def __or__(self, other):
        #if self._domain is not other._domain:
        #    raise InvalidArgument("Domains do not match")
        #return _Set(self._bitmap | other._bitmap, self._domain)
        return self._domain.create_set(self._bitmap | other._bitmap)
    
    #def __sub__(self, other):
    #    return _Set(self._bitmap & ~ other._bitmap, self._same_domain(other))

    #def xorSet(self, other):
    #    if self._domain is not other._domain:
    #        raise InvalidArgument("Domains do not match")
    #    self._bitmap = self._bitmap ^ other._bitmap

    #def __xor__(self, other):
    #    if self._domain is not other._domain:
    #        raise InvalidArgument("Domains do not match")
    #    return _Set(self._bitmap ^ other._bitmap, self._domain)

    #def invert(self):
    #    self._bitmap = ~ self._bitmap

    def __invert__(self):
        #return _Set(~ self._bitmap, self._domain)
        return self._domain.create_set(~ self._bitmap)

    def subseteq(self, other):
        #if self._domain is not other._domain:
        #    raise InvalidArgument("Domains do not match")
        return not self._bitmap & ~other._bitmap

    #def subset(self, other):
        #if self._domain is not other._domain:
        #    raise InvalidArgument("Domains do not match")
    #    return self._bitmap != other._bitmap and \
    #           not self._bitmap & ~other._bitmap

    #def supset(self, other):
        #if self._domain is not other._domain:
        #    raise InvalidArgument("Domains do not match")
    #    return not other._bitmap & ~ self._bitmap

    #def supseteq(self, other):
        #if self._domain is not other._domain:
        #    raise InvalidArgument("Domains do not match")
    #    return self._bitmap != other._bitmap and \
    #           not other._bitmap & ~ self._bitmap

    def __eq__(self, other):
        if self._domain is not other._domain:
            raise InvalidArgument("Domains do not match")
        return self._bitmap == other._bitmap

    def __ne__(self, other):
        if self._domain is not other._domain:
            raise InvalidArgument("Domains do not match")
        return self._bitmap != other._bitmap

    def __str__(self):
        if self._bitmap < 0:
            return "~" + (~self).__str__()
        return "{" + string.join([str(x) for x in self.elements()], ",") + "}"

    def __repr__(self):
        return "<_Set %s>"%self.__str__()
