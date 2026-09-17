# CLAUDE.md — VitaAgent

VitaAgent is a Python terminal agent that helps people understand nutrition and why
vitamins and minerals matter. The user types questions in plain English. The agent uses
OpenAI function calling in a loop: it picks tools (local nutrition data, meal analysis,
a saved profile), reads the results, and keeps going until it can give a clear, friendly
answer.

Example questions it must handle:
- "Why is vitamin D important and how do I get enough in winter?"
- "I had porridge, a banana and a chicken salad today. What vitamins am I low on?"
- "Which foods are high in iron and vitamin C?"
- "Make me a simple weekly meal idea list rich in B vitamins."

## Current status

- [x] Plan approved by the user
- [x] Reference-value standard confirmed: **NHS / UK values** (see "Data files")
- [x] Safety rule additions approved (kept in the system prompt)
- [x] M1: setup, config, basic chat (checked by the user with their real key)
- [ ] M2: agent loop + get_vitamin_info. Built and tests pass, but it hasn't been run against
  the real API from Claude's shell, because there's no `.env` in the project folder.
  **Waiting for the user to check it and approve M3.**

Update this section as work moves forward.

## Working rules

1. Build one milestone at a time. When a milestone is done, stop and wait for the user's
   go-ahead before starting the next one.
2. Before calling a milestone done, run the app to check it works (see "Smoke test") and
   run `pytest`.
3. Write tests as you go. Each milestone ships with tests for what it added. Milestone 6
   fills any gaps.
4. Keep files small and focused: one job per module, aim for under ~150 lines, split
   anything that grows past ~200.
5. At the end of each milestone, explain what you built in a few lines and update
   "Current status".
6. Don't add dependencies beyond the tech stack without asking.
7. Only commit when the user asks. Before any commit, check that `git status` does not
   list `.env`.

## Tech stack

- Python 3.11+ (3.13 is installed on this machine)
- `openai` 3.x: Chat Completions API with `tools=` (function calling). The SDK uses
  `httpx2` internally; SDK errors are built from `httpx2.Request`/`httpx2.Response`.
- `rich` 15.x: terminal UI (streamed Markdown, tables, panels, status spinners)
- `python-dotenv`: loads `.env`
- `pytest`: tests
- M7 only: `httpx2` for USDA FoodData Central (already installed with `openai`)

Why Chat Completions: the app owns the full message list, so the loop, history trimming
and mocking stay simple and explicit.

