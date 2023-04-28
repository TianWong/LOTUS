import json
import random
from typing import Tuple
ASPA_DISTANCE = 5

class Lotus_configurator:
    setASPV_str = "setASPV {} on {}"
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
        match self.aspa_flag:
            case 1:
                # variable aspv and aspa together
                num_deploy = int(float(self.params["rate"]) * len(self.all_asns))
                aspa_config = [self.autoASPA_str.format(target, ASPA_DISTANCE)]
                for x in random.sample(self.all_asns, num_deploy):
                    aspa_config.extend([self.autoASPA_str.format(x, ASPA_DISTANCE), self.setASPV_str.format(x, self.params["aspv_level"])])
                # print(f"aspv deployed: {num_deploy} at {float(self.params["aspv_rate"])}%")
                return aspa_config
            case 2:
                # get edge nodes of target country, set aspv there
                # protect target with aspa
                with open(self.params["edge_node_file"], "r") as in_file:
                    edge_nodes = json.load(in_file)
                num_deploy = int(float(self.params["aspv_rate"]) * len(edge_nodes))
                edge_nodes = random.sample(edge_nodes, num_deploy)
                aspa_config = [self.autoASPA_str.format(target, ASPA_DISTANCE)]
                aspa_config.extend([self.setASPV_str.format(x, self.params["aspv_level"]) for x in edge_nodes])
                return aspa_config
            case 3:
                # variable aspv and aspa
                aspa_deploy = int(float(self.params["aspa_rate"]) * len(self.all_asns)) # account for aspa at target
                aspv_deploy = int(float(self.params["aspv_rate"]) * len(self.all_asns))
                config = [self.autoASPA_str.format(target, ASPA_DISTANCE)]
                config.extend([self.autoASPA_str.format(x, ASPA_DISTANCE) for x in random.sample(self.all_asns, aspa_deploy)])
                config.extend([self.setASPV_str.format(x, self.params["aspv_level"]) for x in random.sample(self.all_asns, aspv_deploy)])
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
                    config.extend([self.autoASPA_str.format(x, ASPA_DISTANCE), self.setASPV_str.format(x, level)])
                return config
            case _:
                return []

    def gen_attack(self):
        match self.attack_flag:
            case 1:
                asns = random.sample(self.all_asns, 2)
                return (asns, [self.attack_str.format(asns[0], asns[1])])
            case 2:
                attacker_asn = None
                target_asn = None
                asn_cl = list(self.all_asns.class_list.values())
                while attacker_asn == None or target_asn == None:
                    val = random.sample(asn_cl, 1)[0]
                    if val.country == self.params["attacker"] and attacker_asn == None:
                        attacker_asn = val
                    elif val.country == self.params["target"] and target_asn == None:
                        target_asn = val
                asns = [attacker_asn.as_number, target_asn.as_number]
                return (asns,
                        [self.attack_str.format(asns[0], asns[1])])
            case _:
                return ([],[])
    
    def gen_situation(self) -> Tuple[list[str], list[str]]:
        random.seed(self.seed)
        asns, attack = self.gen_attack()
        aspa = self.gen_aspa(asns)
        return (aspa, attack)
