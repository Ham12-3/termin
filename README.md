# VitaAgent

A friendly AI agent for your terminal that helps you understand nutrition and why
vitamins and minerals matter. Ask questions in plain English, for example:

- "Why is vitamin D important and how do I get enough in winter?"
- "Which foods are high in iron and vitamin C?"

VitaAgent gives general information, not medical advice.

## Setup (Windows PowerShell)

You need Python 3.11 or newer and an OpenAI API key.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Open `.env` and replace the placeholders with your OpenAI API key and a model name.
`.env` is ignored by git, so your key is never committed.

If PowerShell won't run `Activate.ps1`, skip activation and use `.venv\Scripts\python.exe`
in place of `python` in the commands below.

## Run

```powershell
python -m vitaagent
```

Type your question and press Enter. Type `/exit` (or press Ctrl+C) to quit.

## Test

```powershell
pytest
```

The tests never call the real OpenAI API.
