import os
import json
import asyncio
from playwright.async_api import Page
from langchain_core.messages import HumanMessage, SystemMessage


def write_deterministic_script(script_history: list, output_path: str, func_name: str = "test_deterministic_flow"):
    """Write a clean, self-contained Playwright test file from a list of script lines."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    lines = [
        "import os",
        "import pytest",
        "from playwright.async_api import async_playwright",
        "",
        "@pytest.mark.asyncio",
        f"async def {func_name}():",
        "    async with async_playwright() as p:",
        "        is_headless = os.getenv('HEADLESS', 'true').lower() == 'true'",
        "        browser = await p.chromium.launch(headless=is_headless, args=['--start-maximized'] if not is_headless else [])",
        "        context = await browser.new_context(no_viewport=True)",
        "        page = await context.new_page()",
        "",
    ]
    # Re-indent each recorded action to 8 spaces to sit inside the `async with` block
    for line in script_history:
        lines.append("        " + line.lstrip())
    lines.append("")
    lines.append("        print('Deterministic success')")
    lines.append("        await browser.close()")
    lines.append("")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[CustomAgent] Deterministic script saved to: {output_path}")


class CustomAgent:
    def __init__(self, page: Page, task: str, llm):
        self.page = page
        self.task = task
        self.llm = llm
        self.max_steps = 40

        # Load dom.js
        dom_js_path = os.path.join(os.path.dirname(__file__), '..', '..', 'dom.js')
        with open(dom_js_path, "r", encoding="utf-8") as f:
            self.dom_js = f.read()

    async def run(self):
        print(f"\n[CustomAgent] Starting task: {self.task}")
        script_history = []

        # Auto-navigate to the initial URL from the task string before the loop
        import re
        url_match = re.search(r'Go to (https?://[^\s]+)', self.task)
        if url_match:
            start_url = url_match.group(1).rstrip('.')
            print(f"[CustomAgent] Navigating to start URL: {start_url}")
            await self.page.goto(start_url, wait_until='domcontentloaded', timeout=30000)
            script_history.append(f"    await page.goto('{start_url}')")

        system_prompt = SystemMessage(content='''You are a precise web automation agent.
You will be given the current URL and a list of interactive elements on the screen.
Your goal is to accomplish the user's task.
Output your response as STRICT JSON matching this schema:
{
  "actions": [
    {
      "action": "click",
      "index": "1"
    },
    {
      "action": "input",
      "index": "2",
      "text": "my-text"
    },
    {
      "action": "done",
      "text": "Task finished successfully"
    }
  ]
}
If clicking a button will navigate to a new page or open a modal, only output actions up to that click, then stop so the page can reload for the next step.
Batch inputs if they are on the same form.
Always respond with valid JSON ONLY. No markdown formatting like ```json.''')

        messages = [system_prompt]

        for step in range(self.max_steps):
            await self.page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(1) # small buffer for dynamic content

            # 1. Execute dom.js
            try:
                # Add it to the global window scope to avoid Python string f-string parsing crashes
                await self.page.add_script_tag(content=f"window.customAgentExtractor = {self.dom_js}")

                # Execute it cleanly
                result = await self.page.evaluate("window.customAgentExtractor({doHighlightElements: false, focusHighlightIndex: -1, viewportExpansion: 0, debugMode: false})")
            except Exception as e:
                print(f"[CustomAgent] Error running dom.js: {e}")
                return False, script_history

            if not result:
                print("[CustomAgent] result from dom.js was None")
                return False, script_history

            dom_map = result.get("map", {})

            # 2. Build DOM string for LLM
            elements_text = []
            for idx, node in dom_map.items():
                # Filter out useless tags for input
                if node.get("isVisible"):
                    tag = node.get("tagName", "")
                    attrs = node.get("attributes", {})
                    # create a clean string
                    attr_str = " ".join([f"{k}='{v}'" for k, v in attrs.items() if k in ['id', 'name', 'placeholder', 'type', 'aria-label', 'value', 'innerText', 'class'] and v])
                    text_content = node.get("text", "")
                    if not text_content and 'innerText' in attrs:
                        text_content = attrs['innerText']
                    elements_text.append(f"[{idx}] <{tag} {attr_str}>{text_content}</{tag}>")

            dom_state = "\\n".join(elements_text)

            prompt = f"Task: {self.task}\\nURL: {self.page.url}\\nInteractive Elements:\\n{dom_state}\\n\\nWhat are the next actions? Return ONLY JSON."
            messages.append(HumanMessage(content=prompt))

            # 3. Call Gemini
            response = await self.llm.ainvoke(messages)
            
            # Standard Langchain AIMessage uses .content
            raw_text = getattr(response, "content", getattr(response, "completion", "")).strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3].strip()

            try:
                parsed = json.loads(raw_text)
                actions = parsed.get("actions", [])
            except json.JSONDecodeError:
                print(f"[CustomAgent] Failed to parse JSON: {raw_text}")
                messages.append(HumanMessage(content="Failed to parse JSON. Please return STRICT JSON."))
                continue

            print(f"[CustomAgent] Step {step}: LLM decided actions: {actions}")
            messages.append(SystemMessage(content=f"Executed actions: {actions}"))

            # 4. Execute Playwright actions & save history
            is_done = False
            for act in actions:
                action_type = act.get("action")
                if action_type == "done":
                    print(f"[CustomAgent] Task Complete: {act.get('text')}")
                    is_done = True
                    break

                # Handle navigation actions from LLM
                if action_type in ("goto", "navigate"):
                    nav_url = act.get("url", "")
                    if nav_url:
                        print(f"[CustomAgent] Navigating to: {nav_url}")
                        await self.page.goto(nav_url, wait_until='domcontentloaded', timeout=30000)
                        script_history.append(f"    await page.goto('{nav_url}')")
                    break  # Let the page reload before next step

                idx = str(act.get("index"))
                if idx not in dom_map:
                    print(f"[CustomAgent] Invalid index {idx}")
                    continue

                xpath = dom_map[idx].get("xpath")
                if not xpath:
                    print(f"[CustomAgent] No XPath for index {idx}")
                    continue

                if action_type == "click":
                    try:
                        await self.page.locator(f"xpath={xpath}").first.click(timeout=3000)
                        script_history.append(f"    await page.locator('xpath={xpath}').first.click()")
                    except Exception as e:
                        print(f"[CustomAgent] Click failed: {e}")
                elif action_type == "input":
                    val = act.get("text", "")
                    try:
                        await self.page.locator(f"xpath={xpath}").first.fill(val, timeout=3000)
                        script_history.append(f"    await page.locator('xpath={xpath}').first.fill('{val}')")
                    except Exception as e:
                        print(f"[CustomAgent] Input failed: {e}")

            if is_done:
                return True, script_history

        print("[CustomAgent] Reached max steps without completing task.")
        return False, script_history
