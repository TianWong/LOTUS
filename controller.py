import os
from lotus_configurator import Lotus_configurator
from main import Interpreter
from multiprocessing import Pool

BASE_SCENARIO = './world/ranked_ca_gb.lotus'

def run_scenario(base_scenario, config: Lotus_configurator):
    if os.path.isfile(base_scenario):
      with open(base_scenario, 'r') as in_file:
          execution_lines = in_file.read().split('\n')
    interpreter = Interpreter()
    interpreter.execute(execution_lines)
    interpreter.do_addAllASInit("")
    interpreter.do_run("")
    

    attack = config.gen_attack(0, ["CA", "GB"])
    aspa_config = config.gen_aspa()

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

if __name__ == "__main__":
    p = Pool(2)
    configs = [(BASE_SCENARIO, Lotus_configurator(0,0)), (BASE_SCENARIO, Lotus_configurator(1,0))]
    p.starmap(run_scenario, configs)