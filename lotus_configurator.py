import random
from typing import Tuple

class Lotus_configurator:
    setASPV_str = "setASPV {} on {}"
    autoASPA_str = "autoASPA {} {}"
    attack_str = "genAttack {} {}"

    def __init__(self, all_asns:list[int], aspa=0, attack=0, seed=None, params={}):
        if seed:
            self.seed = seed
        else:
            self.seed = 0
        self.all_asns = all_asns
        self.aspa_flag = aspa
        self.attack_flag = attack
        self.params = params

    def gen_aspa(self, target) -> list[str]:
        match self.aspa_flag:
            case 1: # protect target with aspa
                num_deploy = int(float(self.params["aspv_rate"]) * len(self.all_asns))
                aspa_config = [Lotus_configurator.autoASPA_str.format(target, 2)]
                aspa_config.extend([Lotus_configurator.setASPV_str.format(x, 1) for x in random.sample(self.all_asns, num_deploy)])
                # print(f"aspv deployed: {num_deploy} at {float(self.params["aspv_rate"])}%")
                return aspa_config
            # case 2:
            case _:
                return []

    def gen_attack(self):
        match self.attack_flag:
            case 1:
                asns = random.sample(self.all_asns, 3)
                return (asns, [Lotus_configurator.attack_str.format(asns[0], asns[1])])
            case _:
                return []
    
    def gen_situation(self) -> Tuple[list[str], list[str]]:
        random.seed(self.seed)
        asns, attack = self.gen_attack()
        aspa = self.gen_aspa(asns[1])
        return (aspa, attack)
