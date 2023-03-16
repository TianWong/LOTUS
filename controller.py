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

    aspa_config, attack = config.gen_situation()

    # add ASPA/ASPV configuration
    interpreter.execute(aspa_config)
    interpreter.do_run("")
    
    # add attack from attack_generator
    interpreter.execute(attack)
    interpreter.do_run("diff")

    updates = interpreter.run_updates
    # changes = 0
    # for idx, val in enumerate(updates):
    #     old, new = val
    #     print(f"change {idx}\nold: {old}\nnew: {new}\n")
    #     changes += 1
    # return changes
    return len(updates)

if __name__ == "__main__":
    all_asns = []
    with open(BASE_SCENARIO, 'r') as infile:
        data = infile.read()
        for line in data.split('\n'):
            if line.startswith('addAS '):
                all_asns.append(int(line[6:]))
    
    p = Pool(6)
    seed = random.random()
    configs = []
    percentages = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
    for i in percentages:
        configs.append((BASE_SCENARIO, Lotus_configurator(1,all_asns,seed=seed,aspa_rate=i)))
    
    changes = p.starmap(run_scenario, configs)
    for idx, num in enumerate(changes):
        print(f"{percentages[idx]}% aspa:\t\t{num} changes")