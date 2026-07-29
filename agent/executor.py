import os
import re
from typing import List, Dict, Any, Callable
from agent.tools import (
    search_web, write_file, summarize_text, read_file, list_files,
    query_memory, python_calculator, extract_citations,
    markdown_table_formatter, text_sentiment_analyzer,
    get_groq_client, FAST_MODEL, POWERFUL_MODEL
)

class ExecutionContext:
    def __init__(self):
        self.search_results: List[str] = []
        self.summaries: List[str] = []
        self.files_written: List[str] = []
        self.logs: List[str] = []
        self.last_output: str = ""

    def get_combined_context(self) -> str:
        """Combine all collected search results and summaries into one context string."""
        context_parts = []
        if self.search_results:
            context_parts.append("--- Gathered Search Results ---")
            context_parts.extend(self.search_results)
        if self.summaries:
            context_parts.append("--- Generated Summaries ---")
            context_parts.extend(self.summaries)
        return "\n\n".join(context_parts)

def execute_step(step: Dict[str, Any], context: ExecutionContext, goal: str, log_callback: Callable[[str], None] = None) -> str:
    """
    Execute a single planned step.
    Updates the execution context and returns a status message.
    """
    step_id = step.get("id")
    tool = step.get("tool")
    argument = step.get("argument")
    reason = step.get("reason")
    
    log_msg = f"Executing Step {step_id}: {tool}('{argument}') - Reason: {reason}"
    print(log_msg)
    if log_callback:
        log_callback(f"[Plan Step {step_id}] Using tool '{tool}' with argument: '{argument}'\nRationale: {reason}")
        
    result_str = ""
    
    if tool == "search_web":
        if log_callback:
            log_callback(f"[Action] Searching the web for: '{argument}'...")
        search_out = search_web(argument)
        context.search_results.append(f"Query: {argument}\nResults:\n{search_out}")
        result_str = f"Found search results for: '{argument}'."
        context.last_output = search_out
        if log_callback:
            snippet = search_out[:400] + "..." if len(search_out) > 400 else search_out
            log_callback(f"[Search Results Summary]\n{snippet}")
            
    elif tool == "summarize_text":
        combined_data = context.get_combined_context()
        if not combined_data:
            combined_data = f"No search data collected yet. Request: {argument}"
            
        if log_callback:
            log_callback("[Action] Summarizing collected research materials using Groq...")
            
        summary_out = summarize_text(combined_data, task_context=f"Goal: {goal}. Instruction: {argument}")
        context.summaries.append(summary_out)
        result_str = f"Generated summary: {summary_out[:100]}..."
        context.last_output = summary_out
        if log_callback:
            log_callback(f"[Summary Output]\n{summary_out}")
            
    elif tool == "write_file":
        if log_callback:
            log_callback(f"[Action] Synthesizing comprehensive research report for: '{argument}'...")
            
        synthesized_report = synthesize_report(goal, context)
        
        if log_callback:
            log_callback(f"[Action] Saving synthesized report to file '{argument}'...")
            
        write_out = write_file(argument, synthesized_report)
        context.files_written.append(argument)
        result_str = write_out
        context.last_output = synthesized_report
        if log_callback:
            log_callback(f"[File Writer Result] {write_out}")

    elif tool == "read_file":
        if log_callback:
            log_callback(f"[Action] Reading document file: '{argument}'...")
        res = read_file(argument)
        context.last_output = res
        result_str = f"Read file '{argument}' ({len(res)} characters)."
        if log_callback:
            log_callback(f"[Reader Output]\n{res[:400]}...")

    elif tool == "list_files":
        if log_callback:
            log_callback("[Action] Listing research files in reports folder...")
        res = list_files(argument)
        context.last_output = res
        result_str = res
        if log_callback:
            log_callback(f"[List Files Output]\n{res}")

    elif tool == "query_memory":
        if log_callback:
            log_callback(f"[Action] Querying vector memory for topic: '{argument}'...")
        res = query_memory(argument)
        context.search_results.append(f"Memory Query: {argument}\nResults:\n{res}")
        context.last_output = res
        result_str = f"Memory search completed for '{argument}'."
        if log_callback:
            log_callback(f"[Memory Query Result]\n{res[:400]}...")

    elif tool == "python_calculator":
        if log_callback:
            log_callback(f"[Action] Calculating expression: '{argument}'...")
        res = python_calculator(argument)
        context.summaries.append(res)
        context.last_output = res
        result_str = res
        if log_callback:
            log_callback(f"[Calculator Result] {res}")

    elif tool == "extract_citations":
        combined = context.get_combined_context()
        if log_callback:
            log_callback(f"[Action] Extracting references and citations...")
        res = extract_citations(combined if combined else argument)
        context.summaries.append(res)
        context.last_output = res
        result_str = "Citations extracted successfully."
        if log_callback:
            log_callback(f"[Citations Result]\n{res}")

    elif tool == "markdown_table_formatter":
        combined = context.get_combined_context()
        if log_callback:
            log_callback(f"[Action] Formatting research findings into Markdown table...")
        res = markdown_table_formatter(combined if combined else argument)
        context.summaries.append(res)
        context.last_output = res
        result_str = "Table formatted successfully."
        if log_callback:
            log_callback(f"[Table Formatter Output]\n{res}")

    elif tool == "text_sentiment_analyzer":
        combined = context.get_combined_context()
        if log_callback:
            log_callback(f"[Action] Analyzing tone and sentiment of research materials...")
        res = text_sentiment_analyzer(combined if combined else argument)
        context.summaries.append(f"Sentiment & Credibility Analysis:\n{res}")
        context.last_output = res
        result_str = "Sentiment analysis completed."
        if log_callback:
            log_callback(f"[Sentiment Analyzer Output]\n{res}")
            
    else:
        result_str = f"Error: Unknown tool '{tool}'"
        if log_callback:
            log_callback(f"[Error] {result_str}")
            
    context.logs.append(f"Step {step_id} ({tool}): {result_str}")
    return result_str

