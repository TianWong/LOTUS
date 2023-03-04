from main import Interpreter

BASE_SCENARIO = './world/situation'

interpreter = Interpreter()
interpreter.execute(BASE_SCENARIO)


interpreter.cmdloop()