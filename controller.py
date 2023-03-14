import os
from lotus_configurator import Lotus_configurator
from main import Interpreter

BASE_SCENARIO = './world/ca_gb.lotus'

def run_scenario(base_scenario, config: Lotus_configurator):
    if os.path.isfile(base_scenario):
      with open(base_scenario, 'r') as in_file:
          execution_lines = in_file.read().split('\n')
    interpreter = Interpreter()
    interpreter.execute(execution_lines)
    interpreter.do_addAllASInit("")
    interpreter.do_run("")
    

    attack = config.gen_attack()
    aspa_config = config.gen_aspa(interpreter)

    # add ASPA/ASPV configuration
    interpreter.execute(aspa_config)
    interpreter.do_run("")
    
    # add attack from attack_generator
    interpreter.execute(attack)
    interpreter.do_run("diff")

    print(f"aspa_config: {aspa_config}\nattack: {attack}\n")
    updates = interpreter.run_updates
    for idx, val in enumerate(updates):
        old, new = val
        print(f"change {idx}\nold: {old}\nnew: {new}\n")
    # import code
    # code.interact(local=locals())
    return interpreter

if __name__ == "__main__":
    config = Lotus_configurator()
    interpreter = run_scenario(BASE_SCENARIO, config)
    import code
    code.interact(local=locals())