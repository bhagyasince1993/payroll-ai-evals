import csv
import json
import urllib.request

MODEL = "llama3.2:3b"

# Read source payroll data
with open("data/client2_payroll.csv", "r") as file:
    reader = csv.DictReader(file)
    rows = list(reader)
    source_columns = reader.fieldnames

# Read target schema
with open("data/target_schema.json", "r") as file:
    target_schema = json.load(file)

target_columns = list(target_schema.keys())


def ask_llm(source_column, sample_values):

    prompt = f"""
You are a payroll data mapping system.

Source field: {source_column}
Sample values: {sample_values}

Available target fields:
{chr(10).join(target_columns)}

Choose exactly ONE target field that best matches the source field.

Return ONLY the target field name.
Do not explain your answer.
"""

    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")

    request = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result["response"].strip()


print("\nAI MAPPING RESULTS")
print("--------------------------------")

for source in source_columns:

    sample_values = [row[source] for row in rows[:5]]

    prediction = ask_llm(
        source,
        sample_values
    )

    print(f"{source} -> {prediction}")