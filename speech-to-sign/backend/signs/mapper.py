from .sign_dictionary import SIGN_DICTIONARY

def gloss_to_signs(gloss: str):
    gloss_words = gloss.split()
    sign_sequence = []

    for word in gloss_words:
        # Known word → direct sign
        if word in SIGN_DICTIONARY:
            sign_sequence.append(SIGN_DICTIONARY[word])
        else:
            # Unknown word → fingerspell letter by letter
            for char in word:
                if char.isalpha():
                    sign_sequence.append(f"FINGER_{char.upper()}")

    return sign_sequence
