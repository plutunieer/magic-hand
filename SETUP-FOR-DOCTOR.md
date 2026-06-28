# PraxisHand — Setup (via GitHub + Terminal)

No installer. You clone the project and let the **AI helper (Claude Code)** run
everything from the terminal.

## One-time setup (with help, ~15 min)
1. Install **Git**, **Python**, **Node.js**, and **Claude Code**
   (`npm install -g @anthropic-ai/claude-code`).
2. Clone the project:
   `git clone https://github.com/<your-org>/praxis-hand.git`
3. `cd praxis-hand`  →  `pip install -r requirements.txt`  →
   `python -m playwright install chromium`
4. Start the helper: `claude`
   - It reads `CLAUDE.md` and guides the rest: log in to Doximity GPT, and build
     the step sequence by inspecting PowerChart (use a **test patient**, never a
     real chart, during setup).

## Daily use
- `python -m praxishand.main`  → toolbar → open chart → click the button →
  review → approve. (Or just ask `claude` to run it.)

## When something breaks
- Run `claude`, describe the problem in plain words. The agent fixes the step
  sequence right there. **No reinstall — ever:** `git pull` for updates.

## Notes
- Daily use needs **no Claude API**. Only the `claude` helper needs an Anthropic
  login, and only for setup/repair.
- The agent never reads patient data or writes to a real chart without approval.
- A coding agent with terminal access on a clinical PC needs IT approval.
