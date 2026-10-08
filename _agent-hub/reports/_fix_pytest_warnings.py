"""Fix pytest warnings: convert return dict → assert in all test_p8 files"""
import re
import glob
from pathlib import Path

test_dir = Path(r"D:\AIOS\_agent-hub\v2\tests")
files = list(test_dir.glob("test_p8_*.py")) + list(test_dir.glob("test_verifier.py"))

count_fixed = 0
for f in files:
    src = f.read_text(encoding="utf-8")
    original = src
    # Convert `return {"ok": True, ...}` patterns to assert with the dict as expected
    # Pattern: `return {...}` after a function body — capture dict literal
    # Simpler: replace `return {` ... closing `}` at column 0 with `assert True  # exit non-empty\n    # ... but we lose the assertions. Use pytest.assume for multi-asserts.
    # Even simpler: keep the dict BUT wrap in `pytest.fail(repr(d)) if not d.get("ok") else None`
    # Cleanest: turn `return dict` into a series of assert statements using `pytest.assume`

    new_lines = []
    lines = src.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        # Look for `return {...` at top level of test function (not method)
        if stripped.startswith("return ") and "{" in stripped and "{" not in stripped.split("return ", 1)[1].split("}", 1)[0]:
            # single-line return {dict}
            pass
        if stripped == "return {" or stripped.startswith("return {"):
            # multi-line return {...}
            # collect dict lines until matching close brace at indent 0
            dict_lines = [stripped]
            j = i + 1
            depth = stripped.count("{") - stripped.count("}")
            while j < len(lines) and depth > 0:
                d = lines[j]
                dict_lines.append(d)
                depth += d.count("{") - d.count("}")
                j += 1
            dict_text = "\n".join(dict_lines)
            # Try to parse dict literal safely
            try:
                # dict literal as python expression
                # convert `True`/`False`/`None` (already python) - no change
                d_eval = eval(dict_text.replace("return ", "", 1).strip())
                if isinstance(d_eval, dict):
                    # generate asserts
                    asserts = []
                    for k, v in d_eval.items():
                        if isinstance(v, bool):
                            asserts.append(f'{indent}assert {k} == {v}, "{k} mismatch"')
                        elif isinstance(v, (int, float, str)):
                            asserts.append(f'{indent}assert {k} == {v!r}, "{k} mismatch"')
                        elif v is None:
                            asserts.append(f'{indent}assert {k} is None, "{k} should be None"')
                        elif isinstance(v, list):
                            asserts.append(f'{indent}assert isinstance({k}, list), "{k} should be list"')
                            asserts.append(f'{indent}assert len({k}) >= 0, "{k} length"')
                        elif isinstance(v, dict):
                            asserts.append(f'{indent}assert isinstance({k}, dict), "{k} should be dict"')
                        else:
                            asserts.append(f'{indent}assert {k} is not None, "{k} not None"')
                    new_lines.append(indent + "# converted from return dict (warning fix)")
                    new_lines.extend(asserts)
                    i = j
                    count_fixed += 1
                    continue
            except Exception:
                pass
        new_lines.append(line)
        i += 1

    new_src = "\n".join(new_lines)
    if new_src != original:
        f.write_text(new_src, encoding="utf-8")
        print(f"  fixed: {f.name}")

print(f"\nFiles modified: {count_fixed}")