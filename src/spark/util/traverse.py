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
#* "$Revision:: 129                                                       $" *#
#* "$HeadURL:: https://svn.ai.sri.com/projects/spark/trunk/spark/src/spar#$" *#
#*****************************************************************************#
from __future__ import generators
import weakref
from types import ListType, TupleType
from spark.internal.version import *
from spark.internal.parse.basicvalues import List, Integer, Structure, Symbol, Variable, value_str, PREFIX_PLUS_SYMBOL, PREFIX_MINUS_SYMBOL
from spark.internal.parse.expr import ExprVariable, ExprStructure, ExprStructureBrace, varsBeforeAndHere, keynameExpr
from spark.internal.parse.usages import *
from spark.internal.parse.usagefuns import *
from spark.internal.parse.processing import StandardExprBindings, Context
from spark.internal.exception import UnlocatedError, LocatedError
from spark.internal.common import ONE_SOLUTION, NO_SOLUTIONS
from spark.internal.repr.common_symbols import P_Do, P_NewFact, P_Achieve
from sets import *

INDENT_STRING = "    "
XML_HEADER = "<?xml version=\"1.0\"?>\n"
HTML_STYLE = "<head>\n<style>\n<!--\n#foldheader{cursor:pointer;cursor:hand ; font-weight:bold ;\nlist-style-image:url(http://www.qpq.org/fold.gif)}#foldinglist{list-style-image:url(http://www.qpq.org/list.gif)}\n//-->\n</style>\n<script language=\"JavaScript1.2\">\n<!--\n\nvar head=\"display:''\"\nvar ns6=document.getElementById&&!document.all\nvar ie4=document.all&&navigator.userAgent.indexOf(\"Opera\")==-1\n\nfunction checkcontained(e){\nvar iscontained=0\ncur=ns6? e.target : event.srcElement\ni=0\nif (cur.id==\"foldheader\")\niscontained=1\nelse\nwhile (ns6&&cur.parentNode||(ie4&&cur.parentElement)){\nif (cur.id==\"foldheader\"||cur.id==\"foldinglist\"){\niscontained=(cur.id==\"foldheader\")? 1 : 0\nbreak\n}\ncur=ns6? cur.parentNode : cur.parentElement\n}\n\nif (iscontained){\nvar foldercontent=ns6? cur.nextSibling.nextSibling : cur.all.tags(\"UL\")[0]\nif (foldercontent.style.display==\"none\"){\nfoldercontent.style.display=\"\"\ncur.style.listStyleImage=\"url(http://www.qpq.org/open.gif)\"\n}\nelse{\nfoldercontent.style.display=\"none\"\ncur.style.listStyleImage=\"url(http://www.qpq.org/fold.gif)\"\n}\n}\n}\nif (ie4||ns6)\ndocument.onclick=checkcontained\n//-->\n</script>\n</head>\n"
UL_TAG = "<ul id=\"foldinglist\" style=\"display:none\" style=&{head};>"
LI_TAG = "<li id=\"foldheader\">"
DOT_STYLE ={"action": "color=lightblue style=filled shape=box",
            "mainaction": "color=blue style=filled shape=box",
            "procedure": "color=green style=filled",
            "select": "shape=diamond fontsize=9",
            "others": "shape=ellipse, width=.3, height=.2  fontsize=9"}

def noneRef():
    return None

def generateUnwantedList(input):
    if isinstance(input, TupleType) or isinstance(input, ListType):
        return tuple(input)
    f = file(input)
    lines = f.readlines()
    f.close()
    return tuple([l.strip() for l in lines])

