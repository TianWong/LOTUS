import copy
import json
import random
from typing import Tuple
ASPA_DISTANCE = 1

class Lotus_configurator:
    setASPV_str = "setASPV {} on {} {}"
    autoASPA_str = "autoASPA {} {}"
    attack_str = "genAttack {} {}"

    def __init__(self, all_asns, aspa=0, attack=0, seed=None, params={"aspv_level":1}):
        if seed:
            self.seed = seed
        else:
            self.seed = 0
        self.all_asns = all_asns
        self.aspa_flag = aspa
        self.attack_flag = attack
        self.params = params

    def gen_aspa(self, asns) -> list[str]:
        if len(asns) == 0:
            return []
        target = asns[1]
        aspv_local_prf = ""
        if "aspv_local_prf" in self.params:
            aspv_local_prf = self.params["aspv_local_prf"]
        match self.aspa_flag:
            case 0:
                # variable aspv and aspa together, without target protection
                asn_ls = self.all_asns
                asn_ls.remove(target)
                num_deploy = int(float(self.params["rate"]) * len(asn_ls))
                aspa_config = []
                for x in random.sample(asn_ls, num_deploy):
                    aspa_config.extend(
                        [self.autoASPA_str.format(x, ASPA_DISTANCE), 
                         self.setASPV_str.format(x, self.params["aspv_level"], aspv_local_prf)])
                # print(f"aspv deployed: {num_deploy} at {float(self.params["aspv_rate"])}%")
                return aspa_config
            case 1:
                # variable aspv and aspa together
                num_deploy = int(float(self.params["rate"]) * len(self.all_asns))
                aspa_config = [self.autoASPA_str.format(target, ASPA_DISTANCE)]
                for x in random.sample(self.all_asns, num_deploy):
                    aspa_config.extend(
                        [self.autoASPA_str.format(x, ASPA_DISTANCE), 
                         self.setASPV_str.format(x, self.params["aspv_level"], aspv_local_prf)])
                # print(f"aspv deployed: {num_deploy} at {float(self.params["aspv_rate"])}%")
                return aspa_config
            case 2:
                # aspa+aspv at target country
                asn_cl = list(self.all_asns.class_list.values())
                target_country_asns = list(filter(lambda x: x.country == self.params["target"], asn_cl))
                num_deploy = int(float(self.params["rate"]) * len(target_country_asns))
                aspa_config = [self.autoASPA_str.format(target, ASPA_DISTANCE)]
                for x in random.sample(target_country_asns, num_deploy):
                    aspa_config.extend(
                        [self.autoASPA_str.format(x.as_number, ASPA_DISTANCE), 
                         self.setASPV_str.format(x.as_number, self.params["aspv_level"], aspv_local_prf)])
                return aspa_config
            case 3:
                # variable aspv and aspa
                def rand_elem_gen(seq):
                    rand_seq = copy.deepcopy(seq)
                    random.shuffle(rand_seq)
                    for x in rand_seq:
                        yield x
                aspa_deploy = int(float(self.params["aspa_rate"]) * len(self.all_asns)) # account for aspa at target
                aspv_deploy = int(float(self.params["aspv_rate"]) * len(self.all_asns))
                config = [self.autoASPA_str.format(target, ASPA_DISTANCE)]
                aspa_gen = rand_elem_gen(self.all_asns)
                aspv_gen = rand_elem_gen(self.all_asns)
                for i in range(max(aspa_deploy, aspv_deploy)):
                    if i < aspa_deploy:
                        config.append(self.autoASPA_str.format(next(aspa_gen), ASPA_DISTANCE))
                    else:
                        next(aspa_gen)
                    if i < aspv_deploy:
                        config.append(self.setASPV_str.format(next(aspv_gen), self.params["aspv_level"], aspv_local_prf))
                    else:
                        next(aspv_gen)
                return config
            case 4:
                # variable aspa+aspv and aspv level
                num_deploy = int(float(self.params["rate"]) * len(self.all_asns))
                config = [self.autoASPA_str.format(target, ASPA_DISTANCE)]
                as_ls = random.sample(self.all_asns, num_deploy)
                aspv_1_ls = random.sample(as_ls, int(float(self.params["aspv_1_rate"]) * len(as_ls)))
                for x in as_ls:
                    level = 2
                    if x in aspv_1_ls:
                        level = 1
                    config.extend(
                        [self.autoASPA_str.format(x, ASPA_DISTANCE), 
                         self.setASPV_str.format(x, level, aspv_local_prf)])
                return config
            case 5:
                # combination of 2 and 4
                asn_cl = list(self.all_asns.class_list.values())
                target_country_asns = list(filter(lambda x: x.country == self.params["target"], asn_cl))
                num_deploy = int(float(self.params["rate"]) * len(target_country_asns))
                aspa_config = [self.autoASPA_str.format(target, ASPA_DISTANCE)]
                as_ls = random.sample(target_country_asns, num_deploy)
                aspv_1_ls = random.sample(as_ls, int(float(self.params["aspv_1_rate"]) * len(as_ls)))
                for x in as_ls:
                    level = 2
                    if x in aspv_1_ls:
                        level = 1
                    aspa_config.extend(
                        [self.autoASPA_str.format(x.as_number, ASPA_DISTANCE), 
                         self.setASPV_str.format(x.as_number, level, aspv_local_prf)])
                return aspa_config
            case _:
                return []

    def gen_attack(self):
        match self.attack_flag:
            case 1:
                asns = random.sample(self.all_asns, 2)
                return (asns, [self.attack_str.format(asns[0], asns[1])])
            case 2:
                target_asn = None
                with open(self.params["edge_node_file"], "r") as in_file:
                    edge_nodes = json.load(in_file)
                attacker_asn = random.sample(edge_nodes, 1)[0]
                asn_cl = list(self.all_asns.class_list.values())
                random.shuffle(asn_cl)
                for asn in asn_cl:
                    if asn.country == self.params["target"]:
                        target_asn = asn
                        break
                if target_asn == None:
                    raise RuntimeError(f"No nodes matching target country {self.params['target']}")
                asns = [attacker_asn, target_asn.as_number]
                return (asns,
                        [self.attack_str.format(asns[0], asns[1])])
            case _:
                return ([],[])
    
    def gen_situation(self) -> Tuple[list[str], list[str]]:
        random.seed(self.seed)
        asns, attack = self.gen_attack()
        aspa = self.gen_aspa(asns)
        return (aspa, attack)
