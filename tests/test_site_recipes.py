"""Site recipe loader."""

from nextbrowser_harness.site_recipes import expand_recipe, list_recipes, resolve_recipe_id


def test_list_recipes_includes_reddit():
    ids = {r["id"] for r in list_recipes()}
    assert "reddit.com/login" in ids


def test_expand_reddit_login():
    url, actions = expand_recipe(
        "reddit.com/login",
        variables={"username": "u1", "password": "p1"},
    )
    assert url == "https://www.reddit.com/login"
    assert any("u1" in a for a in actions)
    assert any("wait-for:" in a for a in actions)


def test_expand_reddit_upvote():
    _, actions = expand_recipe("reddit.com/upvote")
    assert actions[0].startswith("shadow-click:") or ">>" in actions[0]


def test_resolve_recipe_id_from_url():
    site, flow = resolve_recipe_id("login", url="https://www.reddit.com/r/all")
    assert site == "reddit.com"
    assert flow == "login"
