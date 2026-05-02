# ============================================================
# Manufacturing Troubleshooting Chatbot
# Built on Databricks using LangGraph ReAct Agent + Gradio UI
#
# Team: Testbench Titans | Treasure AI Hackathon
#
# HOW TO RUN:
# 1. Open this in a Databricks notebook
# 2. Run Cell 1 (SQL) to register Unity Catalog functions
# 3. Run Cell 2 (pip install) to install dependencies
# 4. Run Cell 3 (Python) to launch the Gradio chat UI
# ============================================================


# ─────────────────────────────────────────
# CELL 1 — Register Unity Catalog Functions (Run as %sql)
# ─────────────────────────────────────────

# %sql

# -- Function 1: Search historical logs by symptom keyword
# CREATE OR REPLACE FUNCTION treasure_ai_hackathon_solution.testbench_titans.find_related_logs(symptom_text STRING)
# RETURNS TABLE(message_text STRING, equipment_number STRING, causes_brief_text STRING)
# LANGUAGE SQL
# RETURN
# SELECT message_text, equipment_number, causes_brief_text
# FROM treasure_ai_hackathon_datasource.manufacturing_intelligence_agent.data_manufacturing_machine_maintenance_assistant_en
# WHERE LOWER(message_text) LIKE LOWER('%' || symptom_text || '%');


# -- Function 2: Get top causes for a given machine ranked by frequency
# CREATE OR REPLACE FUNCTION treasure_ai_hackathon_solution.testbench_titans.common_causes(equipment_id STRING)
# RETURNS TABLE(cause STRING, count BIGINT)
# LANGUAGE SQL
# RETURN
# SELECT causes_brief_text AS cause, COUNT(*) AS count
# FROM treasure_ai_hackathon_datasource.manufacturing_intelligence_agent.data_manufacturing_machine_maintenance_assistant_en
# WHERE equipment_number = equipment_id
# GROUP BY causes_brief_text
# ORDER BY count DESC;


# -- Function 3: Get average standstill/downtime for a machine
# CREATE OR REPLACE FUNCTION treasure_ai_hackathon_solution.testbench_titans.avg_downtime(equipment_id STRING)
# RETURNS DOUBLE
# LANGUAGE SQL
# RETURN
# SELECT AVG(standstill_time)
# FROM treasure_ai_hackathon_datasource.manufacturing_intelligence_agent.data_manufacturing_machine_maintenance_assistant_en
# WHERE equipment_number = equipment_id;


# -- Function 4: Count how many times a specific issue occurred on a machine
# CREATE OR REPLACE FUNCTION treasure_ai_hackathon_solution.testbench_titans.cnt_by_issue(equipment_id STRING, issue_text STRING)
# RETURNS BIGINT
# LANGUAGE SQL
# RETURN
# SELECT COUNT(*)
# FROM treasure_ai_hackathon_datasource.manufacturing_intelligence_agent.data_manufacturing_machine_maintenance_assistant_en
# WHERE equipment_number = equipment_id
#   AND LOWER(message_text) LIKE LOWER('%' || issue_text || '%');


# -- Function 5: Fetch the most recent log entry for a machine
# CREATE OR REPLACE FUNCTION treasure_ai_hackathon_solution.testbench_titans.latest_issue(equipment_id STRING)
# RETURNS STRING
# LANGUAGE SQL
# RETURN
# SELECT message_text
# FROM treasure_ai_hackathon_datasource.manufacturing_intelligence_agent.data_manufacturing_machine_maintenance_assistant_en
# WHERE equipment_number = equipment_id
# ORDER BY start_date_time DESC
# LIMIT 1;


# ─────────────────────────────────────────
# CELL 2 — Install Dependencies (Run as %python)
# ─────────────────────────────────────────

# %pip install databricks-langchain langchain gradio streamlit "typing_extensions>=4.15.0" "pydantic>=2.13.0"
# dbutils.library.restartPython()


# ─────────────────────────────────────────
# CELL 3 — Agent + Gradio UI (Run as %python)
# ─────────────────────────────────────────

