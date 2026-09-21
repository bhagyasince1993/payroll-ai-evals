import csv
import json

# Load payroll input
with open("data/payroll_input.csv", "r") as file:
    reader = csv.DictReader(file)
    rows = list(reader)

# Load translation rules used by our system
with open("data/translation_rules.json", "r") as file:
    translation_rules = json.load(file)

# Load expected answers
with open("data/expected_translations.json", "r") as file:
    expected_translations = json.load(file)

# Source field -> target field
field_mapping = {
    "PAY_GRP": "paygroup_code",
    "WORK_ST": "work_state",
    "COST_CTR": "cost_center"
}

passed = 0
failed = 0

print("\nTRANSLATION EVAL")
print("--------------------------------")

for source_field, target_field in field_mapping.items():

    unique_values = sorted(
        set(row[source_field] for row in rows)
    )

    for source_value in unique_values:

        actual = translation_rules.get(
            target_field, {}
        ).get(
            source_value,
            "NEEDS_REVIEW"
        )

        expected = expected_translations.get(
            target_field, {}
        ).get(
            source_value,
            "NEEDS_REVIEW"
        )

        if actual == expected:
            result = "PASS"
            passed += 1
        else:
            result = "FAIL"
            failed += 1

        print(
            f"{source_field}: "
            f"{source_value} -> {actual} | "
            f"Expected={expected} | "
            f"{result}"
        )

total = passed + failed

accuracy = (
    (passed / total) * 100
    if total > 0
    else 0
)

print("\nTRANSLATION EVAL SUMMARY")
print("--------------------------------")
print(f"Total: {total}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Translation Accuracy: {accuracy:.2f}%")