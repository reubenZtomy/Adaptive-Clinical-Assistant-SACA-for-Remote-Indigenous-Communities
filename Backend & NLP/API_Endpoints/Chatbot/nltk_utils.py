import numpy as np
import nltk
import re
# nltk.download('punkt')
from nltk.stem.porter import PorterStemmer
_stemmer = PorterStemmer()

def tokenize(sentence: str):
    """
    Simple regex tokenizer:
    - Splits words and keeps punctuation as separate tokens.
    - No NLTK data downloads required.
    """
    return re.findall(r"\w+|[^\w\s]", sentence, flags=re.UNICODE)


def stem(word: str):
    """Lowercase + Porter stem."""
    return _stemmer.stem(word.lower())

def bag_of_words(tokenized_sentence, all_words):
    """
    Return a bag-of-words (1/0) vector for tokenized_sentence w.r.t. all_words.
    """
    tokenized_sentence = [stem(w) for w in tokenized_sentence]
    bag = np.zeros(len(all_words), dtype=np.float32)
    word_index = {w: i for i, w in enumerate(all_words)}
    for w in tokenized_sentence:
        idx = word_index.get(w)
        if idx is not None:
            bag[idx] = 1.0
    return bag