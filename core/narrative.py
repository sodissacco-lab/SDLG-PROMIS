from .models import Parish, SubCounty

FIELDS = [
    ("introduction", "Introduction", 6),
    ("executive_summary", "Executive summary", 8),
    ("activities_text", "Activities implemented", 6),
    ("targets_text", "Performance against targets", 7),
    ("achievements_text", "Achievements by department", 6),
    ("coverage_text", "Field coverage", 6),
    ("challenges", "Challenges", 8),
    ("actions_taken", "Actions taken", 6),
    ("recommendations", "Recommendations", 8),
    ("conclusion", "Conclusion", 5),
]
KEYS = [f[0] for f in FIELDS]

KIND_WORDS = {
    "daily": "daily activity",
    "weekly": "weekly activity",
    "monthly": "monthly progress",
    "quarterly": "quarterly performance",
    "annual": "annual performance",
}


def _num(n):
    return "{:,}".format(n or 0)


def _pct_value(cell):
    try:
        return float(str(cell).rstrip("%"))
    except ValueError:
        return None


def _scope(department, sub_county):
    if sub_county and department:
        return "the %s section in %s Sub-county" % (department.name, sub_county.name)
    if sub_county:
        return "%s Sub-county" % sub_county.name
    if department:
        return "the %s section of the Production Department" % department.name
    return "the Production Department"


def _notes(qs, field, limit=10):
    seen, out = set(), []
    for text in qs.order_by("date").values_list(field, flat=True):
        t = " ".join((text or "").split())
        if not t or t.lower() in seen:
            continue
        seen.add(t.lower())
        out.append(t if len(t) <= 220 else t[:217] + "...")
        if len(out) >= limit:
            break
    return out


