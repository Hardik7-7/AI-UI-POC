import os
from src.models.schemas import TestSuite, TestScenario


def steps_to_task_string(scenario: TestScenario) -> str:
    """Convert structured steps to a natural language task string for the AI agent."""
    ACTION_TEMPLATES = {
        "open_url":  lambda s: f"Open the URL {s.value}.",
        "wait":      lambda s: f"Wait for {s.value} to be visible." if s.value else "Wait for the page to load.",
        "input":     lambda s: f"Type '{s.value}' into the field.",
        "click":     lambda s: f"Click '{s.value}'.",
        "scroll":    lambda s: f"Scroll down to find '{s.value}'." if s.value else "Scroll down.",
        "assert":    lambda s: f"Verify that '{s.value}' is present.",
    }
    parts = []
    for step in sorted(scenario.steps, key=lambda s: s.step):
        template = ACTION_TEMPLATES.get(step.action)
        if template:
            parts.append(template(step))
        elif step.value:
            parts.append(f"{step.action.capitalize()} '{step.value}'.")
        else:
            parts.append(f"{step.action.capitalize()}.")
    return " ".join(parts)


class CodeGenerator:
    def __init__(self, output_dir="output/generated_tests"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_pytest_file(self, suite: TestSuite, filename="test_suite.py"):
        filepath = os.path.join(self.output_dir, filename)

        script_content = [
            "import pytest",
            "import os",
            "from playwright.async_api import async_playwright",
            "from src.agent.custom_agent import CustomAgent",
            "from langchain_google_genai import ChatGoogleGenerativeAI",
            "",
            "@pytest.fixture",
            "def llm():",
            "    # We initialize the Gemini LLM",
            "    return ChatGoogleGenerativeAI(model='gemini-2.5-flash', temperature=0.1)",
            ""
        ]

        for i, scenario in enumerate(suite.scenarios):
            func_name = f"test_{scenario.scenario_name.lower().replace(' ', '_')}_{i}"

            # Prefer natural_language_task if present; otherwise derive from steps
            if scenario.natural_language_task:
                raw_task = scenario.natural_language_task
            else:
                raw_task = steps_to_task_string(scenario)

            task_str = raw_task.replace('"', '\\"').replace('\\n', ' ')
            if scenario.navigate_url:
                task_str = f"Go to {scenario.navigate_url} and then: {task_str}"

            script_content.extend([
                "@pytest.mark.asyncio",
                f"async def {func_name}(llm):",
                f"    \"\"\"{scenario.description}\"\"\"",
                f"    task = \"{task_str}\"",
                f"    ",
                f"    async with async_playwright() as p:",
                f"        browser = await p.chromium.launch(headless=False, args=['--start-maximized'])",
                f"        context = await browser.new_context(no_viewport=True)",
                f"        page = await context.new_page()",
                f"        ",
                f"        agent = CustomAgent(page, task, llm)",
                f"        is_success, script_history = await agent.run()",
                f"        ",
                f"        await browser.close()",
                f"        ",
                f"        assert is_success, 'CustomAgent failed to complete the task'",
                f"        ",
                f"        # Write deterministic script",
                f"        from src.agent.custom_agent import write_deterministic_script",
                f"        deterministic_path = os.path.join(os.path.dirname(__file__), '..', 'deterministic', '{func_name}_det.py')",
                f"        write_deterministic_script(script_history, deterministic_path, func_name='{func_name}')",
                ""
            ])

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(script_content))

        return filepath
