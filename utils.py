# backend/utils.py

def parse_claude_scores(text):
    """
    Transforme le texte de Claude en un score global
    """
    lines = text.strip().split("\n")
    scores = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":")
            try:
                scores[key.strip()] = float(value.strip())
            except:
                scores[key.strip()] = 0.0

    # Score global 0-10 simple
    return round(
        ((scores.get("demand_score", 0) + scores.get("trend_score", 0) - scores.get("competition_score", 0)) / 3) * 10,
        2
    )