#==============================
class ExecNode(object):
    __slots__ = (
    "id",
    "name",
    "fullname",
    "attribs",
    "children",
    )
        
    def __init__(self, name, fullname = "", attribs = {}, children = []):
        self.name = name
        self.attribs = attribs
        self.children = children
        self.fullname = fullname
        self.id = -1
        
    def getTag(self):
        if self.name in ("mainaction", "action", "procedure"):
            return self.fullname
        else:
            return "%s%s"%(self.name, self.id)

    def getLabel(self):
        if self.name in ("mainaction", "action", "procedure"):
            return self.fullname[self.fullname.rfind(".")+1:]
        else:
            return self.name
        
    def removeUnnecessaryLeaves(self):
        unnecessary = []
        for child in self.children:
            if not child.name in ("action", "procedure", "EXPANDED"):
                if not child.children:
                    unnecessary.append(child)
        for un in unnecessary:
            self.children.remove(un)
        for child in self.children:
            child.removeUnnecessaryLeaves()

    def removeUnnecessaryNodes(self):
        TAGS_TO_IGNORE = ("fail", "succeed", "context", "set", "retract", "retractall")
        unnecessary = []
        for child in self.children:
            if child.name in TAGS_TO_IGNORE:
                unnecessary.append(child)
            else:
                child.removeUnnecessaryNodes()
            if not (child.name in ("action", "procedure", "EXPANDED") or child.children):
                unnecessary.append(child)
        for un in unnecessary:
            if un in self.children: self.children.remove(un)

    def removeLibraryActions(self):
        SPARK_ACTIONS = ("spark.lang", "spark.io", "spark.net", "spark.pylang", "spark.tests", "spark.ui", "spark.lang", "spark.util")
        unnecessary = []
        for child in self.children:
            if child.name == "action":
                for sAction in SPARK_ACTIONS:
                    if child.fullname.startswith(sAction):
                        unnecessary.append(child)
        for un in unnecessary:
            if un in self.children: self.children.remove(un)
        for child in self.children:
            child.removeLibraryActions()

    def removeUnwantedNodes(self, unwanted):
        unnecessary = []
        for child in self.children:
            if child.name == "action" and child.fullname in unwanted:
                unnecessary.append(child)
        for un in unnecessary:
            if un in self.children: self.children.remove(un)
        for child in self.children:
            child.removeUnwantedNodes(unwanted)


    def getTree(self, detail=2):
        children = [child.getTree(detail) for child in self.children]
        if detail == 2:
            att = ", ".join([key+"="+self.attribs[key] for key in self.attribs.keys()])
            att = att.replace("\n","\\n").replace("\t","\\t").replace("\r","\\r")
        elif detail == 1:
            att = self.fullname
        elif detail == 0:
            if self.fullname.rfind(".") == -1:
                att = ""
            else:
                att = self.fullname[self.fullname.rfind(".")+1:]
        else:
            raise Exception("Wrong number for detail.")
        str = "%s  %s\n"%(self.name, att)
        ind = " "
        totalKids = len(children)
        if totalKids > 0:
            for i in range(totalKids-1):
                child = children[i]
                str = str + ind + " |\n"
                lines = child.split("\n")
                firstLine = True
                for line in lines:
                    if not line: continue
                    if firstLine: 
                        x = "+"
                    else:
                        x = "|"
                    firstLine = False
                    str = str + ind + " " + x + line + "\n"
            child = children[totalKids-1]
            str = str + ind + " |\n"
            lines = child.split("\n")
            firstLine = True
            for line in lines:
                if not line: continue
                if firstLine: 
                    x = "+"
                else:
                    x = " "
                firstLine = False
                str = str + ind + " " + x + line + "\n"   
        return str
        
    def getXML(self, level = 0):
        str = ""
        ind = "".join([INDENT_STRING for i in range(level)])
        if self.children: 
            endStr = ""
            endTag = "%s</%s>\n"%(ind, self.name)
        else:
            endStr = "/"
            endTag = ""
        att = ""
        for key in self.attribs.keys():
            att = att + " " + key + "='" + self.attribs[key] + "'"
        att = att.replace("\n","\\n").replace("\t","\\t").replace("\r","\\r")
        str = str + "%s<%s%s%s>\n"%(ind, self.name, att, endStr)
        for child in self.children:
            str = str + child.getXML(level+1)
        str = str + endTag
        if level == 0:
            str = XML_HEADER + str
        return str
            
    def getHTML(self, level = 0):
        ind = "".join([INDENT_STRING for i in range(level)])
        name = self.name
        if name in ("action", "mainaction"):
        	name = "<font COLOR=\"#007F00\">%s</font>"%"action"
        elif self.name == "procedure":
        	name = "<font COLOR=\"#0000FF\">%s</font>"%self.name
        else:
        	name = self.name
        if self.children:
            str = "%s%s<b>%s</b> %s</li>\n"%(ind, LI_TAG, name, self.fullname)
        else:
            str = "%s<li><b>%s</b> %s</li>\n"%(ind, name, self.fullname)
        if self.children: 
            str = str + "%s%s\n"%(ind, UL_TAG)
            for child in self.children:
                str = str + child.getHTML(level+1)
            str = str + "%s</ul>\n"%ind
        if level == 0:
            title = "<title>%s</title>\n"%self.fullname
            str = "<html>\n" + title + HTML_STYLE + "<body>\n<ul>\n" + str + "\n</ul>\n</body>\n</html>\n"
        return str

    def __generateEdges(node, edges, definition):
        global DOT_STYLE
        name = node.name
        tag = node.getTag()
        label = node.getLabel()
        if definition.has_key(tag): return (edges, definition) #already added
        if name in ("action", "mainaction"):
            #print "node.children: %s"%(node.children,)
            style = ""
            grandchildren = ()
            if node.children:
                child = node.children[0] # may be an "or"
                if child.name == "or": # there is more than one procedure
                    style = "[style=dashed]"
                    grandchildren = child.children
                else: # only one procedure, so there is no "or" node.
                    grandchildren = (child,)
                for grandchild in grandchildren:
                    edge = (tag, grandchild.getTag(), style, True)
                    if not edge in edges: edges.append(edge)
                    (edges, definition) = grandchild.__generateEdges(edges, definition)
        elif name == "procedure":
            index = 1
            for child in node.children:
                #if child.name == "EXPANDED": continue
                edge = (tag, child.getTag(), "[label=\"%s\"]"%index, True)
                index = index + 1
                if not edge in edges: edges.append(edge)
                (edges, definition) = child.__generateEdges(edges, definition)
        elif name == "select":
            for child in node.children:
                for grandchild in child.children:              
                    edge = (tag, grandchild.getTag(), "[style=dashed]", False)
                    if not edge in edges: edges.append(edge)
                    (edges, definition) = grandchild.__generateEdges(edges, definition)
        elif name == "wait":
            if node.children:
                if node.children[0].children:
                    edge = (tag, node.children[0].children[0].getTag(), "", True)
                    if not edge in edges: edges.append(edge)
        else:
            index = 1
            for child in node.children:      
                edge = (tag, child.getTag(), "[label=\"%s\"]"%index, False)
                index = index + 1
                if not edge in edges: edges.append(edge)
                (edges, definition) = child.__generateEdges(edges, definition)

        if not definition.has_key(tag):
            if DOT_STYLE.has_key(name):
                style = DOT_STYLE[name]
            else:
                style = DOT_STYLE["others"]
            definition[tag] = "[%s label=\"%s\"]"%(style, label)

        return (edges, definition)


    def __generateID(node, id = 0):
        node.id = id
        id = id + 1
        for child in node.children:
            id = child.__generateID(id)
        return id

    def getDOT(self):
        self.__generateID()
        (edges, definition) = self.__generateEdges([], {})
        str = ""
        edges.sort()
        for key in definition.keys():
            if key.startswith("EXPANDED"): continue
            str = str + "\"%s\" %s;\n"%(key, definition[key])
        for edge in edges:
            if edge[1].startswith("EXPANDED"): continue
            str = str + "\"%s\" -> \"%s\" %s;\n"%(edge[0],edge[1],edge[2])                 
        str = "digraph G {\n" + str + "}\n"
        return str

    def __str__(self):
        return self.name
    
