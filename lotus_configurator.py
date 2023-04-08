import json
import random
from typing import Tuple

class Lotus_configurator:
    setASPV_str = "setASPV {} on {}"
    autoASPA_str = "autoASPA {} {}"
    attack_str = "genAttack {} {}"

    def __init__(self, all_asns, aspa=0, attack=0, seed=None, params={}):
        if seed:
            self.seed = seed
        else:
            self.seed = 0
        self.all_asns = all_asns
        self.aspa_flag = aspa
        self.attack_flag = attack
        self.params = params

    def gen_aspa(self, asns) -> list[str]:
        match self.aspa_flag:
            case 1: # protect target with aspa
                if len(asns) == 0:
                    return []
                target = asns[1]
                num_deploy = int(float(self.params["aspv_rate"]) * len(self.all_asns))
                aspa_config = [Lotus_configurator.autoASPA_str.format(target, 5)]
                aspa_config.extend([Lotus_configurator.setASPV_str.format(x, 1) for x in random.sample(self.all_asns, num_deploy)])
                # print(f"aspv deployed: {num_deploy} at {float(self.params["aspv_rate"])}%")
                return aspa_config
            case 2:
                # get edge nodes of target country, set aspv there
                # protect target with aspa
                if len(asns) == 0:
                    return []
                target = asns[1]
                with open(self.params["edge_node_file"], "r") as in_file:
                    edge_nodes = json.load(in_file)
                num_deploy = int(float(self.params["aspv_rate"]) * len(edge_nodes))
                edge_nodes = random.sample(edge_nodes, num_deploy)
                aspa_config = [Lotus_configurator.autoASPA_str.format(target, 5)]
                aspa_config.extend([Lotus_configurator.setASPV_str.format(x, 1) for x in edge_nodes])
                return aspa_config
            case _:
                return []

    def gen_attack(self):
        match self.attack_flag:
            case 1:
                asns = random.sample(self.all_asns, 2)
                return (asns, [Lotus_configurator.attack_str.format(asns[0], asns[1])])
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
                        [Lotus_configurator.attack_str.format(asns[0], asns[1])])
            case _:
                return ([],[])
    
    def gen_situation(self) -> Tuple[list[str], list[str]]:
        random.seed(self.seed)
        asns, attack = self.gen_attack()
        aspa = self.gen_aspa(asns)
        return (aspa, attack)
