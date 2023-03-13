class Lotus_configurator:
    def __init__(self):
        # set rand state to generate attacks
        pass

    def gen_aspa(self) -> list[str]:
        return ["autoASPA 1 1", "setASPV 25 on 3", "setASPV 11 on 3"]
        pass

    def gen_attack(self) -> list[str]:
        return ["genAttack 100 1"]
        pass