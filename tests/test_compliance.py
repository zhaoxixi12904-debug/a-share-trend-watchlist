import pytest

from a_share_watchlist.compliance import assert_no_banned_terms, validate_action


def test_validate_action_allows_only_observation_actions():
    assert validate_action("观察") == "观察"
    assert validate_action("等待回调") == "等待回调"
    assert validate_action("排除") == "排除"

    with pytest.raises(ValueError):
        validate_action("买入")


def test_banned_terms_are_rejected():
    with pytest.raises(ValueError):
        assert_no_banned_terms(["这里不能出现买入措辞"])
