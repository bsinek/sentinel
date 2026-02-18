# Sentinel System Context

Sentinel is a modular quant research environment for portfolio construction, simulation, and strategy experimentation.
It is a research system, not a trading product or dashboard.
Quantitative methods are implemented as independent modules and evaluated through a consistent experimentation pipeline.

## Core Workflow
portfolio construction -> simulation -> evaluation

## Architecture Direction
- Django + Django REST Framework (DRF) for orchestration and experiment APIs  
- Postgres for experiment data, configurations, and results  
- Celery + Redis for asynchronous simulations and compute workloads  
- Quant engine implemented as independent, modular Python components that integrate without modifying orchestration logic  
- Frontend flexible and replaceable; visualization is not core to system operation  

## Engineering Principles
- modular system design  
- separation of compute and orchestration  
- research-first infrastructure  
- reproducibility over speed  
- incremental system complexity (avoid premature abstraction)  
- avoid premature implementation of advanced quant methods; core quantitative modeling should be user-driven, with Claude primarily assisting infrastructure and scaffolding  




# Global Claude Rules

<tool_use_summary>
After completing a task that involves tool use, provide a quick summary of the work completed
</tool_use_summary>

<do_not_act_before_instructions>
Do not jump into implementatation or changes files unless clearly instructed to make changes. When the user's intent is ambiguous, default to providing information, doing research, and providing recommendations rather than taking action. Only proceed with edits, modifications, or implementations when the user explicitly requests them.
</do_not_act_before_instructions>

<use_parallel_tool_calls>
If you intend to call multiple tools and there are no dependencies between the tool calls, make all of the independent tool calls in parallel. Prioritize calling tools simultaneously whenever the actions can be done in parallel rather than sequentially. For example, when reading 3 files, run 3 tool calls in parallel to read all 3 files into context at the same time. Maximize use of parallel tool calls where possible to increase speed and efficiency. However, if some tool calls depend on previous calls to inform dependent values like the parameters, do NOT call these tools in parallel and instead call them sequentially. Never use placeholders or guess missing parameters in tool calls.
</use_parallel_tool_calls>

<investigate_before_answering>
Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. Make sure to investigate and read relevant files BEFORE answering questions about the codebase. Never make any claims about code before investigating unless you are certain of the correct answer - give grounded and hallucination-free answers.
</investigate_before_answering>