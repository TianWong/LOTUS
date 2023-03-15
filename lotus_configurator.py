import random
from main import Interpreter

class Lotus_configurator:
    def __init__(self, aspa, attack, seed=None):
        if seed:
            random.seed(seed)

        self.aspa_situation = aspa
        self.attack_type = attack
        
        self.attack_list = []

    def gen_aspa(self, params) -> list[str]:
        setASPV_str = "setASPV {} on {}"
        autoASPA_str = "autoASPA {} {}"
        match self.aspa_situation:
            case 0:
                return []
            case 1:
                return ["autoASPA 39875 3", "setASPV 13768 on 1"]
        # return ["autoASPA 1 1", "setASPV 25 on 3", "setASPV 11 on 3"]

    def _international(self, attack_str:str, params):
        country_a = params[0]
        country_b = params[1]
        return ["genAttack 46320 39875"]
        # return [attack_str.format()]
        pass

    def gen_attack(self, params) -> list[str]:
        attack_str = "genAttack {} {}"
        match self.attack_type:
            case 0:
                return self._international(attack_str, params)
        # return ["genAttack 100 1"]
        pass

if __name__ == "__main__":
    from main import Interpreter
    i = Interpreter()
    config = Lotus_configurator()
    config.gen_aspa(i)
    import code
    code.interact(local=locals())