def build_sections(data, period, department, sub_county, qs):
    s = data["summary"]
    approved = qs.filter(status="approved")
    kind = period["kind"]
    scope = _scope(department, sub_county)
    label = data["period"]
    n, reached = s["activities"], s["reached"]
    women_pct = round(100.0 * s["women"] / reached) if reached else 0

    named = [r for r in data["by_sub_county"] if r["name"] != "Not specified"]
    done_names = {r["name"] for r in named}
    if sub_county:
        all_sc = [sub_county.name]
    else:
        all_sc = list(SubCounty.objects.order_by("name").values_list("name", flat=True))
    missing = [x for x in all_sc if x not in done_names]
    types = sorted(data["by_type"], key=lambda r: -r["activities"])

    tdata = data.get("targets")
    t_rows = tdata["rows"] if tdata and tdata["rows"] else []
    pcts = [p for p in (_pct_value(r[3]) for r in t_rows) if p is not None]
    met = sum(1 for p in pcts if p >= 100)
    behind = [
        (r, _pct_value(r[3]))
        for r in t_rows
        if _pct_value(r[3]) is not None and _pct_value(r[3]) < 50
    ]
    pending = qs.filter(status="submitted").count()
    returned = qs.filter(status="returned").count()

    out = {}

    out["introduction"] = (
        "This %s report presents the work of %s of Soroti District Local Government "
        "for %s. It is compiled from approved activity records entered by field "
        "officers in the Production Management Information System (SDLG-Production MIS), "
        "supported by GPS locations and photographs where these were captured. The "
        "report summarises what was done, who was reached, how performance compares "
        "with targets, the challenges encountered and recommendations for management."
        % (KIND_WORDS.get(kind, "progress"), scope, label)
    )

    if n == 0:
        out["executive_summary"] = (
            "No approved activities were recorded for %s during %s. If work was done, "
            "the activity records may still be awaiting supervisor approval." % (scope, label)
        )
    else:
        parts = [
            "During %s, %s approved activities were implemented by %s, reaching %s people "
            "(%s men and %s women; women were %d%% of those reached)."
            % (label, _num(n), scope, _num(reached), _num(s["men"]), _num(s["women"]), women_pct),
            "Among them were %s youth and %s persons with disability."
            % (_num(s["youth"]), _num(s["pwd"])),
        ]
        if named and not sub_county:
            top_sc = max(named, key=lambda r: r["activities"])
            parts.append(
                "Activities were recorded in %d of %d sub-counties, with %s recording the most (%s)."
                % (len(named), len(all_sc), top_sc["name"], _num(top_sc["activities"]))
            )
        if types:
            parts.append(
                "The most frequent activity was %s (%s)." % (types[0]["name"], _num(types[0]["activities"]))
            )
        if pcts:
            parts.append(
                "Against the targets set, %d of %d indicators were met or exceeded." % (met, len(pcts))
            )
        out["executive_summary"] = " ".join(parts)

    if n:
        lines = ["A total of %s approved activities were implemented during the period." % _num(n)]
        lines.append(
            "The main activity types were: "
            + "; ".join("%s (%s)" % (r["name"], _num(r["activities"])) for r in types[:5])
            + "."
        )
        bd = data.get("breakdown")
        if bd and bd["rows"]:
            peak = max(bd["rows"], key=lambda r: r["activities"])
            lines.append(
                "The busiest %s was %s with %s activities."
                % ("day" if kind == "weekly" else "month", peak["name"], _num(peak["activities"]))
            )
        out["activities_text"] = "\n".join(lines)
    else:
        out["activities_text"] = ""

    if t_rows:
        basis = "annual" if kind == "annual" else "quarterly"
        lines = ["Performance against the %s targets was as follows:" % basis]
        for r in t_rows:
            pct = r[3] if r[3] != "-" else "no target set for this period"
            lines.append("- %s: %s against a target of %s (%s)." % (r[0], _num(r[2]), _num(r[1]), pct))
        if pcts:
            lines.append(
                "%d of %d indicators were met or exceeded; %d were below half of their target."
                % (met, len(pcts), len(behind))
            )
        out["targets_text"] = "\n".join(lines)
    else:
        out["targets_text"] = ""

    out["achievements_text"] = "\n".join(
        "%s: %s activities reaching %s people." % (r["name"], _num(r["activities"]), _num(r["reached"]))
        for r in data["by_department"]
    )

    lines = []
    if named:
        ordered = sorted(named, key=lambda r: -r["activities"])
        lines.append(
            "Activities were recorded in: "
            + "; ".join("%s (%s)" % (r["name"], _num(r["activities"])) for r in ordered)
            + "."
        )
    parishes_total = (
        Parish.objects.filter(sub_county=sub_county).count() if sub_county else Parish.objects.count()
    )
    parishes_hit = approved.exclude(parish=None).order_by().values("parish").distinct().count()
    if parishes_total:
        lines.append("Activities reached %d of %d registered parishes." % (parishes_hit, parishes_total))
    if missing and not sub_county:
        lines.append("No approved activity was recorded in: %s." % ", ".join(missing))
    out["coverage_text"] = "\n".join(lines)

    findings = _notes(approved, "findings")
    follow = _notes(approved, "follow_up")
    lines = []
    if findings:
        lines.append("Findings and issues recorded by officers:")
        lines += ["- " + t for t in findings]
    if follow:
        lines.append("Follow-up required:")
        lines += ["- " + t for t in follow]
    if pending or returned:
        lines.append(
            "At the time of reporting, %d entries were awaiting supervisor review and %d had been "
            "returned for correction, so this report may understate the work done." % (pending, returned)
        )
    if not lines:
        lines.append(
            "No challenges were recorded in the activity records for this period. Officers are "
            "encouraged to record challenges in the Findings and Follow-up fields."
        )
    out["challenges"] = "\n".join(lines)

    actions = _notes(approved, "action_taken")
    out["actions_taken"] = (
        "\n".join("- " + t for t in actions)
        if actions
        else "No specific actions were recorded in the activity records for this period."
    )

    recs = []
    if missing and not sub_county:
        recs.append(
            "Schedule field visits to %s, which recorded no approved activity in the period."
            % ", ".join(missing[:6])
        )
    for r, p in behind[:4]:
        recs.append("Intensify work on %s, which reached %d%% of its target." % (r[0], round(p)))
    if pending:
        recs.append(
            "Supervisors should clear the %d entries awaiting review so that reports reflect all work done." % pending
        )
    if returned:
        recs.append("Officers should correct and resubmit the %d returned entries." % returned)
    if reached and women_pct < 40:
        recs.append("Strengthen the mobilisation of women, who were %d%% of those reached." % women_pct)
    if n and not data.get("photos"):
        recs.append("Attach photographs to activity records so that field work is supported by evidence.")
    if follow:
        recs.append("Management should follow up the issues listed under Challenges and report back on progress.")
    recs.append("Continue regular supervision and timely approval of activity records.")
    out["recommendations"] = "\n".join("%d. %s" % (i, t) for i, t in enumerate(recs, 1))

    if n:
        text = "In conclusion, %s implemented %s approved activities reaching %s people during %s." % (
            scope, _num(n), _num(reached), label,
        )
        if pcts:
            text += (
                " Performance against targets was largely on track."
                if met * 2 >= len(pcts)
                else " Several targets remain below expectation and need attention."
            )
        text += " Management is requested to consider the recommendations above."
    else:
        text = (
            "No approved activities were recorded for %s during %s. Management is requested to "
            "ensure that field records are entered and approved promptly." % (scope, label)
        )
    out["conclusion"] = text
    return out