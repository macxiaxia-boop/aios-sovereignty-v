"""fix_strategy_gate_fingerprint.py — Round 3 final: 修 fingerprint logic 过宽匹配.

Root cause: PA-10 summary 含 'install_aios_loop.cmd' → alphanumeric token 'loop' (len 4) match 'loopback-demo'.
修法: 1) token length >= 6; 2) word boundary check; 3) require >= 2 token hits.
"""
import pathlib

p = pathlib.Path(r"D:\AIOS\_agent-hub\policy\strategy_gate.py")
src = p.read_text(encoding="utf-8")

old = '''    def _scan_for_prohibited_assets(self, text: str) -> list[str]:
        """F-NEW-1 + Round 6 A-1: alphanumeric token fingerprint."""
        import re as _re_pa
        hits = []
        if not self.policy:
            return hits
        text_lower = text.lower()
        for pa in self.policy.get("prohibited_active_assets", []) or []:
            pa_id = pa.get("id", "")
            summary = pa.get("summary", "") or ""
            tokens = [t for t in _re_pa.findall(r"[A-Za-z0-9-]+", summary) if len(t) >= 4][:5]
            hit_tokens = [t for t in tokens if t.lower() in text_lower]
            if len(hit_tokens) >= 1:
                hits.append(f"{pa_id}({','.join(hit_tokens[:2])})")
        return hits'''

new = '''    def _scan_for_prohibited_assets(self, text: str) -> list[str]:
        """F-NEW-1 + Round 6 A-1 + Round 3 fix: alphanumeric token fingerprint.

        Round 3 fix: tightened thresholds to prevent false-positive substring matches
        like 'loop' matching 'loopback-demo'. Now requires:
        - alphanumeric token length >= 6 (was >=4), AND
        - at least 2 distinct token hits (was >=1), AND
        - word boundary check (token must NOT be a strict prefix of a longer text token).

        Example fix: PA-10 summary = 'install_aios_loop.cmd ...' previously matched
        'loopback-demo' because 'loop' (4 chars) was a substring of 'loopback'.
        Now requires >= 6-char tokens + 2 hits + boundary check, so 'loop' alone
        no longer matches.
        """
        import re as _re_pa
        hits = []
        if not self.policy:
            return hits
        text_lower = text.lower()
        for pa in self.policy.get("prohibited_active_assets", []) or []:
            pa_id = pa.get("id", "")
            summary = pa.get("summary", "") or ""
            tokens = [t for t in _re_pa.findall(r"[A-Za-z0-9-]+", summary) if len(t) >= 6][:8]
            # Word boundary: token must be its own word in text (not just a prefix)
            # Split text on non-alphanumeric, check exact token presence
            text_words = set(_re_pa.findall(r"[A-Za-z0-9-]+", text_lower))
            hit_tokens = [t for t in tokens if t.lower() in text_words]
            if len(hit_tokens) >= 2:
                hits.append(f"{pa_id}({','.join(hit_tokens[:2])})")
        return hits'''

assert old in src, "_scan_for_prohibited_assets block not found"
src = src.replace(old, new)
p.write_text(src, encoding="utf-8")
print("strategy_gate _scan_for_prohibited_assets tightened (len>=6, >=2 hits, boundary check)")