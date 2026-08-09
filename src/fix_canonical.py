"""
src/fix_canonical.py
====================
Directly fixes the get_canonical_title function in preprocess.py
by reading the file, finding the exact fallback lines, and replacing them.
Run: python src/fix_canonical.py
"""
from pathlib import Path

path = Path("src/preprocess.py")
lines = path.read_text(encoding="utf-8").splitlines()

fixed = False
i = 0
while i < len(lines):
    # Find the return line with cleaned[:40]
    if "cleaned[:40]" in lines[i] and "return" in lines[i]:
        # Replace this line with return "Other"
        lines[i] = '    return "Other"'
        # Remove the two lines above if they are the cleaned = re.sub lines
        if i >= 2 and "re.sub" in lines[i-1]:
            lines[i-1] = ""
        if i >= 3 and "re.sub" in lines[i-2]:
            lines[i-2] = ""
        print(f"Fixed line {i}: canonical title fallback now returns Other")
        fixed = True
        break
    i += 1

if not fixed:
    print("Line not found. Searching for context...")
    for j, line in enumerate(lines):
        if "cleaned[:40]" in line:
            print(f"  Line {j}: {line}")

# Also fix city aliases - find the vizag entry and add slash variants after it
city_fixed = False
for i, line in enumerate(lines):
    if '"vizag"' in line and "Visakhapatnam" in line:
        # Insert new aliases after this line
        new_lines = [
            '    "bengaluru/bangalore" : "Bengaluru",',
            '    "bangalore/bengaluru" : "Bengaluru",',
            '    "delhi/ncr"           : "Delhi NCR",',
            '    "ncr"                 : "Delhi NCR",',
        ]
        for j, new_line in enumerate(new_lines):
            if new_line.split(":")[0].strip().strip('"') not in "\n".join(lines):
                lines.insert(i + 1 + j, new_line)
        print("City aliases added")
        city_fixed = True
        break

if not city_fixed:
    print("City alias section not found")

# Write back
content = "\n".join(lines)
path.write_text(content, encoding="utf-8")
print("preprocess.py saved.")
print()
print("Now run:")
print("  python src/preprocess.py")
print("  python src/analysis.py")