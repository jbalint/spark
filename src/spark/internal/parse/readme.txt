NOTES ON THE JAVA IMPLEMENTATION OF VALUES


# How is the switching between Java and Python implementations done?

There spark.internal.parse.javamode Python module defines a function
javaMode().  It's value is determined by a constant _JAVA_MODE in the
module.  A Python module, xxx.py, that needs to choose between
different implementations imports javamode and calls javaMode(). Based
on the result it either imports symbols (Java classes) from Java
packages or imports symbols from another Python module (generally
called xxx_python.py).

The two examples as of September 19, 2006, are values.py and
constructor.py.


# How do I use the Java implementations?

Manually edit the value of _JAVA_MODE in spark/internal/parse/javamode.py.


# Why are there duplicate methods in SConstructorInterface and why are
  there SConstructorJ and SConstructorP?

In Jython, it is hard to get automatic conversion from Python objects
to Java Object arrays. The SConstructorInterface needs to be
implemented both in Jython and in Java and needs to be called both
from Jython and from Java. The Object[] methods are implemented and
called by Java classes. The PyObject versions are implemented by
Python classes and called from Python.

The SConstructorJ class is meant to be extended in Java and provides
an implementation of the PyObject versions of the methods in terms of
the Object[] versions (which are defined in the extension class). The
SConstructorP class is meant to be extended in Python and provides an
implementation of the Object[] versions of the methods in terms of the
PyObject versions (which the Python subclass defines). 

Python can call the "components" method which returns an Object[]
array because is converted into something appropriate by
Python. However, to implement the components method in Python, an
intermediary method is introduced in SConstructorP: "public abstract
PyObject components(PyObject pyobj)". This is the method that Python
subclasses of SConstructorP implement, and the "public Object[]
components method is defined in terms of it.


# If SPARK Strings are implemented as Python strings (PyString) why do
  we need class SString?

The SString, SList, SInteger and SFloat classes are there to provide
static methods for handling SPARK Strings, Lists, Integers and Floats
respectively. The creation, testing, and manipulation of SPARK core
values goes via the equivalent Java classes (SPARK List -> Java SList
etc.), even though these Java classes may not implement the SPARK
classes.


# How do I use the new Java classes from Java?

The com.sri.ai.jspark.values package has a public class Values with lots of static methods.

In general, since all of the core SPARK values are PyObjects, life is
much simpler if you use class PyObject to represent an arbitrary SPARK
object. For one thing, when crossing the SPARK/Java boundary,
PyObjects are left untouched, in constrast to Objects, which have all
sorts of processing done on them (PyString <-> String,
PyInteger<->Integer, ...).

Use append_value_str to append the SPARK-L syntax representation of a
PyObject to a StringBuffer.

Use value_str to get the SPARK-L syntax representation of a PyObject.

Use inverse_eval to get the SPARK construct that would evaluate to a
PyObject (if one exists).

To get a SPARK Symbol, String, Variable, Integer or Float, call the
appropriate public static method on the appropriate class:
SSymbol.getSymbol(String), SString.getString(String),
SInteger.getInteger(long), SFloat.getFloat(double). Note that what
SPARK calls Integers and Floats are Java longs and doubles.

To create a SPARK List, call the create(PyObject[], boolean),
create0(), create1(PyObject), create2(PyObject,PyObject), or
create3(PyObject,PyObject,PyObject) public static methods of
SList. The boolean in the first method states whether you should clone
the array - use false only if you are sure that noone else could ever
modify the array.

Don't be tempted to create PyTuples directly - SPARK Lists may not
always be implemented as PyTuples!

To create a SPARK Structure, you could call the
create(SSymbol,PyObject[], boolean), create0(SSymbol),
create1(SSymbol,PyObject), create2(SSymbol,PyObject,PyObject), or
create3(SSymbol,PyObject,PyObject,PyObject) public static methods of
SStructure or alternatively you could call the
structure(SSymbol,PyObject[], boolean), structure0(SSymbol),
structure1(SSymbol,PyObject), structure2(SSymbol,PyObject,PyObject),
or structure3(SSymbol,PyObject,PyObject,PyObject) public methods on
the functor SSymbol instance.

To test the type of a Variable or Symbol, use the isLocal(),
isCaptured, isTag(), isBrace() or isPrefix() method as appropriate.

Both SPARK Lists and SPARK Structures implement the List interface.

To test to see if something is one of the SPARK core data types, use
the isa(Object) method of the appropriate Java class, e.g.,
SInteger.isa(myobject).


# The persisted files are switchable between Java and Jython
  implementations. How is this done?

The functions to reconstruct the variant data types (Variables,
Symbols, and Structures) are defined in the one place, values.py. This
causes a bit of trouble, in the that __reduce__ methods which are
defined in other places need to reference these functions. When the
__reduce__ methods are defined in values_python.py, the problem is
that we need to avoid circular imports of modules and so cannot refer
to the reconstruction functions in values.py. When the __reduce__
methods are defined in Java files, the problem is that we need a
reference to objects from the Python world that may or may not exist
at Class initialization time. A way around this is by defining a
setUnpickleFunctions function/static method that can be used to insert
the function references in the appropriate spot.


# How do I test that the values code is working as expected?

There is a basicvalues_test.py in this directory that goes though a
number of tests, incluing conversion to and from Icl if you have the
OAA libraries available.  In your src directory run the following
command, twice, once with java mode true and once with java mode
false:

java -Dpython.home=<pythondirectory> -classpath "../lib/spark.jar:<pythondirectory>/jython.jar" -Djava.ext.dirs="../lib/oaa2.3.1" org.python.util.jython spark/internal/parse/basicvalues_test.py
