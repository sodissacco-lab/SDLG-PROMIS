from . import registers

# Sidebar entries. Their pages are the permit screens: sidebar_links.py points these two
# labels at /permits/?type=animal and /permits/?type=fish.
registers._add(
    "animal-permits", "Animal movement permits", "record",
    "Movement permits for animals: sub-county to sub-county, and district to district for "
    "slaughter or other purposes.",
    "Permits issued, valid and expired, by destination.",
)
registers._add(
    "fish-permits", "Fish movement permits", "record",
    "Fish movement permits for fish and fishery products moved within Uganda.",
    "Permits issued, valid and expired, by destination.",
)


def _add_to_menu(sector, slug):
    items = list(registers.MENUS.get(sector, []))
    if slug not in items:
        items.append(slug)
    registers.MENUS[sector] = items


_add_to_menu("Veterinary", "animal-permits")
_add_to_menu("Fisheries", "fish-permits")
