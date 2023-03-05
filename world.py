from main import Interpreter

BASE_SCENARIO = './world/test_situation'

interpreter = Interpreter()
interpreter.execute(BASE_SCENARIO)


interpreter.cmdloop()