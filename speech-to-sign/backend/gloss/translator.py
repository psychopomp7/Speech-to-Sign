def english_to_asl_gloss(text: str) -> str:
    text = text.lower()

    # Words that ASL usually drops
    remove_words = {
        "am", "is", "are", "was", "were",
        "the", "a", "an", "to", "of"
    }

    # Simple verb normalization
    verb_map = {
        "going": "go",
        "eating": "eat",
        "drinking": "drink",
        "playing": "play",
        "doing": "do"
    }

    words = text.split()
    gloss_words = []

    for word in words:
        if word in remove_words:
            continue

        # Normalize verb form
        if word in verb_map:
            word = verb_map[word]

        gloss_words.append(word.upper())

    # Handle WH-questions (WHAT, WHO, WHERE, etc.)
    wh_words = {"WHAT", "WHO", "WHERE", "WHEN", "WHY", "HOW"}
    normal_words = []
    wh_part = []

    for w in gloss_words:
        if w in wh_words:
            wh_part.append(w)
        else:
            normal_words.append(w)

    final_gloss = normal_words + wh_part

    return " ".join(final_gloss)
