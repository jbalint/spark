from spark import main
from spark.main import init
from spark.internal.debug.debugger import execute_spark_main, dispose, get_modname
from spark.internal.parse.processing import get_default_module

import string

#TODO: There probably is a better way to do this
#####unit test success/failure tracking#####
success = {}
failure = {}
def isSuccessful(name):
    if success.has_key(name):
        return success[name]
    else:
        return None
def failMessage(name):
    if failure.has_key(name):
        return failure[name]
    else:
        return None
    
def setSuccess(name):
    success[name] = True
    failure[name] = None
    return 1
def setFail(name, reason):
    success[name] = False
    failure[name] = reason
    return 1

#####Unit test loading/running/cleanup#####
def initTest(mod):
    success = {}
    failure = {}
    main.defaultModule = mod
    init_result = init(None, (True, False, False, "./persist"))
def endTest():
    dispose(main.runAgent)
def unitTest(cmd):
    err = run_cmd(main.runAgent, cmd)
    return err
def run_cmd(agent, cmd):
    mod = get_default_module()
    if mod is None:
        return "Module %s not found"%mod.filename
    main = mod.main_name
    if main is None:
        return "Module %s main not found"%mod.filename
    try:
        ext = agent.run(cmd, get_modname())
        x = ext.wait_result()
    except Exception, e:
        print "Test in %s failed to execute"%mod.filename
        return e
    #all okay
    return None

def test(name, args=None):  
    from spark.tests.unit import isSuccessful, failMessage
    if args is not None:
        strArgs = string.join(args, "\" \"")
        cmd = "[do: ("+name+" \""+strArgs+"\")]"
        print cmd
    else:
        cmd = "[do: ("+name+" \"foo\")]"
        
    err = unitTest(cmd)
    if err is not None:
        return "Test",name,"aborted.  Reason:", err.message
    elif isSuccessful(name):
        return 0
    else:
        return failMessage(name)

class nobuffer:
    """Flushes a file stream every time a write is called"""
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

if __name__ == "__main__":
    #Testing unit tests
    import sys
    sys.stdout = nobuffer(sys.stdout)

    module = "spark.tests.forin_test"
    initTest(module)
    
    test("unit_forin_test", None)
    module = "spark.tests.sampler_test"
    initTest(module)
    test("unit_sampler_test1", None)
    test("unit_sampler_test2", None)
    test("unit_sampler_test3", None)
    test("unit_sampler_test4", None)
    test("unit_sampler_test5", None)
    test("unit_sampler_test6", None)
    test("unit_sampler_test7", None)
    test("unit_sampler_test8", None)
    test("unit_sampler_test9", None)
    test("unit_sampler_test10", None)
    module = "spark.tests.test_simpleimp"
    initTest(module)
    test("unit_simpleimp_test1", None)
    test("unit_simpleimp_test2", None)
    test("unit_simpleimp_test3", None)
    test("unit_simpleimp_test4", None)
    test("unit_simpleimp_test5", None)
    test("unit_simpleimp_test6", None)
    module = "spark.tests.determined_test"
    initTest(module)
    test("unit_determined_test", None)
    module = "spark.tests.parallel_test"
    initTest(module)
    test("unit_parallel_test1", None)
    test("unit_parallel_test2", None)
    module = "spark.tests.list_test"
    initTest(module)
    test("unit_list_elements", None)
    test("unit_list_index", None)
    test("unit_list_length", None)
    test("unit_list_concat", None)
    test("unit_list_empty", None)
    test("unit_list_slice", None)
    module = "spark.tests.meta_test"
    initTest(module)
    cmd = """    [seq:
      [conclude: (Debug "meta")]
      [context: (CurrentEvent $task)]
      [context: (CurrentTFrame $pi)]
      [context: (ProcInstSymbol $pi Meta_Unit_Tests)
            "ProcInstSymbol failed to get the correct procedure symbol"]
    ]"""
    unitTest(cmd)
    test("unit_mygoal", None)
    test("unit_mygoal_xg", None)
    test("unit_mygoal_xb", None)
    test("unit_mygoal_xg1", None)
    test("unit_mygoal_xb1", None)
    test("unit_mygoal_tasknm", None)
    cmd = "[retract: (Debug \"meta\")]"
    unitTest(cmd)
    
    module = "spark.tests.unit"
    initTest(module)
    test("unit_assert_succeed", None)
    test("unit_assert_succeed1", None)
    test("unit_assert_fail", None)
    test("unit_assert_bound", None)
    test("unit_assert_pred", None)

    endTest()
    sys.exit(0)