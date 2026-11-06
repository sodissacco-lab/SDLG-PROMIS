from django.db.models import Sum

from .ent_com_models import (
    MSME,
    Enterprise,
    EnterprisePerformance,
    LoanIntervention,
    Market,
    MarketLinkage,
    SurveillanceRound,
    Trap,
    TrapInspection,
    ValueAdditionVenture,
    VectorCount,
    VectorIncident,
)
from .report_registers import _in, _row, _sum


def more_register_tables(period, department=None, sub_county=None):
    start, end = period["start"], period["end"]
    name = department.name if department else None

    def sc(qs, path):
        return qs.filter(**{path: sub_county}) if sub_county else qs

    active = {"status": "active"}
    rows, measured = [], []

    if name in (None, "Entomology"):
        rows += [
            _row("Traps", sc(Trap.objects.all(), "sub_county"), start, end, active),
            _row("Vector incidents", sc(VectorIncident.objects.all(), "sub_county"), start, end, active),
        ]
        inspections = _in(sc(TrapInspection.objects.all(), "trap__sub_county"), start, end)
        measured += [
            ["Traps operational now", sc(Trap.objects.filter(status="active"), "sub_county").count()],
            ["Trap inspections", inspections.count()],
            ["Traps inspected", inspections.values("trap").distinct().count()],
            ["Vectors caught", _sum(
                sc(VectorCount.objects.filter(inspection__date__gte=start, inspection__date__lte=end),
                   "inspection__trap__sub_county"), "number_caught")],
            ["Surveillance rounds", _in(sc(SurveillanceRound.objects.all(), "sub_county"), start, end).count()],
            ["Vector incidents reported", _in(sc(VectorIncident.objects.all(), "sub_county"), start, end).count()],
        ]

    if name in (None, "Commercial"):
        rows += [
            _row("Enterprises", sc(Enterprise.objects.all(), "sub_county"), start, end, active),
            _row("MSMEs", sc(MSME.objects.all(), "sub_county"), start, end, active),
            _row("Markets", sc(Market.objects.all(), "sub_county"), start, end, active),
            _row("Value addition ventures", sc(ValueAdditionVenture.objects.all(), "sub_county"), start, end, active),
        ]
        perf = _in(sc(EnterprisePerformance.objects.all(), "enterprise__sub_county"), start, end)
        measured += [
            ["Revenue reported (UGX)", "{:,}".format(_sum(perf, "revenue_ugx"))],
            ["Expenditure reported (UGX)", "{:,}".format(_sum(perf, "expenditure_ugx"))],
        ]
        if sub_county is None:
            loans = LoanIntervention.objects.all()
            measured += [
                ["Loans and support given in the period (UGX)", "{:,}".format(_sum(_in(loans, start, end), "amount_ugx"))],
                ["Repaid to date (UGX)", "{:,}".format(_sum(loans, "repaid_ugx"))],
                ["Overdue loans now", loans.filter(status="overdue").count()],
                ["Market linkages recorded", _in(MarketLinkage.objects.all(), start, end).count()],
            ]

    tables = []
    if rows:
        tables.append({
            "title": "Register statistics: Entomology and Commercial",
            "header": ["Register", "Registered to date", "New in the period", "Active now"],
            "rows": rows,
        })
    if measured:
        tables.append({
            "title": "Measured results: Entomology and Commercial",
            "header": ["Indicator", "Total"],
            "rows": measured,
        })
    return tables