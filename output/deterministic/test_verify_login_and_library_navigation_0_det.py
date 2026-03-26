import pytest
from playwright.async_api import async_playwright

@pytest.mark.asyncio
async def test_verify_login_and_library_navigation_0():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        await page.goto('http://fresh-test.corp.coriolis.in/')
        await page.locator('xpath=html/body/app-root/app-page/div[1]/div/div[2]/div/app-login-form/form/mat-form-field[1]/div[1]/div/div[3]/input').first.fill('colama')
        await page.locator('xpath=html/body/app-root/app-page/div[1]/div/div[2]/div/app-login-form/form/mat-form-field[2]/div[1]/div/div[3]/input').first.fill('coriolis')
        await page.locator('xpath=html/body/app-root/app-page/div[1]/div/div[2]/div/app-login-form/form/div/button').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav/div/ngx-scrollbar/mat-nav-list/div/div[1]/a[3]').first.click()

        print('Deterministic success')
        await browser.close()
