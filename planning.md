# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
FitFindr is a multi-tool AI agent that helps users find secondhand clothing and figure out how to wear it. It searches a listings dataset for matching items, suggests outfit combinations based on the user's existing wardrobe, and generates a shareable fit card caption. If any step fails — for example, if no listings match — the agent communicates what went wrong and stops rather than passing bad data to the next tool.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): gives the description of the piece of clothing in terms of its looks
- `size` (str): Gives the size of the piece of clothing, either standard, or W30, L30. None indicating no price filter. 
- `max_price` (float): The maximum price the user is ready to pay for the piece of clothing. 

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A list of listing dicts (may be empty). Each dict contains all original listing fields: id, title, description, category, style_tags, size, condition, price, colors, brand, platform. List is sorted descending by relevance score (count of description words and style_tags that appear in the listing's title, description, or style_tags). Returns [] if no listings match.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
Shoudl return an empty list. The agent should comunicate the message that something went wrong and nothing could be matched to the user's choices. It should be clear when saying that it couldn't find anything instead of passing bad data, which reduces the reliability of the tool.
---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a specific listing item and the user's wardrobe, calls the LLM to suggest one or more complete outfit combinations using the new item paired with existing wardrobe pieces.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A single listing dict returned by search_listings, giving the title, category, colors, style_tags, condition, price, platform.
- `wardrobe` (dict): A wardrobe dict with an "items" key containing a list of wardrobe item dicts. Each wardrobe item has: id, name, category, colors, style_tags, notes. May have an empty items list.

**What it returns:**
<!-- Describe the return value -->
A string containing 1–2 outfit suggestions in plain English. Each suggestion names specific wardrobe pieces (by name field) and describes how to style them together. If the wardrobe is empty, returns general styling advice for the item based on its style_tags and colors alone (e.g. "This flannel pairs well with straight-leg jeans and chunky boots for a grunge look."). Never returns an empty string — always returns something actionable.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If wardrobe["items"] is empty, skips wardrobe references and returns general LLM-generated styling advice for the item on its own. If the LLM call raises an exception, returns the string: "Outfit suggestion unavailable right now — try describing your wardrobe and I can help manually."

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Takes the outfit suggestion and the selected listing item and asks the LLM to write a 2–4 sentence caption in a casual, social-media voice — the kind someone would post with their OOTD on Instagram or TikTok. Mentions the item name, price, and platform naturally once each.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit`. Must be non-empty; guarded before the LLM is called.
- `new_item` (dict): The listing dict for the thrifted item. Fields used in the prompt: `title`, `price`, `platform`.

**What it returns:**
<!-- Describe the return value -->
Calls the LLM to generate a short, shareable caption describing the complete outfit — written in a casual, social-media voice as if the user is posting about their thrifted find. 


**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If `outfit` is an empty string or None, returns the error string: "Fit card could not be created — outfit description was empty." Does not call the LLM. If the LLM call raises an exception, returns: "Fit card unavailable right now." Never raises an exception to the caller.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The agent runs a linear loop with early-exit on failure. Here is the exact
conditional logic:

1. Call search_listings(description, size, max_price) with values parsed from
   the user's query.
2. Check if results == []:
   - YES → set session["error"] = "No listings found for '[description]' in
     size [size] under $[max_price]. Try a broader description or a higher
     budget." Set session["selected_item"] = None. Return session immediately.
     Do NOT proceed to step 3.
   - NO → set session["selected_item"] = results[0] (top relevance match).
     Clear session["error"].
3. Call suggest_outfit(session["selected_item"], wardrobe).
   - Store result in session["outfit_suggestion"] regardless of whether wardrobe
     was empty (the tool handles that internally).
4. Check if session["outfit_suggestion"] is an empty string:
   - YES → set session["error"] = "Could not generate outfit suggestion."
     Return session. Do NOT proceed to step 5.
   - NO → continue.
5. Call create_fit_card(session["outfit_suggestion"], session["selected_item"]).
   Store result in session["fit_card"].
6. Return session.

The loop does NOT call all three tools unconditionally — steps 3–5 are only
reached if step 2 produced a valid result.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

All state lives in the `session` dict initialized by `_new_session()` in `agent.py`. No data is passed directly between tools as function arguments — each tool reads its inputs from `session` and writes its output back into `session`. This means every step of the loop can inspect or log the full state at any point.

| Key | Written in step | Read in step | Contents |
|-----|----------------|--------------|----------|
| `query` | init | 1 (parsing) | Raw user input string |
| `parsed` | 1 | 2 | `{description, size, max_price}` extracted from query |
| `search_results` | 2 | 3 | Full list of matching listing dicts |
| `selected_item` | 3 | 4, 5 | Single listing dict — `results[0]` |
| `wardrobe` | init | 4 | User's wardrobe dict passed into `run_agent` |
| `outfit_suggestion` | 4 | 4 (check) + 5 | String returned by `suggest_outfit` |
| `fit_card` | 5 | returned | String returned by `create_fit_card` |
| `error` | 2 or 4 (on failure) | returned | Error message string, or `None` on success |
 
`selected_item` is the key handoff: it is set once from `search_results[0]` and passed into both `suggest_outfit` and `create_fit_card` without the user re-entering anything.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets `session["error"]` = "No listings found for '[description]' in size [size] under $[max_price]. Try a broader description or a higher budget." Returns session immediately — `suggest_outfit` and `create_fit_card` are never called. |
| suggest_outfit | Wardrobe is empty | Uses a fallback LLM prompt asking for general styling advice based on the item's style_tags and colors alone. Returns a non-empty string; the agent continues normally to `create_fit_card`. |
| create_fit_card | Outfit input is missing or incomplete | If `outfit` is empty or None, returns the string "Fit card could not be created — outfit description was empty." without calling the LLM. Never raises an exception. |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     Use ASCII art or a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html).
     Do NOT embed an image — graders need to read your diagram directly in the file;
     an embedded image or screenshot cannot be evaluated.
     You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

     User query (str) + wardrobe (dict)
        │
        ▼
   run_agent()
        │
   Step 1: LLM query parser
        │  → session["parsed"] = {description, size, max_price}
        │
   Step 2: search_listings(description, size, max_price)
        │  → session["search_results"]
        │
        ├── results == [] ──► session["error"] = "No listings found..."
        │                     return session          (early exit)
        │
        │  results = [item, ...]
        │
   Step 3: session["selected_item"] = results[0]
        │
   Step 4: suggest_outfit(selected_item, wardrobe)
        │  → session["outfit_suggestion"]
        │      └── wardrobe empty → fallback: general styling advice
        │
        ├── outfit_suggestion == "" ──► session["error"] = "Could not generate outfit suggestion."
        │                               return session          (early exit)
        │
   Step 5: create_fit_card(outfit_suggestion, selected_item)
        │  → session["fit_card"]
        │      └── outfit empty → returns error string, no crash
        │
   Step 6: return session
        │
        ▼
   {query, parsed, search_results, selected_item,
    wardrobe, outfit_suggestion, fit_card, error} 

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

For `search_listings`: I'll give Claude the Tool 1 spec block from this file (signature, parameters, return value, failure mode) plus the listing field names from `listings.json`, and ask it to implement the function inside `tools.py` using `load_listings()`. Before using it, I'll verify: (1) it calls `load_listings()` rather than re-implementing file reading, (2) size matching is case-insensitive substring, (3) listings scoring 0 are dropped, (4) it returns `[]` without raising on no matches. Then I'll run the three pytest tests from Milestone 3.
 
For `suggest_outfit`: I'll give Claude the Tool 2 spec block plus a sample wardrobe item dict and a sample listing dict (from the schema files), and ask it to implement the function. I'll verify it branches on `len(wardrobe["items"]) == 0`, uses a fallback prompt for the empty case, and returns a non-empty string in both cases. I'll test with `get_example_wardrobe()` and `get_empty_wardrobe()`.
 
For `create_fit_card`: I'll give Claude the Tool 3 spec block including the caption style guidelines and the empty-outfit guard. I'll verify the guard runs before the LLM call, and I'll call the function three times on the same input to confirm output varies (if not, I'll ask Claude to increase the temperature).


**Milestone 4 — Planning loop and state management:**

I'll give Claude the Architecture diagram above and the Planning Loop section (the numbered conditional logic), and ask it to implement `run_agent()` in `agent.py`. Before using the output I'll check: (1) there is an explicit `if results == []` branch that returns early, (2) all results are stored in `session` rather than local variables only, (3) `suggest_outfit` is never called when `search_results` is empty.


---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The agent parses the query using the LLM to extract structured parameters: `description="vintage graphic tee"`, `size=None` (no size mentioned), `max_price=30.0`. These are stored in `session["parsed"]`. Then `search_listings("vintage graphic tee", size=None, max_price=30.0)` is called. It scores all listings by keyword overlap with "vintage graphic tee" across title, description, and style_tags, filters out anything over $30, drops zero-score listings, and returns the remainder sorted by score. Suppose it returns 3 matches; the top result is `{"title": "Faded Band Tee", "price": 22.0, "platform": "depop", ...}`. This list is stored in `session["search_results"]`.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
`results` is non-empty, so the agent sets `session["selected_item"] = session["search_results"][0]` (the Faded Band Tee at $22). Then `suggest_outfit(session["selected_item"], wardrobe)` is called. The wardrobe has items, so the LLM receives a prompt listing the new item's details alongside the wardrobe pieces. It returns: "Pair this faded band tee with your baggy straight-leg dark-wash jeans and chunky white sneakers for a 90s streetwear look. Roll the sleeves once and half-tuck the front for shape." This is stored in `session["outfit_suggestion"]`.

**Step 3:**
<!-- Continue until the full interaction is complete -->
`outfit_suggestion` is non-empty, so the agent calls `create_fit_card(session["outfit_suggestion"], session["selected_item"])`. The LLM receives the outfit description and item details and generates a casual caption. It returns: "thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 full look dropping soon". This is stored in `session["fit_card"]`.

**Final output to user:**
<!-- What does the user actually see at the end? -->
The app displays three panels:
- **Found item:** "Faded Band Tee — $22 on Depop, good condition"
- **Outfit suggestion:** "Pair this faded band tee with your baggy straight-leg dark-wash jeans and chunky white sneakers for a 90s streetwear look. Roll the sleeves once and half-tuck the front for shape."
- **Fit card:** "thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 full look dropping soon"