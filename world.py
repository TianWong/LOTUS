from main import Interpreter

BASE_SCENARIO = './world/sample_situation'

interpreter = Interpreter()
interpreter.execute(BASE_SCENARIO)

# interpreter.do_import("./experiment/jpnic_network.yml")
# interpreter.do_addAllASInit("")
# interpreter.do_run("")
# interpreter.do_genAttack("24280 38629")
# interpreter.do_run("diff")

print(interpreter.run_updates)

# interpreter.cmdloop()
import code
code.interact(local=locals())