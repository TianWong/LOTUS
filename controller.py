import copy
import os
import pickle
import random

import pandas as pd
import numpy as np
from lotus_configurator import Lotus_configurator as lc
from main import Interpreter
from multiprocessing import Pool

BASE_SCENARIO = './world/ranked_ca_gb.lotus'

def run_base(base_scenario):
    if os.path.isfile(base_scenario):
      with open(base_scenario, 'r') as in_file:
          execution_lines = in_file.read().split('\n')
    interpreter = Interpreter()
    interpreter.execute(execution_lines)
    interpreter.do_addAllASInit("")
    interpreter.do_run("")
    return interpreter

def init_interpreter(interp_attributes):
    i = Interpreter()
    i.as_class_list, i.connection_list, i.public_aspa_list, i.run_updates = interp_attributes
    return i

def run_scenario(interp_attributes, config: lc):
    interpreter = init_interpreter(interp_attributes)
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

def get_interp_attributes(interp:Interpreter):
    as_class_list = copy.deepcopy(interp.as_class_list)
    connection_list = copy.deepcopy(interp.connection_list)
    public_aspa_list = copy.deepcopy(interp.public_aspa_list)
    run_updates = copy.deepcopy(interp.run_updates)
    return (as_class_list, connection_list, public_aspa_list, run_updates)

def main(pickle_file, all_asns, situation, usr_seed=None, verbose=False, iterations=10):
    if not usr_seed:
        seed = random.random()
        print(seed)
    else:
        seed = usr_seed
    match situation:
        case "protect_random":
            p = Pool(6)
            results = []
            proportions = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
            for _ in range(iterations):
                with open(pickle_file, 'rb') as infile:
                    obj = pickle.load(infile)
                scenario_gen = ((copy.deepcopy(obj), lc(all_asns,aspa=1,attack=1,seed=seed,aspa_rate=i)) for i in proportions)
                changes = p.starmap(run_scenario, scenario_gen)
                max_changes = changes[0]
                results.append(list(map(lambda x: 1.0 - x/max_changes, changes)))
                if verbose:
                    for idx, num in enumerate(changes):
                        print(f"{int(proportions[idx] * 100)}% aspv:\t\t{num} changes")
            df = pd.DataFrame(np.array(results), columns=proportions)
            print(df.describe())
        case _: # runs base scenario
            run_scenario(copy.deepcopy(obj), lc(all_asns))

def export_interpreter(base_scenario, pickle_out, pickle_flag=False):
    """
    generate pickle of interpreter
    """
    all_asns = []
    with open(base_scenario, 'r') as infile:
        data = infile.read()
        for line in data.split('\n'):
            if line.startswith('addAS '):
                all_asns.append(int(line[6:]))
    if pickle_flag:
        interpreter = run_base(base_scenario)
        obj = get_interp_attributes(interpreter)
        with open(pickle_out, "wb") as outfile:
            pickle.dump(obj, outfile)
    return all_asns

if __name__ == "__main__":
    all_asns = export_interpreter(BASE_SCENARIO, BASE_SCENARIO+".pickle")
    main(BASE_SCENARIO+".pickle", all_asns, "protect_random", verbose=False, usr_seed=0.07528564395807658)