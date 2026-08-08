"""
src/patch_preprocess.py
=======================
One-time patch script.
Fixes the normalise_education and parse_salary functions in preprocess.py.
Run once: python src/patch_preprocess.py
Then run: python src/preprocess.py
"""
from pathlib import Path

path = Path("src/preprocess.py")
content = path.read_text(encoding="utf-8")

# -----------------------------------------------------------------------
# PATCH 1: Fix normalise_education
# Remove "postgraduate" from full_masters list — it matches "any postgraduate"
# which is NOT a specific Master's degree requirement
# -----------------------------------------------------------------------
old_edu = '''    full_masters = [
        "m.tech", "mba", "pgdm", "mca", "msc", "m.sc",
        "m.com", "mcom", "master", "post graduate", "postgraduate"
    ]'''

new_edu = '''    full_masters = [
        "m.tech", "mba", "pgdm", "mca", "msc", "m.sc",
        "m.com", "mcom", "master", "post graduate"
    ]
    # NOTE: "postgraduate" deliberately excluded — "any postgraduate" in
    # UG/PG format means the degree is optional, not required.'''

if old_edu in content:
    content = content.replace(old_edu, new_edu)
    print("PATCH 1 applied: fixed full_masters list")
else:
    print("PATCH 1 NOT FOUND — checking alternative...")
    # Try to find and report what's there
    if "full_masters" in content:
        idx = content.find("full_masters")
        print("Found full_masters at:", content[idx:idx+200])
    else:
        print("full_masters not found in file at all")

# -----------------------------------------------------------------------
# PATCH 2: Fix parse_salary threshold
# Change 100000 minimum to 80000 to catch more valid salaries
# (some valid annual salaries are 80,000-99,999 rupees)
# -----------------------------------------------------------------------
old_sal = "        if 100000 <= float(n) <= 10000000"
new_sal = "        if 80000 <= float(n) <= 10000000"

if old_sal in content:
    content = content.replace(old_sal, new_sal)
    print("PATCH 2 applied: salary threshold 100000 → 80000")
else:
    print("PATCH 2 NOT FOUND — salary threshold line not found")

# Write the patched file
path.write_text(content, encoding="utf-8")
print()
print("File saved. Now run: python src/preprocess.py")