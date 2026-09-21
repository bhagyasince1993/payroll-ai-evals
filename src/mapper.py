import csv
import json
from difflib import SequenceMatcher

# Read source/client columns
with open("data/payroll_input.csv", "r") as file:
    reader = csv.DictReader(file)
    source_columns = reader.fieldnames

# Read target schema
with open("data/target_schema.json", "r") as file:
    target_schema = json.load(file)

target_columns = list(target_schema.keys())


def similarity(source, target):
    source = source.lower().replace("_", "")
    target = target.lower().replace("_", "")

    return SequenceMatcher(None, source, target).ratio()


print("\nMAPPING RESULTS")
print("------------------------------")

for source in source_columns:

    best_target = None
    best_score = 0

    for target in target_columns:

        score = similarity(source, target)

        if score > best_score:
            best_score = score
            best_target = target

    print(
        f"{source} -> {best_target} | "
        f"Confidence: {best_score:.2f}"
    )