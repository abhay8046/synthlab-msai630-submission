from synthlab.access import can_generate

def test_no_configured_password_always_blocks_generation():
    assert not can_generate(configured_password=None,supplied_password=None,has_api_credentials=True)
    assert not can_generate(configured_password="",supplied_password="anything",has_api_credentials=True)

def test_credentials_alone_are_not_sufficient():
    assert not can_generate(configured_password="team-only",supplied_password="",has_api_credentials=True)
    assert not can_generate(configured_password="team-only",supplied_password="wrong",has_api_credentials=True)
    assert not can_generate(configured_password="team-only",supplied_password="team-only",has_api_credentials=False)

def test_valid_password_and_api_are_required():
    assert can_generate(configured_password="team-only",supplied_password="team-only",has_api_credentials=True)