def synthesize_report(goal: str, context: ExecutionContext) -> str:
    """
    Calls Groq to write a professional research report summarizing all collected facts and searches.
    """
    combined_context = context.get_combined_context()
    
    system_prompt = """You are a Principal AI Research Scientist.
Your task is to write a highly professional, beautifully structured, and comprehensive Markdown research report.
Use the collected search results and summaries provided by the user.

Ensure the report contains:
1. A clear Title (using a single `#` tag).
2. Executive Summary.
3. Detailed Findings (organized with proper headings and sub-headings).
4. Sources and Citations (list URLs gathered from search results).
5. Next Steps or Recommendations.

Format with clear headers, lists, and bold text for readability. Avoid generic placeholders."""

    user_content = f"""User Goal: {goal}

Collected Information:
{combined_context}

Write the complete research report:"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model=POWERFUL_MODEL,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Synthesizer Warning] Failed to synthesize report with Groq ({e}). Creating basic fallback report.")
        # Fallback basic report
        sources = []
        for res in context.search_results:
            urls = list(set(re.findall(r'URL: (https?://[^\s]+)', res)))
            sources.extend(urls)
            
        fallback = f"""# Research Report: {goal}

## Executive Summary
This report was generated autonomously to address the goal: "{goal}".

## Detailed Findings
The following research points were accumulated during execution:

"""
        for summary in context.summaries:
            fallback += f"- {summary}\n\n"
            
        if not context.summaries:
            fallback += "No summaries were generated. Below is the raw search logs preview:\n"
            for search in context.search_results:
                fallback += f"### Search Logs\n{search[:500]}...\n\n"
                
        fallback += "\n## Sources\n"
        for s in set(sources):
            fallback += f"- {s}\n"
            
        if not sources:
            fallback += "- Internal Knowledge Base\n"
            
        return fallback
