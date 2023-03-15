import os
import random
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

    attack = config.gen_attack()
    aspa_config = config.gen_aspa()

    # add ASPA/ASPV configuration
    interpreter.execute(aspa_config)
    interpreter.do_run("")
    
    # add attack from attack_generator
    interpreter.execute(attack)
    interpreter.do_run("diff")

    print(f"aspa_config: {aspa_config}\nattack: {attack}\n")
    updates = interpreter.run_updates
    changes = 0
    for idx, val in enumerate(updates):
        old, new = val
        print(f"change {idx}\nold: {old}\nnew: {new}\n")
        changes += 1
    return changes

if __name__ == "__main__":
    all_asns = []
    with open(BASE_SCENARIO, 'r') as infile:
        data = infile.read()
        for line in data.split('\n'):
            if line.startswith('addAS '):
                all_asns.append(int(line[6:]))
    
    with_aspa_changes = 0
    without_aspa_changes = 0
    seed = 0
    for _ in range(5):
        p = Pool(2)
        configs = [(BASE_SCENARIO, Lotus_configurator(0,0,all_asns,seed)), (BASE_SCENARIO, Lotus_configurator(1,0,all_asns,seed))]
        changes = p.starmap(run_scenario, configs)
        with_aspa_changes += changes[0]
        without_aspa_changes += changes[1]
        seed += 1
    print(f'Routes changed with ASPA: {with_aspa_changes}')
    print(f'Routes changed without ASPA: {without_aspa_changes}')