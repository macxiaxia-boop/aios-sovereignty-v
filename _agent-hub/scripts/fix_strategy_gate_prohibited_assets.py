"""fix_strategy_gate_prohibited_assets.py — 修 production bug: _scan_for_prohibited_assets
定义在 GateDecision 类外 (module-level), 但 evaluate_envelope 用 self. 调, 找不到.

修法: 把 _scan_for_prohibited_assets 移到 StrategyGate 类内 (放在 _scan_for_prohibited_paths 之后).
"""
import pathlib

p = pathlib.Path(r'D:\AIOS\_agent-hub\policy\strategy_gate.py')
src = p.read_text(encoding='utf-8')

# Step 1: remove the module-level _scan_for_prohibited_assets (between GateDecision end and StrategyGate.__init__)
old_module_method = '''


    def _scan_for_prohibited_assets(self, text: str) -> list[str]:
        """F-NEW-1 fix: Scan for prohibited_active_assets[].summary mentions.
        
        Each PA-XX has a 'summary' field. If envelope text mentions any of these
        active assets (e.g. "CloudTech V22 Gateway", "WorkBuddy user profile"),
        it should be blocked as DEPRECATED_ASSET_REFERENCED.
        """
        hits = []
        if not self.policy:
            return hits
        for pa in self.policy.get("prohibited_active_assets", []) or []:
            pa_id = pa.get("id", "")
            summary = pa.get("summary", "") or ""
            # Match the leading keyword phrase from the summary
            # e.g. "CloudTech V22 Unified Gateway" → match "CloudTech V22"
            # Use first 3 words as a fingerprint
            tokens = summary.split()[:3]
            if len(tokens) < 2:
                continue
            fingerprint = " ".join(tokens)
            if fingerprint in text:
                hits.append(f"{pa_id}({fingerprint})")
        return hits

# ---------------------------------------------------------------- Gate
'''

assert old_module_method in src, "module-level _scan_for_prohibited_assets block not found"
src = src.replace(old_module_method, "")

# Step 2: add it as a method inside StrategyGate class — right after _scan_for_prohibited_paths method
# Find _scan_for_prohibited_paths and add after it
old_paths_method = '''    def _scan_for_prohibited_paths(self, text: str) -> list[str]:
        """F-NEW-1 fix: Scan for prohibited_active_assets[].summary mentions."""
        # (single source of truth for prohibited asset scanning)'''
# This isn't quite right - let me find the right marker.

# Let me find the end of _scan_for_prohibited_paths method
import re
match = re.search(r'(    def _scan_for_prohibited_paths\(self, text: str\) -> list\[str\]:.*?)(\n    def _scan_for_quarantine_paths)', src, re.DOTALL)
if match:
    insert_at = match.end(1)
    new_method = '''

    def _scan_for_prohibited_assets(self, text: str) -> list[str]:
        """F-NEW-1 fix: Scan for prohibited_active_assets[].summary mentions.

        Each PA-XX has a 'summary' field. If envelope text mentions any of these
        active assets (e.g. "CloudTech V22 Gateway", "WorkBuddy user profile"),
        it should be blocked as DEPRECATED_ASSET_REFERENCED.
        """
        hits = []
        if not self.policy:
            return hits
        for pa in self.policy.get("prohibited_active_assets", []) or []:
            pa_id = pa.get("id", "")
            summary = pa.get("summary", "") or ""
            tokens = summary.split()[:3]
            if len(tokens) < 2:
                continue
            fingerprint = " ".join(tokens)
            if fingerprint in text:
                hits.append(f"{pa_id}({fingerprint})")
        return hits
'''
    src = src[:insert_at] + new_method + src[insert_at:]
    p.write_text(src, encoding='utf-8')
    print("production bug fixed: _scan_for_prohibited_assets moved into StrategyGate class")
else:
    print("ERROR: couldn't find insertion location")