#==============================

class Inst(object):
    __slots__ = (
        "__weakref__",
        "_parentRef",
        "expr",
        "expandable",
        "level",
        )
        
    theAgent = None
    
    def __init__(self, parent, expr, level=0):
        self.expr = expr
        if parent is None:
            self._parentRef = noneRef
        else:
            self._parentRef = weakref.ref(parent)
        self.level = level
        self.expandable = True
        
    def getParent(self):
        return self._parentRef()

    def getName(self):
        return "tag"
    
    def getFullName(self):
        # Returns a fullname information about the object
        return ""
    
    def getAttributes(self):
        return {}

    def getParent(self):
        return self._parentRef()

    parent = property(getParent)

    def getNode(self, depth):
        if depth <= 0:
            return ExecNode(self.getName(), self.getFullName())
        kids = [child.getNode(depth-1) for child in self.calcChildren()]
        return ExecNode(self.getName(), self.getFullName(), self.getAttributes(), kids)

    def calcChildren(self):
        "Get children of self"
        raise Unimplemented()
    
    def __repr__(self):
        return self.__str__()

class Interface(Inst):
    """An Interface corresponds to a task or choice the agent must make.
    The children of an Interface are Units that express alternative ways that
    the task is performed or the choice is made.
    An Interface acts as a link between variables in a parent Unit and
    the corresponding variables in each of the child Units.
    The parameters of an Interface are the actual parameters from the parent Unit.
    """
    __slots__ = ()
        
    def __str__(self):
        parent = self.getParent()
        if parent is None:
            prefix = ""
        else:
            prefix = "%s.%d."%(parent, parent.children.index(self))
        return "%s%s"%(prefix, self.getSuffix())

    def getSuffix(self):
        return self.__class__.__name__

    def childUpdated(self, child):
        self._calcValues()
            

