from spark.internal.version import *
from spark.internal.parse.basicvalues import Symbol, Structure, isList, isString, List, isStructure
from spark.internal.common import DEBUG
from spark.internal.exception import LowError


debug = DEBUG(__name__)#.on()

__all__ = ["isMap", "mapChange", "mapGetPred", "mapGet", "mapDict", "mapKeys", "dictMap", "mapCreate"]

################################################################
# SPARK map handling functions

################################################################
# Routines for accessing fields of a map structure.

def isMap(map):
    if not isStructure(map):
        return False
    for elt in map:
        if (not isStructure(elt) or
            len(elt) != 1 or
            not elt.functor.name.endswith(":")):
            return False
    return True

def mapChange(map, *keysAndValues):
    d = mapDict(map)
    if d == None:
        raise LowError("Non-map passed to mapChange")
    numKeysAndValues = len(keysAndValues)
    if numKeysAndValues%2:
        raise LowError("mapChange takes an odd number of arguments")
    for index in range(0, numKeysAndValues-1, 2):
        key = keysAndValues[index]
        if not isString(key):
            raise RuntimeException("mapChange keys must be Strings")
        val = keysAndValues[index+1]
        d[key] = val
    return dictMap(d)

def mapGetPred(map, *keysAndValues):
    if not isMap(map):
        raise RuntimeException("First argument to MapGet must be a map")
    result = list(keysAndValues)
    for index in range(0, len(result)-1, 2):
        key = result[index]
        if key == None:
            raise RuntimeException("Must have bound values for keys in MapGet")
        if isString(key):
            default = None
        elif isList(key) and len(key) == 2 and isString(key[0]):
            default = key[1]
            key = key[0]
        else:
            raise RuntimeException("Each MapGet key must be a String or a List of a String and a default value")
        val = mapGet(map, key)
        if val == None:                 # key isn't found
            if default == None:
                return None
            else:
                val = default
        if result[index+1] == None:   # No value specified
            result[index+1] = val
        elif result[index+1] != val:    # Incorrect value specified
            return None
    if len(result)%2 != 0:              # odd number of arguments
        key = result[-1]
        if key == None:
            raise RuntimeException("Final MapGet key must be supplied")
        if not isString(key):
            raise RuntimeException("Final MapGet key must be a String")
        if mapGet(map, key) == None:         # specified key is not present
            return None
    return result

_TYPE = "_type_"

def mapGet(map, key):
    "Return the value found for the given key in the map or None if not found"
    if isStructure(map):
        if key == _TYPE:
            return map.functor.name
        lenKey1 = len(key) + 1
        for kv in map:
            if isStructure(kv):
                k = kv.functor.name
                if len(k) == lenKey1 and k.startswith(key) and k.endswith(":"):
                    return kv[0]
            else:
                raise LowError("Not a valid map")
        return None
    elif isList(map) and len(map) == 2 and len(map[0]) == len(map[1]): # allows for old list of lists format
        for index, keyi in enumerate(map[0]):
            if keyi == key:
                return map[1][index]
        return None
    else:
        raise LowError("Not a valid map")
        
    
_MAP_FUNCTOR = Symbol("")

def _identity(x):
    return x

def mapDict(map, fun=_identity):
    "Convert a map to a dict (appying fun to each component except the type), return None if it isn't a proper map"
    fname = map.functor.name
    if fname == _MAP_FUNCTOR.name:
        d = {}
    else:
        d = {_TYPE:fname}
    for keyval in map:
        if not isStructure(keyval) or len(keyval) != 1:
            break
        fname = keyval.functor.name
        if not fname.endswith(":"):
            break
        d[fname[:-1]] = fun(keyval[0])
    else:                           # reached end of args
        return d
    return None

def mapKeys(map):
    return List(mapDict(map).keys())

def dictMap(d, fun=_identity):
    "Convert a dict to a map (appying fun to each component except the type)."
    fname = d.get(_TYPE)
    items = d.items()
    items.sort()
    args = [Symbol(k+":").structure(fun(v))
            for (k, v) in items
            if k != _TYPE]
    if fname == None:
        return Structure(_MAP_FUNCTOR, args)
    else:
        return Structure(Symbol(fname), args)

def mapGen(*args):
    if len(args)%2 != 0:
        raise LowError("You must have an even number of positional arguments for mapCreate")
    return dictMap(dict(zip(args[0::2], args[1::2])))
    
def mapCreate(**keyargs):
    return dictMap(keyargs)
    

################################################################
