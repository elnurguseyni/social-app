from playwright.sync_api import expect


def test_like_updates_without_reload(page, live_server):
    page.goto(f"{live_server}/login")
    page.get_by_label("Email").fill("browser@example.com")
    page.get_by_label("Password").fill("browser-test-password")
    page.get_by_role("button", name="Log in", exact=True).click()

    expect(page).to_have_url(f"{live_server}/")

    card = page.locator("article").filter(
        has_text="A post for browser testing"
    )

    expect(card.locator(".like-count")).to_have_text("0 likes")
    page.evaluate("window.browserTestMarker = 'still-here'")

    card.get_by_role("button", name="Like", exact=True).click()

    expect(
        card.get_by_role("button", name="Unlike", exact=True)
    ).to_be_visible()
    expect(card.locator(".like-count")).to_have_text("1 likes")

    assert page.evaluate("window.browserTestMarker") == "still-here"