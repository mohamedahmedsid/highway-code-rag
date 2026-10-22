import json
import re
from pathlib import Path

MAX_CHARS = 2200   # rules longer than this get split into parts
OVERLAP = 200      # how much a part repeats from the previous part
RULE_LINE = re.compile(r"^Rule (H?\d+)\s*$")  # matches lines like "Rule 124"


def split_long(text, size, overlap):
    parts = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind("\n", start, end)
            if cut > start + size // 2:
                end = cut
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [p for p in parts if p]


def split_into_rules(text):
    sections = []
    current_rule = "intro"
    current_lines = []
    for line in text.splitlines():
        match = RULE_LINE.match(line.strip())
        if match:
            if current_lines:
                sections.append((current_rule, "\n".join(current_lines)))
            current_rule = match.group(1)
            current_lines = [line.strip()]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_rule, "\n".join(current_lines)))
    return sections


records = []
for path in sorted(Path("data").glob("*.txt")):
    text = path.read_text(encoding="utf-8")
    for rule, body in split_into_rules(text):
        for n, part in enumerate(split_long(body, MAX_CHARS, OVERLAP)):
            if len(part) < 40:
                continue
            if n > 0 and rule != "intro":
                part = f"Rule {rule} (continued)\n" + part
            records.append(
                {
                    "id": f"{path.stem}-{rule}-{n}",
                    "source": path.stem,
                    "rule": rule,
                    "text": part,
                }
            )

Path("chunks.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

print("Total chunks:", len(records))
rule124 = [r for r in records if r["rule"] == "124"]
print("Rule 124 chunks:", len(rule124))
if rule124:
    print("\nRule 124 contains the table:", "Motorways" in rule124[0]["text"] and "70 (112)" in rule124[0]["text"])