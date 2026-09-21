import csv
import json
from difflib import SequenceMatcher

# Load client/source columns
with open("data/payroll_input.csv", "r") as file:
    reader = csv.DictReader(file)
    source_columns = reader.fieldnames

# Load target schema
with open("data/target_schema.json", "r") as file:
    target_schema = json.load(file)

# Load the correct answers (ground truth)
with open("data/expected_mapping.json", "r") as file:
    expected_mapping = json.load(file)

target_columns = list(target_schema.keys())


def similarity(source, target):
    source = source.lower().replace("_", "")
    target = target.lower().replace("_", "")
    return SequenceMatcher(None, source, target).ratio()


passed = 0
failed = 0

print("\nPAYROLL MAPPING EVAL")
print("-----------------------------------------------")

for source in source_columns:

    best_target = None
    best_score = 0

    for target in target_columns:
        score = similarity(source, target)

        if score > best_score:
            best_score = score
            best_target = target

    expected = expected_mapping[source]

    if best_target == expected:
        result = "PASS"
        passed += 1
    else:
        result = "FAIL"
        failed += 1

    print(
        f"{source}: "
        f"Predicted={best_target} | "
        f"Expected={expected} | "
        f"Score={best_score:.2f} | "
        f"{result}"
    )


total = passed + failed
accuracy = (passed / total) * 100

print("\nEVAL SUMMARY")
print("----------------")
print(f"Total: {total}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Accuracy: {accuracy:.2f}%")