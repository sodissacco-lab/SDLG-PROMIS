def _all_zero(row):
    """A register line with nothing registered, nothing new and nothing active."""
    def zero(v):
        try:
            return float(str(v).replace(",", "").strip()) == 0
        except ValueError:
            return str(v).strip() == "-"
    return all(zero(v) for v in row[1:])


def keep_nonzero(rows):
    return [r for r in rows if not _all_zero(r)]


def register_text(data):
    lines = []
    for t in data.get("register_tables") or []:
        title = t["title"]
        if title.startswith("Register statistics"):
            lines.append("Registers (these count records, not activities):")
            for r in keep_nonzero(t["rows"]):
                text = "- %s: %s registered to date, %s new in the period" % (r[0], r[1], r[2])
                if r[3] != "-":
                    text += ", %s active" % r[3]
                lines.append(text + ".")
        elif title.startswith("Measured results"):
            lines.append("Measured results recorded in the period:")
            for r in t["rows"]:
                lines.append("- %s: %s." % (r[0], r[1]))
    return "\n".join(lines)