from playwright.sync_api import expect


def test_login_page_displays_form(page, live_server):
    page.goto(f"{live_server}/login")

    expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
    expect(page.get_by_label("Email")).to_be_visible()
    expect(page.get_by_label("Password")).to_be_visible()

def test_user_can_log_in(page, live_server):
    page.goto(f"{live_server}/login")

    page.get_by_label("Email").fill("browser@example.com")
    page.get_by_label("Password").fill("browser-test-password")
    page.get_by_role("button", name="Log in", exact=True).click()

    expect(page).to_have_url(f"{live_server}/")
    expect(
        page.get_by_role("button", name="Log out", exact=True)
    ).to_be_visible()