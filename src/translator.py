import csv
import json

# Load translation rules
with open("data/translation_rules.json", "r") as file:
    translation_rules = json.load(file)

# Load payroll data
with open("data/payroll_input.csv", "r") as file:
    reader = csv.DictReader(file)
    rows = list(reader)

# We already know these mappings for this translation test
field_mapping = {
    "PAY_GRP": "paygroup_code",
    "WORK_ST": "work_state",
    "COST_CTR": "cost_center"
}

print("\nTRANSLATION RESULTS")
print("--------------------------------")

for source_field, target_field in field_mapping.items():

    print(f"\n{source_field} -> {target_field}")

    unique_values = set(row[source_field] for row in rows)

    for value in sorted(unique_values):

        translated_value = translation_rules[target_field].get(
            value,
            "UNKNOWN - NEEDS REVIEW"
        )

        print(f"{value} -> {translated_value}")