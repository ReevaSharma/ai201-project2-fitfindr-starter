"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
 
    # Step 2: filter by price and size
    filtered = []
    for listing in listings:
        if max_price is not None and listing["price"] > max_price:
            continue
        if size is not None:
            listing_size = (listing.get("size") or "").lower()
            if size.lower() not in listing_size:
                continue
        filtered.append(listing)
 
    # Step 3: score by keyword overlap with description
    tokens = [t.lower() for t in description.split()]
 
    def score(listing):
        searchable = " ".join([
            listing.get("title", ""),
            listing.get("description", ""),
            " ".join(listing.get("style_tags", [])),
        ]).lower()
        return sum(1 for token in tokens if token in searchable)
 
    # Step 4 & 5: drop zero-score listings, sort highest first
    scored = [(listing, score(listing)) for listing in filtered]
    scored = [(listing, s) for listing, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
 
    return [listing for listing, _ in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    
    try:
        client = _get_groq_client()
 
        item_summary = (
            f"Item: {new_item.get('title', 'Unknown item')}\n"
            f"Category: {new_item.get('category', 'unknown')}\n"
            f"Colors: {', '.join(new_item.get('colors', []))}\n"
            f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
            f"Condition: {new_item.get('condition', 'unknown')}"
        )
 
        # Step 1: check if wardrobe is empty
        wardrobe_items = wardrobe.get("items", [])
 
        if not wardrobe_items:
            # Step 2: fallback prompt for empty wardrobe
            prompt = (
                f"A user just thrifted this item:\n{item_summary}\n\n"
                "They haven't told me what else they own. Give them general styling advice: "
                "what categories of clothing pair well with this item, what aesthetic or vibe it suits, "
                "and one specific styling tip (e.g. how to tuck it, what shoes work, etc.). "
                "Keep it to 2–3 sentences, casual and practical."
            )
        else:
            # Step 3: build wardrobe context and ask for specific combinations
            wardrobe_lines = []
            for item in wardrobe_items:
                notes = f" ({item['notes']})" if item.get("notes") else ""
                wardrobe_lines.append(
                    f"- {item['name']} [{item['category']}], "
                    f"colors: {', '.join(item.get('colors', []))}, "
                    f"tags: {', '.join(item.get('style_tags', []))}{notes}"
                )
            wardrobe_summary = "\n".join(wardrobe_lines)
 
            prompt = (
                f"A user just thrifted this item:\n{item_summary}\n\n"
                f"Here is their current wardrobe:\n{wardrobe_summary}\n\n"
                "Suggest 1–2 complete outfit combinations using the new item and specific named pieces "
                "from their wardrobe. For each outfit, name the exact wardrobe pieces and describe the vibe "
                "and one styling tip (e.g. tuck, roll sleeves, layer). Keep it casual and specific — "
                "no generic advice. 3–5 sentences total."
            )
 
        # Step 4: call LLM and return response
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
 
    except Exception as e:
        print(f"DEBUG error: {e}")
        return "Outfit suggestion unavailable right now — try describing your wardrobe and I can help manually."

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Step 1: guard against empty outfit
    if not outfit or not outfit.strip():
        return "Fit card could not be created — outfit description was empty."
 
    try:
        client = _get_groq_client()
 
        title = new_item.get("title", "thrifted find")
        price = new_item.get("price", "")
        platform = new_item.get("platform", "")
 
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else str(price)
 
        # Step 2: build prompt
        prompt = (
            f"Write a 2–4 sentence Instagram/TikTok caption for this thrifted outfit.\n\n"
            f"Thrifted item: {title}, {price_str} from {platform}\n"
            f"Outfit: {outfit}\n\n"
            "Rules:\n"
            "- Sound like a real person posting their OOTD, not a product description\n"
            "- Mention the item name, price, and platform naturally — each exactly once\n"
            "- Be specific about the vibe (e.g. '90s grunge', 'soft Y2K', 'clean streetwear')\n"
            "- Keep it under 4 sentences\n"
            "- You can use 1–2 relevant emojis if they fit naturally\n"
            "- Do NOT use hashtags"
        )
 
        # Step 3: call LLM with high temperature for variety
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=1.2,
        )
        return response.choices[0].message.content.strip()
 
    except Exception as e:
        print(f"DEBUG error: {e}")
        return "Outfit suggestion unavailable right now — try describing your wardrobe and I can help manually."