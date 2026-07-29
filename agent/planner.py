import os
import json
from typing import List, Dict, Any
from groq import Groq

from agent.tools import get_groq_client, FAST_MODEL, POWERFUL_MODEL
PLANNING_MODEL = POWERFUL_MODEL

def generate_plan(goal: str, memory_context: str = "") -> List[Dict[str, Any]]:
    """
    Generate a step-by-step execution plan based on the user goal.
    Integrates memory context if available.
    """
    print(f"[Planner] Generating execution plan for: '{goal}'")
    
    system_prompt = """You are the Lead Planner in a Hermes-style agent architecture.
Your job is to break down a high-level user research or file generation goal into a logical sequence of discrete steps.

Available tools you can plan steps for:
1. `search_web`: Argument is a search query. Gathers new live web information.
2. `summarize_text`: Argument specifies what to summarize. Compresses retrieved web results or documents.
3. `write_file`: Argument is a target filename (e.g. "report.md"). Saves compiled research results to disk.
4. `read_file`: Argument is a filename to read existing documents or reports from disk.
5. `list_files`: Argument is empty or directory path. Lists all generated research files in reports folder.
6. `query_memory`: Argument is a query topic. Searches past vector memory for historical context.
7. `python_calculator`: Argument is a math expression to evaluate (e.g. "250 * 1.15").
8. `extract_citations`: Argument is text/URL content. Extracts and formats reference citations.
9. `markdown_table_formatter`: Argument is raw data text to format into clean Markdown tables.
10. `text_sentiment_analyzer`: Argument is research text to analyze tone, sentiment, and credibility.

Rules:
- The steps must be sequential and lead logically to fulfilling the user goal.
- Be precise. Limit the plan to 3-6 high-quality steps.
- Select the most appropriate tools for the goal.
- You MUST output a JSON object containing a "steps" key which is a list of steps.
- Each step in the "steps" list must have: "id" (int starting at 1), "tool" (one of the 10 tool names), "argument" (string), and "reason" (string)."""

    user_content = f"Goal: {goal}\n\n"
    if memory_context:
        user_content += f"Here is context from similar past tasks to help optimize your plan:\n{memory_context}\n\n"
        
    user_content += "Create a step-by-step execution plan in JSON format."

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model=PLANNING_MODEL,
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        result_json = json.loads(response.choices[0].message.content)
        steps = result_json.get("steps", [])
        return steps
    except Exception as e:
        print(f"[Planner Warning] Failed to plan with Groq ({e}). Falling back to static default plan.")
        # Return a robust default plan if LLM call fails
        filename = f"research_{goal.replace(' ', '_')[:30].lower()}.md"
        return [
            {
                "id": 1,
                "tool": "search_web",
                "argument": goal,
                "reason": "Initial search to gather data on the goal."
            },
            {
                "id": 2,
                "tool": "summarize_text",
                "argument": "summarize the search results",
                "reason": "Compress search results to make it readable."
            },
            {
                "id": 3,
                "tool": "write_file",
                "argument": filename,
                "reason": "Save the final research report."
            }
        ]
