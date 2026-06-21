"""
tests/test_tools.py

Pytest tests for each FitFindr tool. Covers the happy path and every
failure mode described in planning.md.

Run with:
    pytest tests/
"""

from tools import search_listings, suggest_outfit, create_fit_card


# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    """Impossible query — should return [] without raising."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter_case_insensitive():
    """Size matching should be case-insensitive substring."""
    results_upper = search_listings("tee", size="M", max_price=None)
    results_lower = search_listings("tee", size="m", max_price=None)
    assert results_upper == results_lower


def test_search_no_size_filter():
    """Passing size=None should not filter out any listings by size."""
    results_with_size = search_listings("jeans", size="W30", max_price=None)
    results_no_size = search_listings("jeans", size=None, max_price=None)
    assert len(results_no_size) >= len(results_with_size)


def test_search_sorted_by_relevance():
    """First result should have at least as many keyword matches as the last."""
    results = search_listings("vintage denim jacket", size=None, max_price=None)
    if len(results) >= 2:
        # Re-score first and last to verify ordering
        tokens = ["vintage", "denim", "jacket"]
        def score(item):
            text = " ".join([
                item.get("title", ""),
                item.get("description", ""),
                " ".join(item.get("style_tags", [])),
            ]).lower()
            return sum(1 for t in tokens if t in text)
        assert score(results[0]) >= score(results[-1])


def test_search_returns_full_listing_fields():
    results = search_listings("tee", size=None, max_price=None)
    if results:
        item = results[0]
        for field in ["id", "title", "description", "category", "style_tags",
                      "size", "condition", "price", "colors", "platform"]:
            assert field in item, f"Missing field: {field}"


# ── suggest_outfit ────────────────────────────────────────────────────────────

SAMPLE_ITEM = {
    "id": "lst_test",
    "title": "Faded Band Tee",
    "category": "tops",
    "style_tags": ["vintage", "graphic tee", "streetwear"],
    "colors": ["black", "grey"],
    "condition": "good",
    "price": 22.0,
    "platform": "depop",
}

EXAMPLE_WARDROBE = {
    "items": [
        {
            "id": "w_001",
            "name": "Baggy straight-leg jeans, dark wash",
            "category": "bottoms",
            "colors": ["dark blue", "indigo"],
            "style_tags": ["denim", "streetwear", "baggy"],
            "notes": "High-waisted, sits above the hip",
        },
        {
            "id": "w_007",
            "name": "Chunky white sneakers",
            "category": "shoes",
            "colors": ["white"],
            "style_tags": ["sneakers", "chunky", "streetwear"],
            "notes": None,
        },
    ]
}

EMPTY_WARDROBE = {"items": []}


def test_suggest_outfit_with_wardrobe_returns_string():
    result = suggest_outfit(SAMPLE_ITEM, EXAMPLE_WARDROBE)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_empty_wardrobe_returns_string():
    """Empty wardrobe should return general advice, not crash or return ''."""
    result = suggest_outfit(SAMPLE_ITEM, EMPTY_WARDROBE)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_empty_wardrobe_no_exception():
    """Must not raise even with an empty wardrobe."""
    try:
        suggest_outfit(SAMPLE_ITEM, EMPTY_WARDROBE)
    except Exception as e:
        assert False, f"suggest_outfit raised an exception on empty wardrobe: {e}"


# ── create_fit_card ───────────────────────────────────────────────────────────

SAMPLE_OUTFIT = (
    "Pair the faded band tee with baggy dark-wash jeans and chunky white sneakers "
    "for a 90s streetwear look. Half-tuck the front for shape."
)


def test_create_fit_card_returns_string():
    result = create_fit_card(SAMPLE_OUTFIT, SAMPLE_ITEM)
    assert isinstance(result, str)
    assert len(result) > 0


def test_create_fit_card_empty_outfit_returns_error_string():
    """Empty outfit string should return error message, not raise."""
    result = create_fit_card("", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert "empty" in result.lower() or "could not" in result.lower()


def test_create_fit_card_whitespace_outfit_returns_error_string():
    result = create_fit_card("   ", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert "empty" in result.lower() or "could not" in result.lower()


def test_create_fit_card_no_exception_on_empty_outfit():
    """Must not raise even when outfit is empty."""
    try:
        create_fit_card("", SAMPLE_ITEM)
    except Exception as e:
        assert False, f"create_fit_card raised an exception on empty outfit: {e}"


def test_create_fit_card_varies_across_calls():
    """Calling with the same input twice should produce different output (high temperature)."""
    result1 = create_fit_card(SAMPLE_OUTFIT, SAMPLE_ITEM)
    result2 = create_fit_card(SAMPLE_OUTFIT, SAMPLE_ITEM)
    # Not a hard failure if they match by chance, but flag it
    if result1 == result2:
        print("WARNING: create_fit_card returned identical output on two calls — consider raising temperature.")