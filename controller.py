import copy
from functools import reduce
import gc
import os
import pickle
import random
import sys

import pandas as pd
import numpy as np
from lotus_configurator import Lotus_configurator as lc
from main import Interpreter
from multiprocessing import Pool

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

def run_scenario(interp_attributes, config: lc, verbose=False):
    interpreter = init_interpreter(interp_attributes)
    aspa_config, attack = config.gen_situation()
    if verbose:
        print(aspa_config)
        print(attack)

    # add ASPA/ASPV configuration
    interpreter.execute(aspa_config)
    interpreter.do_run("")
    
    # add attack from attack_generator
    interpreter.execute(attack)
    interpreter.do_run("diff")

    updates = interpreter.run_updates
    
    # edge defense
    if config.attack_flag == 2:
        count = 0
        target_country = config.params["target"]
        for routing_table in updates.values():
            for _, route_diff in routing_table.values():
                target_as = route_diff["path"].split("-")[0]
            if config.all_asns.class_list[target_as].country == target_country:
                count += 1
        return count
    
    if verbose:
        print(f"ASPA+ASPV commands:{len(aspa_config)}, affected ASes:{len(updates)}, {updates}")
    return reduce(lambda x, y: x + len(y), updates.values(), 0)

def get_interp_attributes(interp:Interpreter):
    as_class_list = copy.deepcopy(interp.as_class_list)
    connection_list = copy.deepcopy(interp.connection_list)
    public_aspa_list = copy.deepcopy(interp.public_aspa_list)
    run_updates = copy.deepcopy(interp.run_updates)
    return (as_class_list, connection_list, public_aspa_list, run_updates)

def compare_to_worst(x, max_changes) -> float:
    # returns relative improvement of x over max_changes
    if max_changes != 0:
        return 1.0 - x/max_changes
    elif x != 0:
        return -1.0
    return 0.0