class Unit(Inst):
    """A Unit corresponds to a procedure instance (or a part of one).
    It has variables and constraints between those variables.
    The parameters of a Unit are the formal parameter variables.
    The children of a Unit are Interfaces representing subtasks or choices.
    """

    __slots__ = ()

    def getName(self):
        return str(self.getPrefix())
        
    def __init__(self, parent, expr, level):
        Inst.__init__(self, parent, expr, level)

    def __str__(self):
        return "%s"%self.getPrefix()

    def getPrefix(self):
        return self.__class__.__name__
        
################

    def _calcChildren(self, expr):       # expr = [...]
        for task in expr:
            impKey = task.impKey
            try:
                id = impKey.id
            except AttributeError:
                raise LocatedError(expr, "Cannot process expression")
            if id == "do:":
                yield DoTaskInterface(self, task, self.level+1)
            elif id == "seq:" or id == "parallel:":
                for subtask in task:
                    for child in self._calcChildren(subtask):
                        yield child
            elif id == "try:":
                yield TryUnit(self, task, self.level+1)
            elif id == "wait:":
                yield WaitInterface(self, task, self.level+1)
            elif id == "select:":
                yield SelectInterface(self, task, self.level+1)
            elif id == "succeed:" or id == "fail:":
                yield SucceedFailInterface(self, task, self.level+1)
            elif id == "context:" or id == "retract:" or id == "retractall:":
                yield ConditionInterface(self, task, self.level+1)
            elif id == "conclude:":
                yield ConcludeInterface(self, task, self.level+1)
            elif id == "achieve:":
                yield AchieveInterface(self, task, self.level+1)
            elif id == "set:":
                yield SetInterface(self, task, self.level+1)
                expr = task[1]
            elif id == "forall:" or id == "forallp:" or id == "while:" or id=="forin:":
                yield LoopUnit(self, expr, self.level+1)
            else:
                if not (False): raise AssertionError, \
                   "Cannot handle %r"%expr

    ################
        
class TryUnit(Unit):
    """A Unit corresponding to one procedure (instance?) for a task.
    self.expr is the closed expr of the ProcedureValue.
    """
    __slots__ = ()

    def __init__(self, parent, expr, level):
        Unit.__init__(self, parent, expr, level)
        
    def calcChildren(self):
        for subtask in self.expr:
            for child in self._calcChildren(subtask):
                yield child
        
    def getPrefix(self):
        return "try"

class ProcedureUnit(Unit):
    """A Unit corresponding to one procedure (instance?) for a task.
    self.expr is the closed expr of the ProcedureValue.
    """
    __slots__ = ("name",)

    def __init__(self, parent, procedureValue, level):
        expr = procedureValue.closed_zexpr
        Unit.__init__(self, parent, expr, level)
        self.name = str(self.expr[0].resolvedSymbol)
        
    def calcChildren(self):
        return self._calcChildren(self.expr.keyget0("body:"))
        
    def getPrefix(self):
        return "procedure"
        
    def getFullName(self):
        return self.name

    def getAttributes(self):
        at = {}
        at["name"] = self.name
        return at

    def getNode(self, depth):
        if depth <= 0:
            return ExecNode(self.name, self.getFullName())
        alreadyExpanded = False
        parent = self.getParent()
        while parent:
            if isinstance(parent, ProcedureUnit):
                if parent.name == self.name:
                    alreadyExpanded = True
                    break
            parent = parent.getParent()
        if alreadyExpanded:
            kids = [ExecNode("EXPANDED"),]
        else:
            kids = [child.getNode(depth-1) for child in self.calcChildren()]
        return ExecNode(self.getName(), self.getFullName(), self.getAttributes(), kids)
 
class SelectUnit(Unit):
    """A Unit corresponding to one alternative of a select/wait choice.
    self.expr is the task expression.
    """
    __slots__ = ("impKey",)
           
    def __init__(self, parent, expr, impKey, level):
        Unit.__init__(self, parent, expr, level)
        self.impKey = impKey

    def getName(self):
        return "or"
        
    def calcChildren(self):
        return [ProcedureUnit(self, pv, self.level+1) for pv in procedureValues(Inst.theAgent, self.impKey, P_Do)]


