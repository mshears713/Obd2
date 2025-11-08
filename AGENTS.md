# Agent Specification — Streamlit Dashboard Project

## Purpose
This document defines how Codex should behave when editing or generating code for this project.  
The project is a Streamlit dashboard hosted on a Raspberry Pi, visualizing real-time OBD-II data from a FastAPI backend running on the same Pi.

## Agent Role
Codex acts as the implementation engine.  
The Streamlit Conjurer (external assistant) provides high-level Incantations, which Codex must follow faithfully.

Codex should:
- Make all required code changes described in Incantations
- Keep code simple, readable, and beginner-friendly
- Avoid unnecessary abstractions
- Prefer explicit logic over cleverness
- Maintain compatibility with Pi hardware and performance limitations

## Runtime Environment
- Raspberry Pi (Python 3.x)
- Streamlit serving on Pi: `streamlit run app.py`
- User views the dashboard from an Android device using Pi's LAN IP
- FastAPI backend also runs on the Pi
- User updates code on the Pi via SSH + Git pull

## Development Workflow
Codex should:
1. Modify or generate files according to Incantation instructions
2. Maintain logical structure of the project
3. Avoid major refactors unless explicitly requested
4. Never modify backend code unless directed
5. Never introduce JS front-end frameworks

## Code Style Guidelines
- Use clear variable names
- Add comments sparingly but clearly
- Avoid global state unless absolutely required
- Use `st.session_state` for UI state
- Avoid heavy plotting libraries if performance becomes an issue
- Keep gauge implementations lightweight for Pi performance

## Project Structure Guidelines
- Keep the main dashboard inside `app.py` (unless the user directs a split)
- Place utility functions into lightweight helper modules
- Maintain clarity and modularity without complexity

## Forbidden Behavior
- Do not introduce containerization
- Do not add CI/CD pipelines
- Do not rewrite large portions of the codebase without direction
- Do not use advanced front-end frameworks (React, Vue, JS)
- Do not modify backend logic unless specifically instructed

## Goal
Produce clean, understandable, incremental changes that implement the Conjurer’s instructions and keep the codebase friendly for a beginner–intermediate programmer.
