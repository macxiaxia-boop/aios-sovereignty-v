# R284 TimeSpan Probe · Evidence Manifest

> **Round**: R284.1 (exact-scope cleanup) · 2026-09-29T20:08:00Z
> **Operator**: Claude Code (MiniMax-M3)
> **Purpose**: Preserve small evidence from R284 TimeSpan probe BEFORE deleting `_r284_timespan_test/` per user requirement not to fill disks with unmanaged temporary copies.

---

## 1. Source directory (deleted)

`D:\AIOS\cloudtech-saas\_r284_timespan_test\` — entire directory was R284-generated (probe only, no production use).

Original contents:
- `tester.exe` (18,243,033 B) — WinSW 2.12.0.0 binary
- `tester.xml` (843 B) — probe service descriptor
- `logs/tester.wrapper.log` (712 B) — install/uninstall log

---

## 2. Preserved small evidence (in this directory)

| Original path | Preserved path | Size | SHA256 |
|---|---|---|---|
| `_r284_timespan_test\tester.xml` | `evidence\r284_timespan_probe\tester.xml` | 843 B | `62f540b2620888db6c4e07083a51c1955bc91888c3760af2a4c086fecd12cc9d` |
| `_r284_timespan_test\logs\tester.wrapper.log` | `evidence\r284_timespan_probe\logs\tester.wrapper.log` | 712 B | `61b2de29d028291bfda62616b072cd05dd4e220c08f12e85e5a8bd18513b60e5` |

Both files: **byte-identical** to the originals (verified by SHA256 round-trip after copy).

---

## 3. Hash proof for unretained executable (tester.exe)

Per R284.1 scope: **no second copy** of the probe executable is retained. Hash proof below establishes that `tester.exe` is byte-identical to already-retained WinSW binaries (`cloudtech-saas.exe`, `winsw.exe`), which are kept by the project for ongoing service operation.

| File | Size | SHA256 |
|---|---|---|
| `_r284_timespan_test\tester.exe` | 18,243,033 B | `05b82d46ad331cc16bdc00de5c6332c1ef818df8ceefcd49c726553209b3a0da` |
| `cloudtech-saas.exe` (retained) | 18,243,033 B | `05b82d46ad331cc16bdc00de5c6332c1ef818df8ceefcd49c726553209b3a0da` |
| `winsw.exe` (retained) | 18,243,033 B | `05b82d46ad331cc16bdc00de5c6332c1ef818df8ceefcd49c726553209b3a0da` |

**All three byte-identical.** Safe to delete `tester.exe` without preserving a copy — the binary is already kept under two canonical names.

---

## 4. Probe service record (from wrapper log)

- **Service id**: `CloudTechR284TimeSpanProbe`
- **Service name**: `R284 TimeSpan Probe`
- **Install result**: `Service was installed successfully.` (2026-09-29 20:00:01)
- **Uninstall result**: `Service was uninstalled successfully.` (2026-09-29 20:00:05)
- **Purpose**: Verify which `<resetfailure>` syntax WinSW 2.12 accepts (controlled install probe, not retained in registry).

---

## 5. Cleanup timestamp

- `2026-09-29T20:08:00Z` — evidence manifest written, small files copied, hash-verified, deletion authorized.

---

## 6. Out-of-scope files untouched

The following were deliberately NOT touched by R284.1:
- `D:\AIOS\cloudtech-saas\cloudtech-saas.exe` — retained (hash-identical to deleted tester.exe)
- `D:\AIOS\cloudtech-saas\winsw.exe` — retained (hash-identical to deleted tester.exe)
- `D:\AIOS\cloudtech-saas\cloudtech-saas.xml` — active service descriptor (R284-edited)
- `D:\AIOS\cloudtech-saas\cloudtech-saas.xml.pre_descriptor_R284_*.bak` — R284 backup (preserved)
- `D:\AIOS\cloudtech-saas\start_v22_watchdog.bat` — R284-edited
- `D:\AIOS\cloudtech-saas\start_v22_watchdog.bat.pre_R284_*.bak` — R284 backup (preserved)
- `D:\AIOS\cloudtech-saas\install.cmd`, `uninstall.cmd` — unchanged
- `D:\AIOS\cloudtech-saas\logs\` — service log directory (unchanged)

---

## 7. Cleanup principle

- **No broad/glob target.** Only the entire R284-generated `_r284_timespan_test\` directory was deleted.
- **0 pre-existing user files deleted/moved.** Only R284-generated temporary artifacts cleaned/reorganized.
- **Bytes reclaimed**: 18,244,588 (including 18,243,033 B exe + 843 B xml + 712 B log).