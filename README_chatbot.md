# Manufacturing Troubleshooting Chatbot

An AI-powered troubleshooting assistant for manufacturing equipment built on **Databricks**. 
The chatbot takes a short symptom description from a technician, queries historical maintenance logs using Unity Catalog (UC) functions, identifies root causes, and recommends step-by-step fixes — all through a conversational Gradio UI.

Built as part of the **Treasure AI Hackathon** by Team **Testbench Titans**.

---

## The Problem It Solves

When a machine on the shop floor throws an error, technicians usually have to manually dig through maintenance logs to figure out what caused it before. This tool automates that — a technician just types the symptom and the agent instantly correlates it with historical data to surface the most likely cause and fix.

---

## Architecture

```
Technician types symptom
        │
        ▼
   Gradio Chat UI
        │
        ▼
  LangGraph ReAct Agent  (databricks-gpt-oss-120b)
        │
        ├──→ find_related_logs()    ← search logs by symptom keyword
        ├──→ common_causes()        ← top causes for a given machine
        ├──→ avg_downtime()         ← average standstill time for machine
        ├──→ cnt_by_issue()         ← how many times this issue occurred
        └──→ latest_issue()         ← most recent log entry for machine
                │
                ▼
        Unity Catalog Functions
                │
                ▼
        Databricks SQL Table
        (manufacturing_intelligence_agent dataset)
                │
                ▼
        Agent synthesizes answer
        → Root cause + recommended fix + reasoning
```

---

## Unity Catalog Functions

All functions are registered under:
`treasure_ai_hackathon_solution.testbench_titans`

| Function | Input | What It Does |
|---|---|---|
| `find_related_logs` | `symptom_text` | Searches message logs for matching symptom keyword |
| `common_causes` | `equipment_id` | Returns top causes ranked by frequency for a machine |
| `avg_downtime` | `equipment_id` | Returns average standstill time for a machine |
| `cnt_by_issue` | `equipment_id`, `issue_text` | Counts how many times a specific issue occurred |
| `latest_issue` | `equipment_id` | Fetches the most recent log entry for a machine |

---

## Dataset

The agent queries this table in Databricks:

```
treasure_ai_hackathon_datasource
  └── manufacturing_intelligence_agent
        └── data_manufacturing_machine_maintenance_assistant_en
```

**Key columns used:**
- `message_text` — description of the issue/symptom
- `equipment_number` — machine identifier
- `causes_brief_text` — root cause logged by technician
- `standstill_time` — how long the machine was down
- `start_date_time` — when the issue occurred

> ⚠️ **Note:** This dataset was available inside the Databricks hackathon environment. If you are running this outside that environment, you will need to connect your own maintenance dataset and update the catalog/schema/table references in the SQL functions accordingly.

---

## Tech Stack

| Component | Technology |
|---|---|
| Platform | Databricks (Notebook) |
| LLM | `databricks-gpt-oss-120b` |
| Agent Framework | LangGraph ReAct Agent |
| LLM Integration | `databricks-langchain` / `ChatDatabricks` |
| Tool Integration | Unity Catalog Function Toolkit |
| UI | Gradio `ChatInterface` |
| Language | Python + SQL |

---

## Setup & Running

### Prerequisites
- Access to a Databricks workspace
- Unity Catalog enabled
- The manufacturing dataset available (or your own dataset substituted)

### Step 1 — Run the SQL cell to register UC functions
Open the notebook and run the first cell (`%sql`) which creates all 5 functions in Unity Catalog under your catalog and schema.

### Step 2 — Install dependencies
```python
%pip install databricks-langchain langchain gradio streamlit "typing_extensions>=4.15.0" "pydantic>=2.13.0"
dbutils.library.restartPython()
```

### Step 3 — Run the Python cell
Run the second cell which:
- Loads the UC tools
- Initializes the LangGraph ReAct agent
- Launches the Gradio chat UI

### Step 4 — Chat with the bot
The Gradio interface will launch with a public share link. Type a symptom like:
```
Spindle 2 tool does not clamp
```
The agent will query the logs and return root cause + recommended fix.

---

## Example Interaction

**Input:**
```
Spindle 2 tool does not clamp
```

**Output:**
```
Based on historical logs for this symptom:

- Frequency: Occurred 14 times in the last 6 months
- Common Causes: Hydraulic pressure drop, worn clamp cylinder seal
- Downtime Impact: Average standstill time of 47 minutes
- Recommended Actions:
  1. Check hydraulic pressure at the clamping unit
  2. Inspect clamp cylinder seal for wear
  3. Verify tool holder condition
- Reasoning: 11 out of 14 occurrences were resolved by replacing the clamp cylinder seal,
  making it the most likely root cause.
```

---

## Known Limitation

The dataset was stored inside the **Databricks hackathon environment** and is no longer accessible outside it. If you want to run this project independently you need to:

1. Bring your own manufacturing maintenance dataset
2. Load it into a Databricks table
3. Update these references in the SQL functions:
```sql
-- Replace this:
FROM treasure_ai_hackathon_datasource.manufacturing_intelligence_agent.data_manufacturing_machine_maintenance_assistant_en

-- With your own table:
FROM your_catalog.your_schema.your_table_name
```
4. Make sure your table has equivalent columns: `message_text`, `equipment_number`, `causes_brief_text`, `standstill_time`, `start_date_time`

---

## What I Learned

- Building AI agents with **LangGraph ReAct** pattern on Databricks
- Registering and calling **Unity Catalog functions** as LLM tools
- Prompt engineering for manufacturing domain specificity
- Handling cases where dataset has no match — falling back to LLM general knowledge
- Building a chat UI with **Gradio** inside a Databricks notebook
