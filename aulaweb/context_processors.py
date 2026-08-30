import secrets


def csp_nonce(request):
    """One nonce shared by the parent page and its sandboxed srcdoc preview."""

    nonce = getattr(request, "_aulaweb_csp_nonce", None)
    if nonce is None:
        nonce = secrets.token_urlsafe(24)
        request._aulaweb_csp_nonce = nonce
    return {"csp_nonce": nonce}
