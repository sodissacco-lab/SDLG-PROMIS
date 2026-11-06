from .reg_config import CONFIGS

fish = CONFIGS["fish-farmers"]
fish.fields = list(fish.fields) + ["farm_name", "farm_category"]
fish.columns = [fish.columns[0], ("Farm or group", "farm_name")] + list(fish.columns[1:])

boats = CONFIGS["boats"]
boats.fields = list(boats.fields) + ["vessel_type", "propulsion", "fishing_gear", "main_species", "bariars"]
boats.columns = list(boats.columns) + [
    ("Propulsion", "propulsion"),
    ("Gear", "fishing_gear"),
    ("Species", "main_species"),
]