def main(pickle_file, all_asns, situation, usr_seed=None, aspv_level=1, verbose=False, iterations=100):
    if not usr_seed:
        seed = random.random()
        print(seed)
    else:
        seed = usr_seed
    with open(pickle_file, 'rb') as infile:
        obj = pickle.load(infile)
    match situation:
        case "random_joint_aspa_aspv_switch":
            # random attacker and target, protected by aspa/aspv, varying joint aspa+aspv globally
            p = Pool(11)
            results = []
            proportions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            for _ in range(iterations):
                scenario_gen = ((copy.deepcopy(obj), lc(all_asns,aspa=0,attack=1,seed=seed,params={"rate":i,"aspv_level":aspv_level}), verbose) for i in proportions)
                changes = p.starmap(run_scenario, scenario_gen)
                max_changes = changes[0]
                results.append(list(map(lambda x: compare_to_worst(x, max_changes), changes)))
                if verbose:
                    for idx, num in enumerate(changes):
                        print(f"{int(proportions[idx] * 100)}% deployment:\t\t{num} changes")
                seed += 1
            df = pd.DataFrame(np.array(results), columns=proportions)
            return df
        case "random_joint_aspa_aspv":
            # random attacker and target, protected by aspa/aspv, varying joint aspa+aspv globally
            p = Pool(11)
            results = []
            proportions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            for _ in range(iterations):
                scenario_gen = ((copy.deepcopy(obj), lc(all_asns,aspa=1,attack=1,seed=seed,params={"rate":i,"aspv_level":aspv_level}), verbose) for i in proportions)
                changes = p.starmap(run_scenario, scenario_gen)
                max_changes = changes[0]
                results.append(list(map(lambda x: compare_to_worst(x, max_changes), changes)))
                # if max(results[-1]) != 0.0:
                #     print(seed, changes)
                if verbose:
                    for idx, num in enumerate(changes):
                        print(f"{int(proportions[idx] * 100)}% deployment:\t\t{num} changes")
                seed += 1
            df = pd.DataFrame(np.array(results), columns=proportions)
            return df
        case "random_joint_aspa_aspv_loc_perf":
            # random attacker and target, protected by aspa/aspv, varying joint aspa+aspv globally
            p = Pool(11)
            results = []
            proportions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            for _ in range(iterations):
                scenario_gen = ((copy.deepcopy(obj), lc(all_asns,aspa=1,attack=1,seed=seed,params={"rate":i,"aspv_level":aspv_level, "aspv_local_prf":"True"}), verbose) for i in proportions)
                changes = p.starmap(run_scenario, scenario_gen)
                max_changes = changes[0]
                results.append(list(map(lambda x: compare_to_worst(x, max_changes), changes)))
                if verbose:
                    for idx, num in enumerate(changes):
                        print(f"{int(proportions[idx] * 100)}% deployment:\t\t{num} changes")
                seed += 1
            df = pd.DataFrame(np.array(results), columns=proportions)
            return df
        case "random_joint_aspa_aspv_level":
            # random attacker and target, protected by aspa/aspv, varying aspv 1/2
            p = Pool(8)
            results = []
            max_changes_ls = []
            proportions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]
            for i in proportions:
                iterseed = seed
                aspv_iter_results = np.zeros(8)
                for it in range(iterations):
                    scenario_gen = ((copy.deepcopy(obj), 
                                    lc(all_asns,aspa=4,attack=1,seed=iterseed,
                                        params={"rate":i,"aspv_1_rate":j}), 
                                    verbose) 
                                    for j in proportions)
                    changes = p.starmap(run_scenario, scenario_gen)
                    if i == 0.0:
                        max_changes = changes[0]
                        max_changes_ls.append(max_changes)
                    else:
                        max_changes = max_changes_ls[it]
                    aspv_iter_results += np.fromiter(map(lambda x: compare_to_worst(x, max_changes), changes), dtype=float)
                    iterseed += 1
                results.append(aspv_iter_results / iterations)
                gc.collect()
            return np.array(results)
        case "random_joint_aspa_aspv_level_loc_prf":
            # random attacker and target, protected by aspa/aspv, varying aspv 1/2, loc_prf adjustment
            p = Pool(8)
            results = []
            max_changes_ls = []
            proportions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]
            for i in proportions:
                iterseed = seed
                aspv_iter_results = np.zeros(8)
                for it in range(iterations):
                    scenario_gen = ((copy.deepcopy(obj), 
                                    lc(all_asns,aspa=4,attack=1,seed=iterseed,
                                        params={"rate":i,"aspv_1_rate":j,"aspv_local_prf":"True"}), 
                                    verbose) 
                                    for j in proportions)
                    changes = p.starmap(run_scenario, scenario_gen)
                    if i == 0.0:
                        max_changes = changes[0]
                        max_changes_ls.append(max_changes)
                    else:
                        max_changes = max_changes_ls[it]
                    aspv_iter_results += np.fromiter(map(lambda x: compare_to_worst(x, max_changes), changes), dtype=float)
                    iterseed += 1
                results.append(aspv_iter_results / iterations)
                gc.collect()
            return np.array(results)
        case "international_defense":
            # from country a edge -> country b, joint aspa+aspv
            p = Pool(8)
            results = []
            proportions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]
            for _ in range(iterations):
                scenario_gen = ((copy.deepcopy(obj), 
                                 lc(obj[0],aspa=2,attack=2,seed=seed,
                                    params={"attacker":"CA", "target":"GB", 
                                            "edge_node_file":"ca_gb/ca_gb_cleaned_ranked_CA_edge_nodes", 
                                            "rate":i, "aspv_level":aspv_level}),
                                 verbose)
                                 for i in proportions)
                changes = p.starmap(run_scenario, scenario_gen)
                max_changes = changes[0]
                results.append(list(map(lambda x: compare_to_worst(x, max_changes), changes)))
                if verbose:
                    for idx, num in enumerate(changes):
                        print(f"{int(proportions[idx] * 100)}% aspv at edge:\t\t{num} changes")
                seed += 1
            df = pd.DataFrame(np.array(results), columns=proportions)
            return df
        case "international_defense_aspv_level":
            # from country a edge -> country b, joint aspa+aspv, varying aspv 1/2
            p = Pool(8)
            results = []
            max_changes_ls = []
            proportions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]
            for i in proportions:
                iterseed = seed
                aspv_iter_results = np.zeros(8)
                for it in range(iterations):
                    scenario_gen = ((copy.deepcopy(obj), 
                                 lc(obj[0],aspa=5,attack=2,seed=iterseed,
                                    params={"attacker":"CA", "target":"GB", 
                                            "edge_node_file":"ca_gb/ca_gb_cleaned_ranked_CA_edge_nodes", 
                                            "rate":i, "aspv_1_rate":j, "aspv_level":aspv_level}),
                                 verbose) 
                                    for j in proportions)
                    changes = p.starmap(run_scenario, scenario_gen)
                    if i == 0.0:
                        max_changes = changes[0]
                        max_changes_ls.append(max_changes)
                    else:
                        max_changes = max_changes_ls[it]
                    aspv_iter_results += np.fromiter(map(lambda x: compare_to_worst(x, max_changes), changes), dtype=float)
                    iterseed += 1
                results.append(aspv_iter_results / iterations)
                gc.collect()
            return np.array(results)
        case "random_aspa_aspv":
            # varying aspa and aspv independent of one another
            p = Pool(8)
            results = []
            max_changes_ls = []
            proportions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]
            for i in proportions:
                iterseed = seed
                aspv_iter_results = np.zeros(8)
                for it in range(iterations):
                    scenario_gen = ((copy.deepcopy(obj), 
                                    lc(all_asns,aspa=3,attack=1,seed=iterseed,
                                        params={"aspa_rate":i,"aspv_rate":j, "aspv_level":aspv_level}), 
                                    verbose) 
                                    for j in proportions)
                    changes = p.starmap(run_scenario, scenario_gen)
                    
                    if i == 0.0:
                        max_changes = changes[0]
                        max_changes_ls.append(max_changes)
                    else:
                        max_changes = max_changes_ls[it]
                    aspv_iter_results += np.fromiter(map(lambda x: compare_to_worst(x, max_changes), changes), dtype=float)
                    iterseed += 1
                results.append(aspv_iter_results / iterations)
                gc.collect()
            return np.array(results)
        case "random_aspa_aspv_rewrite":
            # varying aspa and aspv independent of one another
            p = Pool(8)
            proportions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]
            results = np.zeros((8,8))
            iterseed = seed
            max_changes = None
            for it in range(iterations):
                it_update = None
                for i in proportions:
                    scenario_gen = ((copy.deepcopy(obj), 
                                        lc(all_asns,aspa=3,attack=1,seed=iterseed,
                                            params={"aspa_rate":i,"aspv_rate":j, "aspv_level":aspv_level}), 
                                        verbose) 
                                        for j in proportions)
                    changes = p.starmap(run_scenario, scenario_gen)
                    if i == proportions[0]:
                        max_changes = changes[0]
                    row_update = np.fromiter(map(lambda x: compare_to_worst(x, max_changes), changes), dtype=float)
                    if i == proportions[0]:
                        it_update = row_update
                    else:
                        it_update = np.vstack((it_update, row_update))
                iterseed += 1
                results += it_update
            return results/iterations
        case _:
            # base scenario, no attack, aspa, aspv
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
                asn = line[6:].split()
                all_asns.append(int(asn[0]))
    if pickle_flag:
        interpreter = run_base(base_scenario)
        obj = get_interp_attributes(interpreter)
        with open(pickle_out, "wb") as outfile:
            pickle.dump(obj, outfile)
    return all_asns

if __name__ == "__main__":
    base_scenario = sys.argv[1]
    print(f"using {base_scenario} as the base scenario")
    all_asns = export_interpreter(base_scenario, base_scenario+".pickle", pickle_flag=True)
    main(base_scenario+".pickle", all_asns, "", verbose=False)