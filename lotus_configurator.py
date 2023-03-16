import random
from typing import Tuple

class Lotus_configurator:
    setASPV_str = "setASPV {} on {}"
    autoASPA_str = "autoASPA {} {}"
    attack_str = "genAttack {} {}"

    def __init__(self, aspa_flag:int, all_asns:list[int], seed=None, aspa_rate=0.0):
        if seed:
            self.seed = seed
        else:
            self.seed = 0
        self.all_asns = all_asns
        self.aspa_flag = aspa_flag
        self.aspa_rate = aspa_rate

    def gen_aspa(self, target) -> list[str]:
        match self.aspa_flag:
            case 0:
                return []
            case 1:
                num_deploy = int(self.aspa_rate * len(self.all_asns))
                # protect target with aspa
                aspa_config = [Lotus_configurator.autoASPA_str.format(target, 2)]
                aspa_config.extend([Lotus_configurator.setASPV_str.format(x, 1) for x in random.sample(self.all_asns, num_deploy)])
                print(f"aspv deployed: {num_deploy} at {self.aspa_rate}%")
                return aspa_config

    def gen_attack(self):
        asns = random.sample(self.all_asns, 3)
        return (asns, [Lotus_configurator.attack_str.format(asns[0], asns[1])])
    
    def gen_situation(self) -> Tuple[list[str], list[str]]:
        random.seed(self.seed)
        asns, attack = self.gen_attack()
        print(f"attack: {attack}")
        aspa = self.gen_aspa(asns[1])
        return (aspa, attack)
