COMMON = [
    "Office work or report writing",
    "Staff or planning meeting",
    "Supervision visit",
    "Workshop or training attended",
    "Other (describe)",
]

PDM_TYPES = [
    "PDM: Beneficiary group training",
    "PDM: Monitoring visit",
    "PDM: Business plan review",
    "PDM: Group meeting",
    "PDM: Loan or recovery follow-up",
]

_SECTORS = {
    "Fisheries": [
        "Fish farmer extension visit",
        "Pond or cage inspection",
        "Landing site inspection",
        "Boat registration",
        "Boat or fishing licence issued or renewed",
        "Fisher sensitization or training",
        "Enforcement operation or patrol",
        "Illegal fishing case handled",
        "Fish stocking or harvest supervision",
        "Catch assessment",
        "Fish monger or trader registration",
    ],
    "Entomology": [
        "Trap deployment",
        "Trap inspection or catch count",
        "Vector control activity",
        "Pest or vector surveillance",
        "Community sensitization",
    ],
    "Crops": [
        "Farmer extension visit",
        "Demonstration plot setup or visit",
        "Farmer training",
        "Pest or disease surveillance",
        "Input distribution",
        "Crop assessment or harvest estimate",
        "Post-harvest handling support",
        "Market information visit",
    ],
    "Veterinary": [
        "Farm or farmer visit",
        "Vaccination campaign",
        "Animal treatment",
        "Disease surveillance",
        "Outbreak investigation or response",
        "Artificial insemination service",
        "Livestock market inspection",
        "Slaughter inspection",
        "Farmer training",
    ],
}

_COMMERCIAL = [
    "Enterprise or group visit",
    "Business training",
    "Cooperative or SACCO support",
    "Market or value-addition support",
    "Business plan support",
]

BY_DEPARTMENT = {name: types + PDM_TYPES for name, types in _SECTORS.items()}
BY_DEPARTMENT["Commercial"] = list(_COMMERCIAL)


def allowed_types(department_name):
    return BY_DEPARTMENT.get(department_name, []) + COMMON


def all_types():
    seen = []
    for lst in list(BY_DEPARTMENT.values()) + [COMMON]:
        for t in lst:
            if t not in seen:
                seen.append(t)
    return seen
_ENT_EXTRA = [
    "Bee keeping: on-farm apiary visit",
    "Bee keeping: group training on new beekeeping methods",
    "Black soldier fly: training",
    "Black soldier fly: farmer visit",
    "Collaboration with partners or other departments",
    "Vermin surveillance",
    "Vermin control",
]
BY_DEPARTMENT["Entomology"] = _SECTORS["Entomology"] + _ENT_EXTRA + PDM_TYPES