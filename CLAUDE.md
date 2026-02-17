# Sentinel Project Context

Sentinel is a full-stack quant research and experimentation platform.

Primary capabilities:
- portfolio optimization
- Monte Carlo simulation
- Brownian motion modeling
- cointegration analysis
- stat arb experimentation
- neural network experimentation later

System architecture direction:
- Django + Django REST Framework (DRF) as system backbone
- Postgres for persistent data
- Celery + Redis for job orchestration
- Quant engine as separate Python modules
- Next.js frontend (replaceable, not core)

Claude should prioritize:
- modular system design
- separation of compute and backend
- production-grade structure
- experimentation flexibility



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