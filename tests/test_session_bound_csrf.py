from sentinel_alpha.browser_auth import _csrf_for_session, _csrf_matches_session

def test_csrf_value_is_bound_to_issuing_session():
    first="session-one"
    second="session-two"
    csrf=_csrf_for_session(first)
    assert _csrf_matches_session(first,csrf)
    assert not _csrf_matches_session(second,csrf)

def test_tampered_csrf_binding_is_rejected():
    csrf=_csrf_for_session("session-one")
    nonce,digest=csrf.split(".",1)
    tampered=nonce+"."+("0" if digest[0]!="0" else "1")+digest[1:]
    assert not _csrf_matches_session("session-one",tampered)
