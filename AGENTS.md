# 🧭 AGENTS.md — Codex Field Manual

## Mission Context
You are assisting **Mike**, an electromechanical engineer with beginner–intermediate Python experience.  
The project involves creating a **Raspberry Pi OBD-II data logger and dashboard** that connects to an ELM327 adapter and logs live engine data to `obd_readings.csv`.

## Objective
Guide Mike by:
1. Writing **clear, readable Python code** with detailed inline comments.  
2. Using **modular structure** — small functions, logical file separation.  
3. Ensuring **cross-compatibility** with Raspberry Pi OS and Codespaces.  
4. Preferring **clarity over cleverness** — always explain “why,” not just “what.”

## Workflow Principles
- Always **summarize the plan** before coding.  
- Code should run **standalone** (no obscure dependencies).  
- Include **TODO** notes where improvement or expansion is possible.  
- Use **example data** (generate fake CSV entries if needed) for testing.  
- **Validate imports** — check `python-obd`, `tkinter`, and `FastAPI` before assuming they’re installed.  
- For UI work:  
  - Start with terminal output.  
  - Then a minimal Tkinter interface.  
  - Finally, expand to FastAPI endpoints.  

## Tone & Teaching Style
- Keep explanations **brief but instructive** — assume Mike is capable but learning.  
- Avoid jargon unless it’s defined in-line.  
- Favor **docstrings and comments** over dense code blocks.  
- Never use shorthand that hides logic; prefer explicit readability.  

## Coding Conventions
- Follow PEP 8.  
- Use f-strings, type hints, and logging when relevant.  
- Output structured data as JSON or CSV only.  
- Handle file I/O gracefully (check if files exist, append safely).  

## Testing & Verification
- Include a **fake mode** to simulate data when the OBD device isn’t available.  
- For UI components, add print or log outputs to confirm updates.  
- Suggest **Playwright or pytest** for testing endpoints later.  

## Error Handling
- If something could fail (like serial connection), explain what the user should check.  
- Fail gracefully with helpful messages — not stack traces.  

## Expansion Hooks
- Prepare for a `Stage 2` FastAPI dashboard (with `/api/health` and `/api/sample`).  
- Consider modularity so a future web UI can reuse the same CSV reading logic.  