# ── Config ──────────────────────────────

# Unity Catalog location where functions are registered
CATALOG_NAME = "treasure_ai_hackathon_solution"
SCHEMA_NAME  = "testbench_titans"

# LLM config
LLM_ENDPOINT    = "databricks-gpt-oss-120b"
LLM_TEMPERATURE = 0.1

# ── Load UC Tools ────────────────────────

tool_list_raw  = ["find_related_logs", "common_causes", "avg_downtime", "cnt_by_issue", "latest_issue"]
function_names = [f"{CATALOG_NAME}.{SCHEMA_NAME}.{tool}" for tool in tool_list_raw]

print("Registered tools:", function_names)

from databricks_langchain import UCFunctionToolkit
toolkit = UCFunctionToolkit(function_names=function_names)
tools   = toolkit.tools

# ── System Prompt ────────────────────────

SYSTEM_PROMPT = (
    "You are a troubleshooting assistant for manufacturing equipment. "
    "The user will provide only a short symptom description or message title. "
    "Use UC functions to correlate this input with historical logs, identify root causes, "
    "and recommend actionable fixes. When relevant data is found, provide a detailed explanation: "
    "include frequency of occurrence, common causes, downtime impact, and step-by-step recommended actions. "
    "Always explain the reasoning behind your answer so technicians understand why the fix is suggested. "
    "If no relevant data is found, respond with a detailed explanation: "
    "acknowledge the issue, explain possible general causes, and suggest next steps. "
    "If the query is unrelated to manufacturing, politely explain that you are focused on troubleshooting, "
    "but still provide a helpful, general answer if possible."
)

# ── Initialize Agent ─────────────────────

from databricks_langchain import ChatDatabricks
from langgraph.prebuilt import create_react_agent

llm_config     = ChatDatabricks(endpoint=LLM_ENDPOINT, temperature=LLM_TEMPERATURE)
agent_executor = create_react_agent(llm_config, tools, prompt=SYSTEM_PROMPT)

# ── Gradio Chat Handler ──────────────────

import gradio as gr

def troubleshoot_bot(user_query, history):
    try:
        response = agent_executor.invoke({"messages": [("human", user_query)]})
        content  = response["messages"][-1].content

        # Handle list-type content (multi-block responses)
        if isinstance(content, list):
            answer = "\n".join(
                segment["text"] for segment in content
                if isinstance(segment, dict) and segment.get("type") == "text"
            )
        else:
            answer = str(content)

        # If dataset returned a valid answer — enrich with structured detail
        if answer.strip() and answer.strip().lower() not in ["none", "null", "error"]:
            answer += (
                "\n\nDetailed Explanation:\n"
                "- Frequency: Historical occurrence count.\n"
                "- Common Causes: Patterns observed in logs.\n"
                "- Downtime Impact: Average standstill time.\n"
                "- Recommended Actions: Step-by-step fixes.\n"
                "- Reasoning: Why this fix is suggested."
            )
        else:
            # No dataset match — fall back to LLM general knowledge
            detailed_response = llm_config.invoke(
                f"The user asked: '{user_query}'. "
                "This query is outside the dataset scope. Provide a detailed, search-engine style answer "
                "with context, reasoning, and helpful suggestions."
            )
            answer = (
                detailed_response.content
                if hasattr(detailed_response, "content")
                else str(detailed_response)
            )

        return answer.strip()

    except Exception as e:
        return (
            "Sorry, I couldn't process that request. "
            "Here's a general explanation: sometimes issues may not be logged in the dataset. "
            "In such cases, check for recent maintenance, unusual vibrations, or operator notes. "
            f"(Error: {str(e)})"
        )

# ── Launch Gradio UI ─────────────────────

demo = gr.ChatInterface(
    fn=troubleshoot_bot,
    title="Manufacturing Troubleshooting Chatbot",
    description="Provide a short symptom description (e.g., 'Spindle 2 tool does not clamp') and get root cause + recommended fix."
)

demo.launch(share=True)
