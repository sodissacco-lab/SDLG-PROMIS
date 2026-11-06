from .models import Department

SECTOR_NAMES = ["Fisheries", "Entomology", "Crops", "Veterinary"]
OTHER_NAMES = ["Commercial"]


def _ordered(names):
    found = {d.name: d for d in Department.objects.filter(name__in=names)}
    return [found[n] for n in names if n in found]


def sectors():
    return _ordered(SECTOR_NAMES)


def other_departments():
    return _ordered(OTHER_NAMES)