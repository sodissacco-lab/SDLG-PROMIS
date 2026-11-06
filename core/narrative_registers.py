def register_text(data):
    lines = []
    for t in data.get("register_tables") or []:
        title = t["title"]
        if title.startswith("Register statistics"):
            lines.append("Registers (these count records, not activities):")
            for r in t["rows"]:
                text = "- %s: %s registered to date, %s new in the period" % (r[0], r[1], r[2])
                if r[3] != "-":
                    text += ", %s active" % r[3]
                lines.append(text + ".")
        elif title.startswith("Measured results"):
            lines.append("Measured results recorded in the period:")
            for r in t["rows"]:
                lines.append("- %s: %s." % (r[0], r[1]))
    return "\n".join(lines)