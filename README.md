# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Tool Inventory

Your README submission must document each tool's name, inputs, and return value. **These must exactly match your actual function signatures in `tools.py`.** Your documented interfaces will be checked against your actual function signatures in `tools.py` — if the parameter count or types contradict what's in the code, you may not receive full credit for that tool.

| Tool | Inputs | Return value | Purpose |
|------|--------|-------------|---------|
| `search_listings` | `description (str)`, `size (str \| None)`, `max_price (float \| None)` | `list[dict]` — matching listing dicts sorted by relevance score, or `[]` if nothing matches | Filters the mock listings dataset by keyword relevance, size, and price ceiling |
| `suggest_outfit` | `new_item (dict)`, `wardrobe (dict)` | `str` — 1–2 outfit suggestions naming specific wardrobe pieces, or general styling advice if wardrobe is empty | Calls the LLM to suggest complete outfit combinations using the new item and the user's existing wardrobe |
| `create_fit_card` | `outfit (str)`, `new_item (dict)` | `str` — a 2–4 sentence casual caption suitable for Instagram or TikTok, or an error message string if `outfit` is empty | Calls the LLM to generate a shareable OOTD caption describing the thrifted find and the complete outfit |

---

## Interaction Walkthrough

<!-- Walk through a complete interaction step by step: natural language query → each tool call (and why) → final fit card.
     Walk through this carefully — it's how graders follow your agent's reasoning without a live demo.
     Use a specific example — do not leave this as a template. -->

**User query:** --> "looking for a vintage graphic tee under $30"

**Step 1 — Tool called:**
- Tool: `search_listings`
- Input: `description="vintage graphic tee"`, `size=None`, `max_price=30.0`
- Why this tool: This is always the first step — the agent needs a real listing before it can suggest an outfit or write a caption. The query is parsed by the LLM into structured fields first, then passed to this tool.
- Output: A list of matching listings sorted by relevance. Top result: `Y2K Baby Tee — Butterfly Print`, $18.00, Depop, good condition.


**Step 2 — Tool called:**
- Tool: `suggest_outfit`
- Input: `new_item={"title": "Y2K Baby Tee — Butterfly Print", "price": 18.0, "platform": "depop", ...}`, `wardrobe=<example wardrobe with 10 items>`
- Why this tool: `search_listings` returned a result, so `session["selected_item"]` is set and the agent proceeds. The wardrobe is non-empty, so the LLM receives a prompt listing specific wardrobe pieces and asks for named outfit combinations.
- Output: "To create a nostalgic look, pair the Y2K Baby Tee with the Baggy straight-leg jeans and Chunky white sneakers. Tuck the tee into the jeans to accentuate the baggy fit. For a more laid-back look, layer the Oversized grey crewneck sweatshirt over the tee and pair with the Wide-leg khaki trousers and Black combat boots."

**Step 3 — Tool called:**
- Tool: `create_fit_card`
- Input: `outfit=<suggestion from step 2>`, `new_item={"title": "Y2K Baby Tee — Butterfly Print", "price": 18.0, "platform": "depop", ...}`
- Why this tool: `outfit_suggestion` is non-empty, so the agent proceeds to the final step. The LLM receives the outfit description and item details and is prompted to write a casual, social-media-style caption.
- Output: "I'm obsessing over this soft Y2K vibe I've got going on today, thanks to my new Butterfly Print Baby Tee that I scored for $18.00 on Depop. I paired it with some baggy straight-leg jeans and chunky white sneakers for a fun, retro look 🙌."


**Final output to user:**
Three panels populate in the Gradio UI: the listing panel shows the item title, price, platform, condition, size, brand, colors, and original description; the outfit panel shows the LLM's styled outfit suggestion; the fit card panel shows the shareable caption.

---

## Error Handling and Fail Points

<!-- For each tool, describe the specific failure mode and what your agent does in response.
     This maps to the error handling section of the rubric (F5-C1). -->

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | Returns `[]` — no listings match the description, size, and price filters | Sets `session["error"]` to a specific message including the filters used, e.g. "No listings found for 'designer ballgown' in size XXS under $5.00. Try a broader description, a higher price limit, or remove the size filter." Returns the session immediately — `suggest_outfit` and `create_fit_card` are never called. |
| `suggest_outfit` | `wardrobe["items"]` is empty — the user has no wardrobe items | Uses a fallback LLM prompt that asks for general styling advice based on the item's style tags and colors alone, without referencing any wardrobe pieces. Returns a non-empty string; the agent continues normally to `create_fit_card`. |
| `create_fit_card` | `outfit` is an empty or whitespace-only string | Returns the string `"Fit card could not be created — outfit description was empty."` without calling the LLM. Does not raise an exception. |

---

## Spec Reflection

<!-- Answer both questions with at least 2–3 sentences each. -->

**One way planning.md helped during implementation:**
Writing out the exact conditional logic in the Planning Loop section before touching `agent.py` made implementing `run_agent()` straightforward. Because the spec described the specific branch — "if `results == []`, set `session["error"]` and return immediately, do NOT proceed to `suggest_outfit`" — there was no ambiguity about what the code needed to do. Without that level of specificity, it would have been easy to write a loop that called all three tools unconditionally and only noticed the problem during testing.

**One divergence from your spec, and why:**
The spec described query parsing as a step inside `run_agent()`, but during implementation it made more sense to extract it into a separate `_parse_query()` helper function. This wasn't a functional change — the behavior is identical — but it kept `run_agent()` readable and made the fallback logic (returning `description=query, size=None, max_price=None` on JSON parse failure) easier to isolate and reason about independently of the planning loop steps.

---

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.