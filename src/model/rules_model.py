class RulesModel:

    def __init__(self, exclusion_set1, exclusion_set2, exclusion_set3, dest_map) -> None:
        super().__init__()
        self.exclusion_set1 = exclusion_set1
        self.exclusion_set2 = exclusion_set2
        self.exclusion_set3 = exclusion_set3
        self.dest_map = dest_map