class ChoiceUnit(Unit):
    """A Unit corresponding to one alternative of a select/wait choice.
    self.expr is the task expression.
    """
    __slots__ = ("condition",)
     
    def __init__(self, parent, expr, condition, level):
        Inst.__init__(self, parent, expr, level)
        self.condition = condition
        
    def getName(self):
        return "choice"
    
    def getFullName(self):
        return str(self.condition)

    def getAttributes(self):
        at = {}
        at["condition"] = str(self.condition)
        return at        
        
    def calcChildren(self):
        return self._calcChildren(self.expr)

    def getPrefix(self):
        return self.expr.functor

class DoTaskInterface(Interface):
    """A DoTaskInterface is an Interface corrsponding to the execution of a basic task.
    self.expr is the do: Expr.
    """
    __slots__ = ()

    def getName(self):
        return "action"

    def getFullName(self):
        return str(Inst.theAgent.getDecl(self.expr[0].resolvedSymbol).asSymbol())
    
    def getAttributes(self):
        at = {}
        at["body"] = str(self.expr[0])
        return at        
   
    def calcChildren(self):
        impKey = self.expr[0].impKey
        kids = [ProcedureUnit(self, pv, self.level+1) for pv in procedureValues(Inst.theAgent, impKey, P_Do)]
        if len(kids)>=2:
            kids = [SelectUnit(self, self.expr, impKey, self.level+1),]
        return kids


    def getSuffix(self):
        return self.expr[0].functor

class LoopUnit(Unit):
    """A LoopInterface is an Interface corrsponding to the execution of a loop task (forall, forallp, while).
    self.expr is the body of the loop
    """
    __slots__ = ()
        
    def getName(self):
        return self.__str__()
    
    def getFunctor(self):
        return str(self.expr[0].functor)[0:-1]
        
    def getFullName(self):
        if self.getFunctor() == "forin":
            return str(self.expr[0][1])            
        return str(self.expr[0][1])        
        
    def getAttributes(self):
        at = {}
        if self.getFunctor() == "forin":
            at["variable"] = str(self.expr[0][0])
            at["list"] = str(self.expr[0][1])            
        else: 
            at["variables"] = str(self.expr[0][0])
            at["condition"] = str(self.expr[0][1])
        return at        
    
    def calcChildren(self):
        return self._calcChildren(self.expr[0][2])
 
    def getSuffix(self):
        return self.expr[0].functor
    
    def __str__(self):
        return str(self.getSuffix())[0:-1]

class RootTask(Interface):
    __slots__ = (
        "impKey",
        "action"
        )
    def __init__(self, agent, actionName):
        self.impKey = Symbol(actionName)
        self.action = actionName
        Inst.theAgent = agent
        Interface.__init__(self, None, None, 0)
        
    def getName(self):
        return "mainaction"
    
    def getFullName(self):
        return self.action
    
    def getAttributes(self):
        at = {}
        at["body"] = str(self.action)
        return at        
        
    def calcChildren(self):
        kids = [ProcedureUnit(self, pv, self.level+1) for pv in procedureValues(Inst.theAgent, self.impKey, P_Do)]
        if len(kids)<2:
            return kids
        else:
            return [SelectUnit(self, self.expr, self.impKey, self.level+1),]

    def getSuffix(self):
        return self.impKey.id

class SelectInterface(Interface):
    """A SelectInterface is an interface corresponding to a select within a procedure.
    self.expr if the select: or wait: Expr.
    self.parameters lists the variables used both inside and outside the choice.
    """
    __slots__ = ()
        
    def getName(self):
        return self.getSuffix()
        
    def calcChildren(self):
        expr = self.expr
        for index in range(0, len(expr), 2):
            choiceAlternative = ChoiceUnit(self, expr[index+1], expr[index+0], self.level+1)
            #for i in range(0, index, 2):
            #    choiceAlternative.addPredFalseConstraint(expr[i])
            yield choiceAlternative

    def getSuffix(self):
        return "select"

class WaitInterface(Interface):
    """A WaitInterface is an interface corresponding to a wait within a procedure.
    self.expr if the select: or wait: Expr.
    self.parameters lists the variables used both inside and outside the choice.
    """
    __slots__ = ()
        
    def getName(self):
        return self.getSuffix()
        
    #def getFullName(self):
    #    return self.action        
        
    def calcChildren(self):
        expr = self.expr
        for index in range(0, len(expr), 2):
            choiceAlternative = ChoiceUnit(self, expr[index+1], expr[index+0], self.level+1)
            #for i in range(0, index, 2):
            #    choiceAlternative.addPredFalseConstraint(expr[i])
            yield choiceAlternative

    def getSuffix(self):
        return "wait"


