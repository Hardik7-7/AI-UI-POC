import pytest
import os
from playwright.async_api import async_playwright
from src.agent.custom_agent import CustomAgent
from langchain_google_genai import ChatGoogleGenerativeAI

@pytest.fixture
def llm():
    # We initialize the Gemini LLM
    return ChatGoogleGenerativeAI(model='gemini-2.5-flash', temperature=0.1)

@pytest.mark.asyncio
async def test_verify_login_and_library_navigation_0(llm):
    """Tests successful user login and navigation to the Library section of the application."""
    task = "Go to http://fresh-test.corp.coriolis.in/ and then: Open the application URL http://fresh-test.corp.coriolis.in/. Wait for the login page to be visible. Enter 'colama' into the username field and 'coriolis' into the password field. Click the 'Login' button. After successful login and navigation, wait for the 'Machines' section to be visible. Then, click on 'Library' and wait for the Library page to be fully visible."
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()
        
        agent = CustomAgent(page, task, llm)
        is_success, script_history = await agent.run()
        
        await browser.close()
        
        assert is_success, 'CustomAgent failed to complete the task'
        
        # Write deterministic script
        from src.agent.custom_agent import write_deterministic_script
        deterministic_path = os.path.join(os.path.dirname(__file__), '..', 'deterministic', 'test_verify_login_and_library_navigation_0_det.py')
        write_deterministic_script(script_history, deterministic_path, func_name='test_verify_login_and_library_navigation_0')

@pytest.mark.asyncio
async def test_verify_library_image_created_successfully_1(llm):
    """Tests the end-to-end process of logging in, navigating to the Library, and successfully creating a new library image."""
    task = "Go to http://fresh-test.corp.coriolis.in/ and then: Open the application URL http://fresh-test.corp.coriolis.in/. Wait for the login page to be visible. Enter 'colama' into the username field and 'coriolis' into the password field. Click the 'Login' button. After successful login and navigation, wait for the 'Machines' section to be visible. Then, click on 'Library' and wait for the Library page to be fully visible. On the Library page, click 'Add New'. Wait for the 'Provide Basic Details' section to appear. Enter 'TestImage_S2' as the custom name. Click 'Next' through the 'Hardware Details', 'Disks Details', 'CD-ROM Details', 'Network Details', and 'Serial Port Details' sections. Finally, click 'Save'. Wait for the image creation process to complete and then verify that 'TestImage_S2' is present in the Library list."
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()
        
        agent = CustomAgent(page, task, llm)
        is_success, script_history = await agent.run()
        
        await browser.close()
        
        assert is_success, 'CustomAgent failed to complete the task'
        
        # Write deterministic script
        from src.agent.custom_agent import write_deterministic_script
        deterministic_path = os.path.join(os.path.dirname(__file__), '..', 'deterministic', 'test_verify_library_image_created_successfully_1_det.py')
        write_deterministic_script(script_history, deterministic_path, func_name='test_verify_library_image_created_successfully_1')

@pytest.mark.asyncio
async def test_verify_library_image_deployed_and_stopped_2(llm):
    """Tests the full workflow from login, creating a library image, deploying it, and verifying the deployed machine reaches a 'Stopped' state."""
    task = "Go to http://fresh-test.corp.coriolis.in/ and then: Open the application URL http://fresh-test.corp.coriolis.in/. Wait for the login page to be visible. Enter 'colama' into the username field and 'coriolis' into the password field. Click the 'Login' button. After successful login and navigation, wait for the 'Machines' section to be visible. Then, click on 'Library' and wait for the Library page to be fully visible. On the Library page, click 'Add New'. Wait for the 'Provide Basic Details' section to appear. Enter 'TestImage_S3' as the custom name. Click 'Next' through the 'Hardware Details', 'Disks Details', 'CD-ROM Details', 'Network Details', and 'Serial Port Details' sections. Finally, click 'Save'. Wait for the image creation process to complete and then verify that 'TestImage_S3' is present in the Library list. Next, locate 'TestImage_S3' in the Library list and click its 'Deploy' (rocket) icon. Wait for the deploy form to appear. Enter 'TestMachine_S3' as the machine name. Scroll down and click the 'Deploy' button. Wait for the deployment process to initiate. Then, navigate to the 'Machines' section. Wait for the Machines page to be visible and then wait for the deployed machine named 'TestMachine_S3' to reach a 'Stopped' state."
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()
        
        agent = CustomAgent(page, task, llm)
        is_success, script_history = await agent.run()
        
        await browser.close()
        
        assert is_success, 'CustomAgent failed to complete the task'
        
        # Write deterministic script
        from src.agent.custom_agent import write_deterministic_script
        deterministic_path = os.path.join(os.path.dirname(__file__), '..', 'deterministic', 'test_verify_library_image_deployed_and_stopped_2_det.py')
        write_deterministic_script(script_history, deterministic_path, func_name='test_verify_library_image_deployed_and_stopped_2')
