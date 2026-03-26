import os

def generate_playwright_test(history_list, output_path: str):
    """
    Parses the AgentHistoryList from a successful browser-use run and generates
    a deterministic, LLM-free Playwright Pytest script based on the XPaths clicked.
    """
    script_lines = [
        "import pytest",
        "from playwright.async_api import Page, expect",
        "",
        "@pytest.mark.asyncio",
        "async def test_deterministic_flow(page: Page):",
    ]
    
    if not history_list.history:
        print("Warning: No history found to generate deterministic script.")
        return
        
    for step_idx, history in enumerate(history_list.history):
        if not history.model_output or not history.model_output.action:
            continue
            
        interacted_elements = history.state.interacted_element
        
        for action_idx, action in enumerate(history.model_output.action):
            # Extract action payload
            action_data = action.model_dump(exclude_none=True)
            if not action_data:
                continue
                
            action_type = next(iter(action_data.keys()))
            params = action_data[action_type]
            
            # Map element interacted to this action (1:1 mapping in browser-use array)
            el = None
            if interacted_elements and action_idx < len(interacted_elements):
                el = interacted_elements[action_idx]
                
            script_lines.append(f"    # [Step {step_idx}] Action: {action_type} - {params}")
            
            # Build deterministic playwright statements
            if action_type == "go_to_url":
                script_lines.append(f"    await page.goto('{params.get('url')}')")
                
            elif action_type == "click":
                if el and hasattr(el, 'x_path'):
                    script_lines.append(f"    await page.locator('xpath={el.x_path}').click()")
                else:
                    script_lines.append(f"    # Warning: Could not find XPath for clicked element - index {params.get('index')}")
                    
            elif action_type == "input":
                if el and hasattr(el, 'x_path'):
                    text_to_fill = params.get('text', '').replace("'", "\\'")
                    script_lines.append(f"    await page.locator('xpath={el.x_path}').fill('{text_to_fill}')")
                else:
                    script_lines.append(f"    # Warning: Could not find XPath for input text - index {params.get('index')}")
                    
            elif action_type == "press_key":
                script_lines.append(f"    await page.keyboard.press('{params.get('key')}')")
                
            elif action_type == "scroll_down":
                script_lines.append("    await page.evaluate('window.scrollBy(0, window.innerHeight)')")
                
            elif action_type == "scroll_up":
                script_lines.append("    await page.evaluate('window.scrollBy(0, -window.innerHeight)')")
                
            elif action_type == "done":
                script_lines.append(f"    # AI agent concluded task with message: {params.get('text')}")
                
            script_lines.append("")

    script_lines.append("    print('Deterministic script completed successfully.')")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(script_lines))
        
    print(f"\n[AI SUCCESS] Deterministic playwright script generated at: {output_path}")