## Setup and commands (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # or call .venv\Scripts\python.exe directly
pip install -e ".[dev]"
Copy-Item .env.example .env         # the user adds their own key to .env
python -m vitaagent                 # also installed as the `vitaagent` command
pytest
```

### Smoke test

Pipe input so the app runs without typing:

```powershell
"Why is vitamin D important?`n/exit" | python -m vitaagent
```

This needs the user's real key in `.env` and uses a few API tokens.

## Config and secrets

- `.env` holds `OPENAI_API_KEY` and `OPENAI_MODEL`. In M7 it also holds an optional
  `USDA_API_KEY`.
- `.env.example` has placeholder values only, e.g. `OPENAI_API_KEY=sk-your-key-here`.
- `.env` goes in `.gitignore` along with `.venv/`, `__pycache__/`, `.pytest_cache/`,
  `*.egg-info/` and the M7 cache folder.
- `config.py` loads settings into a dataclass. The key field uses `repr=False`.
- If a required value is missing, show a friendly message naming the variable and pointing
  to `.env.example`. Never echo the values.
- **Never print, log or commit the API key.** Keep it out of error messages, tracebacks
  shown to the user, and test fixtures (tests use a fake key such as `sk-test-fake`).
- **Claude never reads `.env`.** To check that a variable is set, run a one-liner that
  prints only `True`/`False`.
- Don't send model-specific sampling settings such as `temperature`, because some models
  reject them. Use whatever model `OPENAI_MODEL` names.

## Folder structure

```
termin/
├── CLAUDE.md
├── README.md
├── pyproject.toml              # deps, `vitaagent` script, pytest config
├── .env.example
├── .gitignore
├── data/
│   ├── nutrients.json          # 16 vitamins & minerals: role, low signs, food sources
│   ├── daily_needs.json        # reference intakes + upper limits by age/sex/pregnancy
│   └── foods.json              # ~50 common foods: nutrients per 100 g + typical portion
├── vitaagent/
│   ├── __init__.py
│   ├── __main__.py             # entry point: python -m vitaagent
│   ├── config.py               # load .env, validate, resolve data/profile paths
│   ├── app.py                  # REPL: read input, route commands, run agent turns
│   ├── commands.py             # /profile /reset /help /exit
│   ├── agent/
│   │   ├── loop.py             # agent loop: max steps, tool dispatch, events
│   │   ├── llm.py              # thin OpenAI wrapper (plain call, streaming from M5)
│   │   ├── history.py          # message history + trimming
│   │   └── prompts.py          # system prompt (safety rules + profile summary)
│   ├── tools/
│   │   ├── registry.py         # collects tool schemas; name -> function; safe runner
│   │   ├── data_loader.py      # load + cache JSON, name/alias matching
│   │   ├── vitamins.py         # get_vitamin_info
│   │   ├── needs.py            # intake/upper-limit lookups (M2); get_daily_needs tool (M3)
│   │   ├── foods.py            # search_food_nutrients
│   │   ├── meals.py            # analyse_meal
│   │   ├── user_profile.py     # save_profile / load_profile (not profile.py: clashes with stdlib)
│   │   └── usda.py             # M7: FoodData Central client
│   └── ui/
│       ├── console.py          # shared Rich Console + theme
│       ├── banner.py           # welcome banner, help text
│       └── render.py           # status lines, streamed answer, meal table, panels
└── tests/
    ├── conftest.py             # fixtures: clean env, in-memory Rich console
    ├── fakes.py                # FakeOpenAIClient, FAKE_KEY, SDK error builders
    ├── test_app.py
    ├── test_config.py
    ├── test_prompts.py
    ├── test_data_integrity.py
    ├── test_registry.py
    ├── test_vitamins.py
    ├── test_needs.py
    ├── test_foods.py
    ├── test_meals.py
    ├── test_user_profile.py
    ├── test_history.py
    ├── test_llm.py
    ├── test_loop.py
    ├── test_commands.py
    ├── test_render.py
    └── test_usda.py            # M7
```

## Architecture rules

- **Tools are plain functions.** They take plain arguments and return JSON-serialisable
  dicts. They never print and never import Rich or OpenAI. On bad input they return
  `{"error": "...", ...}` instead of raising.
- **The loop knows nothing about Rich.** It reports progress through an `AgentEvents`
  protocol (`on_text_delta`, `on_tool_start`, `on_tool_end`). The UI implements it and
  tests use a recorder.
- **The OpenAI client is injected** into `llm.py` and the loop, so tests pass a fake
  client. Tests never make real API or network calls.
- **Tool schemas sit next to their functions.** Each tool module defines `SCHEMA` (OpenAI
  function format) beside its function, and `default_registry()` in `registry.py` pairs
  them. Tool names are defined in one place only.
- `ToolRegistry.run(name, arguments_json)` never raises. Unknown tools, bad JSON, wrong
  argument names and tool exceptions all come back as `{"error": ...}`.
- **Reference intakes and upper limits live only in `data/daily_needs.json`.** Other tools
  read them from there and never copy the numbers.
- The data directory and profile path are resolved once, in `config.py`.

## Agent loop

```
run_turn(user_text):
    history.add_user(user_text)
    for step in 1..MAX_STEPS (10):
        reply = llm.complete(history.messages(), tools,
                             tool_choice = "none" if step == MAX_STEPS else "auto")
        history.add_assistant(reply)                # keeps tool_calls on the message
        if not reply.tool_calls:
            return reply.text
        for call in reply.tool_calls:               # the model may request several
            events.on_tool_start(call.name, call.args)
            result = registry.run(call.name, call.arguments_json)   # never raises
            events.on_tool_end(call.name, result)
            history.add_tool_result(call.id, result)
