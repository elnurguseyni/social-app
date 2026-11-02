from playwright.sync_api import expect


def test_comment_appears_without_reload(page, live_server):
    page.goto(f"{live_server}/login")
    page.get_by_label("Email").fill("browser@example.com")
    page.get_by_label("Password").fill("browser-test-password")
    page.get_by_role("button", name="Log in", exact=True).click()

    expect(page).to_have_url(f"{live_server}/")

    card = page.locator("article").filter(
        has_text="A post for browser testing"
    )
    comment_box = card.locator(".comment-form textarea")

    page.evaluate("window.browserTestMarker = 'still-here'")

    comment_box.fill("My automated test comment")
    card.get_by_role("button", name="Comment", exact=True).click()

    expect(card.locator(".comment-list")).to_contain_text(
        "My automated test comment"
    )
    expect(comment_box).to_have_value("")
    assert page.evaluate("window.browserTestMarker") == "still-here"