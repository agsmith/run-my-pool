from public_identity import display_name_from_email, public_display_name


def test_display_name_uses_only_email_local_part():
    assert display_name_from_email("Tony.Sweeney+pool@example.com") == "Tony.Sweeney+pool"


def test_display_name_falls_back_without_exposing_missing_identity():
    assert display_name_from_email(None) == "Member"
    assert public_display_name(type("User", (), {"email": "player@company.example"})()) == "player"
