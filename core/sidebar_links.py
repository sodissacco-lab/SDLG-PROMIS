import re

# label shown in the sidebar -> page it should open
LINKS = [
    (r"Document Cent(?:re|er)", "/manage/documents/"),
    (r"Partners", "/manage/partners/"),
    (r"Animal movement permits", "/permits/?type=animal"),
    (r"Fish movement permits", "/permits/?type=fish"),
]

SKIP_PREFIXES = ("/admin/", "/offline-app", "/sw.js", "/media/", "/static/")

_patterns = [
    (
        re.compile(
            r'(<a\b[^>]*?\bhref=")[^"]*("(?:(?!</a>).){0,300}?' + label + ")",
            re.S,
        ),
        url,
    )
    for label, url in LINKS
]


class SidebarLinks:
    """Points the Document Centre and Partners & Projects sidebar links at the
    real pages, whatever the old sidebar code says. Remove it once the sidebar
    source itself has been corrected."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method != "GET"
            or request.path.startswith(SKIP_PREFIXES)
            or getattr(response, "streaming", False)
            or not response.get("Content-Type", "").startswith("text/html")
        ):
            return response
        charset = response.charset or "utf-8"
        html = response.content.decode(charset, "ignore")
        new = html
        for pattern, url in _patterns:
            new = pattern.sub(lambda m, u=url: m.group(1) + u + m.group(2), new)
        if new != html:
            response.content = new.encode(charset)
            if response.has_header("Content-Length"):
                response["Content-Length"] = str(len(response.content))
        return response
