import json
import os
import random
from typing import List, Dict

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

from nltk_utils import tokenize, stem, bag_of_words
from model import NeuralNet

# ---------------------------
# Helpers to support BOTH schemas:
#   classic: {"tag","patterns","responses"}
#   alt    : {"intent","text","responses"}
# ---------------------------
def get_intents(doc: Dict):
    """
    Returns list of intent dicts from loaded JSON.
    Expects top-level key 'intents'.
    """
    intents = doc.get("intents")
    if not isinstance(intents, list):
        raise ValueError("intents.json must contain a top-level 'intents' array")
    return intents

def get_tag(intent: Dict):
    return intent.get("tag", intent.get("intent"))

def get_patterns(intent: Dict) -> List[str]:
    pts = intent.get("patterns", intent.get("text", []))
    if isinstance(pts, str):
        pts = [pts]
    return pts or []

def get_responses(intent: Dict) -> List[str]:
    rs = intent.get("responses", [])
    if isinstance(rs, str):
        rs = [rs]
    return rs

# ---------------------------
# Load data
# ---------------------------
# Allow overriding intents file via env var SWINSACA_INTENTS
INTENTS_FILE = os.environ.get("SWINSACA_INTENTS", "intents.json")
with open(INTENTS_FILE, "r", encoding="utf-8") as f:
    doc = json.load(f)

intents = get_intents(doc)

all_words = []
tags = []
xy = []   # list of (tokenized_sentence, tag)

IGNORE_TOKENS = {"?", "!", ".", ",", ":", ";", "'", '"', "(", ")", "[", "]", "{", "}"}

for intent in intents:
    tag = get_tag(intent)
    if not tag:
        # Skip malformed intent blocks that have no tag/intent
        continue
    tags.append(tag)

    patterns = get_patterns(intent)
    for pattern in patterns:
        w = tokenize(pattern)
        w = [stem(tok) for tok in w if tok not in IGNORE_TOKENS]
        all_words.extend(w)
        xy.append((w, tag))

# Deduplicate/sort
all_words = sorted(set(all_words))
tags = sorted(set(tags))

# Build training data
X_train = []
y_train = []

for (pattern_words, tag) in xy:
    bag = bag_of_words(pattern_words, all_words)
    X_train.append(bag)
    y_train.append(tags.index(tag))

X_train = np.array(X_train, dtype=np.float32)
y_train = np.array(y_train, dtype=np.int64)

class ChatDataset(Dataset):
    def __len__(self):
        return len(X_train)

    def __getitem__(self, idx):
        return X_train[idx], y_train[idx]

# Hyperparameters
input_size = len(all_words)
hidden_size = 128
output_size = len(tags)
batch_size = 8
learning_rate = 1e-3
num_epochs = 1000  # small dataset usually; adjust as needed

dataset = ChatDataset()
train_loader = DataLoader(dataset=dataset, batch_size=batch_size, shuffle=True, num_workers=0)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = NeuralNet(input_size, hidden_size, output_size).to(device)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

# Train
for epoch in range(num_epochs):
    for (words, labels) in train_loader:
        words = words.to(device)
        labels = labels.to(device)

        outputs = model(words)
        loss = criterion(outputs, labels)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    if (epoch + 1) % 100 == 0 or epoch == 0:
        print(f"epoch {epoch+1}/{num_epochs}, loss={loss.item():.4f}")

print("Training complete.")

# Save
data = {
    "model_state": model.state_dict(),
    "input_size": input_size,
    "hidden_size": hidden_size,
    "output_size": output_size,
    "all_words": all_words,
    "tags": tags,
}
# Save to a name based on the intents file stem for convenience
stem = os.path.splitext(os.path.basename(INTENTS_FILE))[0]
FILE = f"data_{stem}.pth" if stem != "intents" else "data.pth"
torch.save(data, FILE)
print(f"Saved trained data to {FILE}")