```

- One step is one model call, with a maximum of 10 per question. The last step forces
  `tool_choice="none"` so the user always gets an answer.
- Unknown tool names, invalid JSON arguments and tool exceptions all become `{"error": ...}`
  tool results that go back to the model. They never crash the app.
- OpenAI errors (bad key, rate limit, connection) show a friendly panel. The unfinished turn
  is **rolled back** so history never holds an assistant `tool_calls` message without its
  tool results.
- **History:** the system message is always first and is rebuilt on each call so it
  includes the current profile. When history goes over `MAX_HISTORY_CHARS` (about 40k
  chars, roughly 10k tokens), drop the oldest *whole turns*. A turn is a user message plus
  everything up to the next user message. Never split an assistant `tool_calls` message
  from its tool results, and always keep the current turn.
- **Streaming (M5):** tool-call names and arguments arrive in fragments keyed by `index`.
  Join them before parsing the JSON. Only `llm.py` changes when streaming is added; the
  loop stays the same.

## Tools

Nutrient ids used everywhere: `vitamin_a, vitamin_b1, vitamin_b2, vitamin_b3, vitamin_b6,
vitamin_b9, vitamin_b12, vitamin_c, vitamin_d, vitamin_e, vitamin_k, iron, calcium,
magnesium, zinc, potassium`.

1. **`get_vitamin_info(name)`**: matches ids, display names and aliases, ignoring case
   ("B12", "vit b12", "cobalamin", "folic acid" → `vitamin_b9`). Returns what it does,
   signs of low levels, best food sources, the reference intake (for the saved profile's
   group, otherwise adults) and the safe upper limit with what it applies to (e.g.
   "supplements only"). If nothing matches, it returns an error plus `did_you_mean`.
2. **`get_daily_needs(age, sex, pregnant=false)`**: finds the life-stage group and returns
   the intake and upper limit for all 16 nutrients, plus the group name and data source.
   It covers ages 1+; under 1 returns a message to speak to a health visitor or GP. It
   rejects bad combinations (e.g. `pregnant` with `sex="male"`).
3. **`search_food_nutrients(food)`**: looks up `foods.json` by exact name or alias, then by
   close match (`difflib`). Returns nutrients per 100 g and per typical portion, units, diet
   tags (vegan, vegetarian) and source. If nothing matches, it returns `did_you_mean`.
   M7 adds USDA as a fallback.
4. **`analyse_meal(foods, age?, sex?, pregnant?)`**: `foods` is a list of
   `{name, grams?}`, and a missing `grams` means one typical portion. It sums the
   nutrients and compares them with daily needs, using the group from the arguments, then
   the profile, then the adult default. It returns the group used, per-nutrient totals, %
   of reference, a status (`low` < 50%, `part_way` 50–99%, `met` ≥ 100%,
   `above_upper_limit`), foods not found, and assumptions. The UI draws a Rich table from
   this result.
5. **`save_profile(age?, sex?, diet_type?)` / `load_profile()`**: stores the profile in
   `~/.vitaagent/profile.json` (override with `VITAAGENT_PROFILE_PATH`). `save_profile`
   merges with the existing profile and validates it. `diet_type` is one of `omnivore`,
   `vegetarian`, `vegan`, `pescatarian`, `other`.

## Data files

- All numbers come from named published sources, and each file records its sources and a
  `checked` date. Don't write figures from memory without checking them against the source.
  `tests/test_data_integrity.py` guards the structure: all 16 nutrients present, ages
  covered with no gaps, upper limits above intakes, and aliases unique.
- **Units per nutrient:** A µg, B1 mg, B2 mg, B3 mg (niacin equivalents), B6 mg,
  B9 µg, B12 µg, C mg, D µg, E mg, K µg, iron mg, calcium mg, magnesium mg, zinc mg,
  potassium mg. Food values use exactly the same units.
- `nutrients.json` → `nutrients{id: {...}}`. Each entry has `name`, `type` (vitamin or
  mineral), `unit`, `aliases`, `what_it_does[]`, `signs_of_low_levels[]`,
  `food_sources[]`, `advice[]` (NHS advice for groups such as pregnancy, vegans and older
  people, plus IU conversions) and `sources[]` (URLs).
  - Facts come from the NHS vitamins and minerals pages.
  - Signs of low levels come from NHS condition pages where they exist, otherwise from NIH
    ODS fact sheets.
- `daily_needs.json` (**standard: NHS / UK values**, chosen by the user):
  - `groups[]`: `{id, label, sex, age_min, age_max (null = no max), intakes{all 16}}`. The
    bands follow PHE 2016: 1, 2–3, 4–6, 7–10, 11–14, 15–18, 19–64, 65–74, 75+. Women are
    split into 19–49 and 50–64, following the NHS iron page (14.8 mg vs 8.7 mg).
  - Vitamins E and K have no UK RNI. Adults use the NHS guide amounts (E: 4 mg men, 3 mg
    women; K: 65 µg, based on 1 µg/kg for a 65 kg person). Children and teens are `null`,
    explained in `intake_notes`.
  - `pregnancy`: `extra{}` holds the COMA increments added to the female group's figures
    (A +100 µg, B1 +0.1 mg, B2 +0.3 mg, B9 +100 µg, C +10 mg). `extra_notes{}` covers
    last-trimester-only increments, and `notes[]` holds the NHS pregnancy advice.
  - `upper_limits{nutrient: [{age_min, age_max, amount, applies_to, note}]}` holds the NHS
    safe upper levels, mostly for supplements. Adults (19+) have one for all 16. The only
    child limit the NHS gives is vitamin D (1–10: 50 µg; 11+: 100 µg). Any other age falls
    back to `no_upper_limit_note` (ask a pharmacist or GP).
- `vitaagent/tools/needs.py` reads this file (`find_group`, `upper_limit_for`,
  `intake_note`). Nothing else reads its numbers directly.
- `foods.json`: about 50 common foods (grains, fruit, veg, dairy, eggs, meat, fish,
  legumes, nuts/seeds). Each food has name, aliases, category, diet tags, typical portion
  (description + grams), nutrients per 100 g, and source ID. Values come from USDA
  FoodData Central. Prefer unfortified entries where UK and US products differ (e.g. milk,
  breakfast cereals).

## Safety rules (must be in the system prompt)

Rules from the user:
1. Always say VitaAgent gives general information, not medical advice.
2. If someone mentions symptoms, medication, pregnancy or a health condition, suggest they
   speak to a GP, pharmacist or dietitian.
3. Warn clearly when a supplement amount goes above the safe upper limit.
4. Don't give extreme or very low calorie diet plans. Keep advice balanced and kind.
5. Keep answers simple and easy to read.

Additions (proposed in planning, pending the user's approval):
6. Use tool data for numbers (intakes, limits, food values). Never invent figures. If the
   data isn't available, say so.
7. One day's food shows gaps for that day. It is not a deficiency, so don't diagnose.
8. For urgent situations (e.g. a child swallowed iron tablets, or severe symptoms), tell
   the person to get urgent medical help straight away (NHS 111 or 999 in the UK).
9. If someone seems to be restricting food heavily or mentions an eating disorder, respond
   kindly and suggest talking to a GP.
10. Ask before saving profile details.

Other system prompt guidance: break mixed dishes (e.g. "chicken salad", "porridge") into
ingredients with estimated grams and state those assumptions. Use the saved profile (age,
sex, diet type) to personalise answers.

## Terminal UI

- Welcome banner: short description, "general information, not medical advice", and
  example questions.
- Status line while each tool runs:
  `get_vitamin_info` → "Looking up vitamin D...",
  `get_daily_needs` → "Checking daily needs...",
  `search_food_nutrients` → "Searching nutrients in spinach...",
  `analyse_meal` → "Adding up your meal...",
  `save_profile` / `load_profile` → "Saving your profile..." / "Loading your profile...".
- The final answer streams as Markdown. The meal analysis shows as a colour-coded table.
- Errors and warnings appear in coloured panels, never as raw tracebacks.
- Commands: `/profile` (view, edit, clear), `/reset` (clear the conversation but keep the
  profile), `/help`, `/exit`. Ctrl+C and Ctrl+D also exit cleanly.

## Milestones

### M1: Project setup, .env handling, basic chat (no tools)
- Build: `pyproject.toml`, `.gitignore`, `.env.example`, `config.py`, `agent/prompts.py`
  (system prompt with safety rules), `agent/llm.py` (plain call), simple history, `app.py`
  REPL with `/exit`, README setup steps.
- Tests: config loads, missing key/model gives a friendly error, key is not in `repr`.
- Done when: install works, the app chats with the model, a missing `.env` shows a clear
  message, and `pytest` passes.

### M2: Agent loop + get_vitamin_info
- Build: `nutrients.json`, `daily_needs.json`, `data_loader.py`, `vitamins.py`,
  `registry.py`, `agent/loop.py` (10-step limit, error-safe dispatch, rollback), history
  trimming, plain status line when a tool runs.
- Tests: alias matching and not-found, data integrity (every nutrient has units, intakes
  and limits for every group), loop with a fake client (plain answer, one tool round,
  several tool calls, unknown tool, bad JSON, step limit), trimming keeps tool-call pairs.
- Done when: "Why is vitamin D important?" calls `get_vitamin_info` and gives an answer
  based on the data.

### M3: get_daily_needs, search_food_nutrients, analyse_meal
- Build: `foods.json` (~50 foods), `needs.py`, `foods.py`, `meals.py`, basic Rich meal
  table.
- Tests: age boundaries and pregnancy groups, fuzzy food matching, portion scaling, meal
  totals/percent/status, unknown foods reported rather than crashing.
- Done when: the porridge/banana/chicken salad question produces a gap table and a
  sensible answer.

### M4: Profile saving + /commands
- Build: `user_profile.py`, profile summary in the system prompt, `commands.py`
  (`/profile`, `/reset`, `/help`, `/exit`).
- Tests: save/load round trip in a temp dir, invalid values rejected, merge behaviour,
  command routing, `/reset` clears history but keeps the profile.
- Done when: the profile survives a restart and changes answers (e.g. vegan iron sources).

### M5: Rich UI polish
- Build: welcome banner, streamed Markdown answers, spinner status lines per tool, coloured
  panels, polished colour-coded meal table.
- Tests: render helpers with `Console(record=True)`, stream handling in `llm.py` (text
  deltas plus fragmented tool-call deltas).
- Done when: a full session looks clean in Windows Terminal.

### M6: Tests for every tool and the loop
- Build: fill the gaps. Cover every tool, loop edge cases (API errors roll back the turn,
  parallel tool calls, step limit), commands, and a leak test (the fake key never appears
  in recorded console output).
- Done when: `pytest` is green with no network access, and every tool and loop path is
  covered.

### M7 (optional): USDA FoodData Central
- Build: `tools/usda.py` (httpx, timeouts), `USDA_API_KEY` in `.env` / `.env.example`.
  Search checks local data first, then USDA when a key is set. Map FDC nutrient numbers to
  our 16 ids, cache results on disk (gitignored), and label each result with its source.
- Tests: mocked HTTP responses, nutrient mapping, missing key or timeout falls back to
  local data without errors.
- Done when: a food not in `foods.json` (e.g. "edamame") returns USDA data.

## Testing conventions

- `tests/fakes.py` provides a `FakeOpenAIClient` that replays scripted replies or raises
  scripted errors (stream chunks are added in M5), plus `FAKE_KEY` and helpers that build
  real SDK errors. Import it with `from fakes import ...`.
- `tests/conftest.py` clears `OPENAI_*` environment variables for every test and provides
  an in-memory `console`. From M4 it also provides a temp profile path.
- No real OpenAI or HTTP calls in tests.
- Test tools directly with plain inputs. Test the loop through the fake client plus an
  event recorder.

## Code conventions

- Type hints everywhere. Use dataclasses for settings and model replies.
- **Always open files with `encoding="utf-8"`.** On Windows the default is cp1252, and the
  data contains "µ".
- Use `pathlib` for paths. Constants (`MAX_STEPS`, `MAX_HISTORY_CHARS`, status thresholds)
  go at the top of the module that owns them.
- User-facing text is friendly and in plain English. Details for developers stay out of
  the UI.
