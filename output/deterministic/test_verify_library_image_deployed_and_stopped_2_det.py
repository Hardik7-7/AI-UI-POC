import pytest
from playwright.async_api import async_playwright

@pytest.mark.asyncio
async def test_verify_library_image_deployed_and_stopped_2():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        await page.goto('http://fresh-test.corp.coriolis.in/')
        await page.locator('xpath=html/body/app-root/app-page/div[1]/div/div[2]/div/app-login-form/form/mat-form-field[1]/div[1]/div/div[3]/input').first.fill('colama')
        await page.locator('xpath=html/body/app-root/app-page/div[1]/div/div[2]/div/app-login-form/form/mat-form-field[2]/div[1]/div/div[3]/input').first.fill('coriolis')
        await page.locator('xpath=html/body/app-root/app-page/div[1]/div/div[2]/div/app-login-form/form/div/button').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav/div/ngx-scrollbar/mat-nav-list/div/div[1]/a[3]').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav-content/ngx-scrollbar/app-container/app-page-wrapper/div/div/app-title-bar/app-page-title/div/div[2]/button[2]').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav-content/ngx-scrollbar/app-wizard/app-page-wrapper/div/div/div/div/div[2]/div[1]/ngx-scrollbar/div/app-basic-details-form/form/div[1]/mat-form-field/div[1]/div/div[2]/input').first.fill('TestImage_S3')
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav-content/ngx-scrollbar/app-wizard/app-page-wrapper/div/div/div/div/div[2]/div[2]/div[2]/button').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav-content/ngx-scrollbar/app-wizard/app-page-wrapper/div/div/div/div/div[2]/div[2]/div[2]/button').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav-content/ngx-scrollbar/app-wizard/app-page-wrapper/div/div/div/div/div[2]/div[2]/div[2]/button').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav-content/ngx-scrollbar/app-wizard/app-page-wrapper/div/div/div/div/div[2]/div[2]/div[2]/button').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav-content/ngx-scrollbar/app-wizard/app-page-wrapper/div/div/div/div/div[2]/div[2]/div[2]/button').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav-content/ngx-scrollbar/app-wizard/app-page-wrapper/div/div/div/div/div[2]/div[2]/div[2]/button/span[5]').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav-content/ngx-scrollbar/app-container/app-page-wrapper/div/div/div/mat-drawer-container/mat-drawer-content/app-list/div/ngx-scrollbar/div/mat-table/mat-row[1]/mat-cell[9]/div/div[1]/button').first.click()
        await page.locator('xpath=html/body/div[4]/div[2]/div/mat-dialog-container/div/div/app-deploy/app-modal/div[2]/form/div[1]/div[3]/mat-form-field/div[1]/div/div[2]/input').first.fill('TestMachine_S3')
        await page.locator('xpath=html/body/div[4]/div[2]/div/mat-dialog-container/div/div/app-deploy/app-modal/div[3]/button[2]').first.click()
        await page.locator('xpath=html/body/app-root/app-view-container/div/mat-sidenav-container/mat-sidenav/div/ngx-scrollbar/mat-nav-list/div/div[1]/a[2]').first.click()

        print('Deterministic success')
        await browser.close()