class SucceedFailInterface(Interface):
    """A SucceedFailInterface is an interface corresponding to a succeed or fail within a procedure.
    self.expr if the select: or wait: Expr.
    self.parameters lists the variables used both inside and outside the choice.
    """
    __slots__ = ()
    
    def __init__(self, parent, expr, level):
        Inst.__init__(self, parent, expr, level)
        self.expandable = False
        
    def getName(self):
        return self.getSuffix()   
        
    def calcChildren(self):
        return ()

    def getSuffix(self):
        return str(self.expr.functor)[0:-1]

class AchieveInterface(Interface):
    """A AchieveInterface is an interface corresponding to an achieve within a procedure.
    self.expr if the select: or wait: Expr.
    self.parameters lists the variables used both inside and outside the choice.
    """
    __slots__ = ()

    def __init__(self, parent, expr, level):
        Inst.__init__(self, parent, expr, level)
        self.expandable = False
        
    def getName(self):
        return self.getSuffix()
    
    def getFullName(self):
        return str(self.expr[0].resolvedSymbol)
    
    def getAttributes(self):
        at = {}     
        at["condition"] = str(self.expr[0])
        return at
        
    def calcChildren(self):
        impKey = self.expr[0].impKey
        kids = [ProcedureUnit(self, pv, self.level+1) for pv in procedureValues(Inst.theAgent, impKey, P_Achieve)]
        if len(kids)<2:
            return kids
        else:
            return [SelectUnit(self, self.expr, impKey, self.level+1),]

    def getSuffix(self):
        return str(self.expr.functor)[0:-1]

class ConcludeInterface(Interface):
    """A ConcludeInterface is an interface corresponding to a conclude within a procedure.
    self.expr if the select: or wait: Expr.
    self.parameters lists the variables used both inside and outside the choice.
    """
    __slots__ = ()

    def __init__(self, parent, expr, level):
        Inst.__init__(self, parent, expr, level)
        self.expandable = False
        
    def getName(self):
        return self.getSuffix()
    
    def getFullName(self):
        return str(self.expr[0].resolvedSymbol)
    
    def getAttributes(self):
        at = {}
        at["condition"] = str(self.expr[0])
        return at
        
    def calcChildren(self):
        return [ProcedureUnit(self, pv, self.level+1) for pv in procedureValues(Inst.theAgent, self.expr[0].impKey, P_NewFact)]

    def getSuffix(self):
        return str(self.expr.functor)[0:-1]

class ConditionInterface(Interface):
    """A ConditionInterface is an interface corresponding to a context, retract, or retractall within a procedure.
    self.expr if the select: or wait: Expr.
    self.parameters lists the variables used both inside and outside the choice.
    """
    __slots__ = ()

    def __init__(self, parent, expr, level):
        Inst.__init__(self, parent, expr, level)
        self.expandable = False
        
    def getName(self):
        return self.getSuffix()
    
    def getFullName(self):
        if self.getSuffix() == "retractall":
            return str(self.expr[1].resolvedSymbol)
        return str(self.expr[0].resolvedSymbol)
    
    def getAttributes(self):
        at = {}     
        if self.getSuffix() == "retractall":
            at["condition"] = str(self.expr[1])
        else:
            at["condition"] = str(self.expr[0])
        return at
        
    def calcChildren(self):
        return ()

    def getSuffix(self):
        return str(self.expr.functor)[0:-1]

class SetInterface(Interface):
    """A SetInterface is an interface corresponding to a set within a procedure.
    self.expr if the select: or wait: Expr.
    self.parameters lists the variables used both inside and outside the choice.
    """
    __slots__ = ()

    def __init__(self, parent, expr, level):
        Inst.__init__(self, parent, expr, level)
        self.expandable = False
        
    def getName(self):
        return self.getSuffix()
    
    def getFullName(self):
        return str(self.expr[0])
    
    
    def getAttributes(self):
        at = {}     
        at["variable"] = str(self.expr[0])
        at["value"]    = str(self.expr[1])
        return at

    def calcChildren(self):
        return ()

    def getSuffix(self):
        return "set"

################################################################
# Tools 

def procedureValues(agent, impKey, symbol):
    facts = agent.factslist1(symbol, agent.getDecl(impKey).asSymbol())
    #if not (facts): raise AssertionError, \
    #    "There are no procedures for action %s"%impKey
    return [fact[1] for fact in facts]
