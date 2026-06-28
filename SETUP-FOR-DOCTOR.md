# Magic Hand — Step-by-Step Guide

Magic Hand reads the relevant entries from **PowerChart**, sends them to your AI
tool (**Doximity GPT / ChatGPT**), and writes the result back into your **Report**.
You set it up once with an AI helper; after that it's one button. You always
review and approve before anything is written into a chart.

---

## Part 1 — Install (once, ~15 min)

Install these (ask IT if needed):
- **Git** — https://git-scm.com
- **Python** — https://python.org (check "Add to PATH")
- **Node.js** — https://nodejs.org

Then open **Terminal / PowerShell** and run, line by line:

```powershell
npm install -g @anthropic-ai/claude-code
git clone https://github.com/plutunieer/magic-hand.git
cd magic-hand
pip install -r requirements.txt
python -m playwright install chromium
```

---

## Part 2 — Set up with the AI helper (once)

1. **Open PowerChart** and your **AI tool in the browser** (Doximity GPT / ChatGPT).
   👉 During setup, use a **test patient** — never a real chart.
2. In the terminal (inside the `magic-hand` folder), start the helper:
   ```powershell
   claude
   ```
3. **Describe your workflow in plain words.** Copy this and fill in your steps:

   > Read CLAUDE.md and set up Magic Hand. My workflow in PowerChart is:
   > 1. I open the **"Results"** tab.
   > 2. I look at the entries from **today and yesterday**.
   > 3. The relevant ones are **labs and findings**.
   > 4. I send those to my AI tool and have it summarize.
   > 5. The result goes into PowerChart on the **"Report"** tab, in the big text box.
   >
   > Ask me whenever you need me to point at something on the screen.

4. The helper will ask questions and say things like *"hover your mouse over the
   Results tab so I can see it."* Just follow along. It builds and tests the steps.

That's it — you won't do this again.

---

## Part 3 — Daily use (one button)

1. Open **PowerChart** and your **AI tool** as usual.
2. In the terminal: `python -m praxishand.main` → a small toolbar appears.
3. Open the patient's chart → click the task button.
4. The app gathers the entries → sends them to the AI → shows you the result.
5. **Read it, edit if needed, click "Approve".** It's written into the Report.

(If you don't approve, nothing is written.)

---

## If something doesn't work

Start `claude` again and describe the problem in plain words, e.g.
*"it can't find the list of entries"* — the helper fixes it right there.
**No reinstall ever** — for updates just run `git pull`.

---

## Notes
- Daily use needs **no AI/API key** — only the `claude` helper does, and only
  during setup/repair.
- The helper never reads patient data or writes to a real chart without approval.
- A terminal AI agent on a clinical PC needs **IT approval**.
