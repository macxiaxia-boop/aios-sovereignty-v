# R286 GIT SIDE EFFECT RECOVERY

- report_id: R286_GIT_SIDE_EFFECT_RECOVERY  
- generated_at: 2026-09-30 01:17:59 +0800  
- audit_timestamp_local: 2026-09-30T14:09:12+08:00  
- stash_unchanged: TRUE  

## 1. Stash identity

- ref: `stash@{0}`  
- commit_sha: `4b26e4e011e2378087bbf63e2e914922c208cd2b`  
- author_time_iso: `2026-09-30 01:17:59 +0800`  
- author_time_unix: `1790702279`  
- subject: WIP on main: 0b964e6 N wave: AIOS_RECONSTRUCTION P7-P9 + WorkBuddy + cross-cloud + 10 new e2e kernels (45/45 PASS)  
- parents: ['0b964e646b46406895eefd816b05363687ee3a0d', 'bd9528b11420909c7ec31101d2f689ba05a79449']  
- author: xinzh <xinzh@users.noreply.github.com>  

## 2. Name-status distribution

| status | count |
|--------|-------|
| A | 138 |
| M | 1 |

## 3. Summary counts (per-file classification)

| classification | count |
|----------------|-------|
| content_diff | 4 |
| content_identical | 1 |
| content_missing | 134 |
| index_only_or_metadata | 0 |

Total classified: **139**  
Files in stash name-status: **139**  
Files in records: **139**  

## 4. Self-check

- records_count == stash_changes_count: **True**  
- classification_sum == records_count: **True**  
- JSON parseable: TRUE (verified via json.load)  

## 5. AIOS_BRIDGE_REGISTRY.json deep check

- path: `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json`  
- path: `"AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json"`  
- stash_blob_sha256: `"6060c040a5a42c48266f518a5e8925650abfd92804794b9411a5fe8aecbbca5a"`  
- stash_size_bytes: `4852`  
- worktree_exists: `true`  
- worktree_sha256: `"2dca43c22ecb1a2cef136395e0ebc68dfec76c78764a27554149165d549488e0"`  
- classification: `"content_diff"`  
- stash_top_level_keys: `["version", "bridges"]`  
- stash_structure_counts: `{"version": "str", "bridges": 9}`  
- worktree_top_level_keys: `["version", "bridges"]`  
- worktree_structure_counts: `{"version": "str", "bridges": 9}`  
- secrets_excluded: True  

## 6. content_diff files (stash vs worktree)

| path | stash sha256[:16] | worktree sha256[:16] | stash size | worktree size | recommended |
|------|-------------------|-------------------|-----------|----------------|-------------|
| `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json` | `6060c040a5a42c48` | `2dca43c22ecb1a2c` | 4852 | 3700 | manual_merge |
| `_agent-hub/memory/2026-09-29.md` | `80883bea660a54cd` | `1bbab3482214760d` | 15080 | 11928 | recover_candidate |
| `_openclaw_18792_watchdog_runner.cmd` | `29f8172426c8668b` | `39b7ff4de26ee37f` | 171 | 702 | manual_merge |
| `_popup_watchdog_parent_state.json` | `7f9d95dba1603db2` | `c4a10db98541a4eb` | 415 | 437 | manual_merge |

## 7. content_missing files

| path | stash sha256[:16] | stash size | recommended |
|------|-------------------|-----------|-------------|
| `_R268_install_watchdog_parent.ps1` | `15bc46404a883d77` | 1051 | recover_candidate |
| `_admin_check_self_elevate.cmd` | `0bd7d6fb925401f4` | 207 | recover_candidate |
| `_admin_check_svc.py` | `e50d1cc50930db1f` | 2940 | recover_candidate |
| `_admin_disable_result.txt` | `50c75764c924c2e6` | 416 | recover_candidate |
| `_admin_disable_self_elevate.cmd` | `7793aefd9fcd4f59` | 215 | recover_candidate |
| `_admin_disable_watchdogs.py` | `56c742bf64cb60e4` | 3474 | recover_candidate |
| `_admin_full_setup.py` | `5f9c93e924730e21` | 6577 | recover_candidate |
| `_admin_full_setup_result.txt` | `e3b0c44298fc1c14` | 0 | recover_candidate |
| `_admin_full_setup_self_elevate.cmd` | `da4e10774152caa2` | 208 | recover_candidate |
| `_admin_register_result.txt` | `60a3a151f2cc67b6` | 151 | recover_candidate |
| `_admin_register_service.py` | `89e751ea6cbc793a` | 5180 | recover_candidate |
| `_admin_self_elevate.cmd` | `1cce860d638cda9b` | 489 | recover_candidate |
| `_agent-hub/CLAUDE.md` | `a6595fa55fec0d95` | 1731 | recover_candidate |
| `_agent-hub/MEMORY.md` | `7250537d3b6cc9f6` | 2764 | recover_candidate |
| `_agent-hub/README.md` | `06e926ecfdd566bb` | 7786 | recover_candidate |
| `_agent-hub/SOUL.md` | `084f0b7ca14d6e5e` | 2745 | recover_candidate |
| `_agent-hub/USER.md` | `d08e26eae602e949` | 1901 | recover_candidate |
| `_agent-hub/install-links.ps1` | `180f5c288c7b724f` | 7780 | recover_candidate |
| `_agent-hub/memory/2026-09-28.md` | `473f4e13a7e8b117` | 4375 | recover_candidate |
| `_agent-hub/memory/45e357fa-c2ec-4bd0-b734-9b016a2759d7_memory.md` | `b8415f112f7695cd` | 5514 | recover_candidate |
| `_agent-hub/memory/automations/291a48ec-f03c-4cd2-9865-3e574ceb1477/memory.md` | `a82dd42fe206242d` | 1326 | recover_candidate |
| `_agent-hub/sync-from-hub.ps1` | `dc3e2740d7a0710c` | 5648 | recover_candidate |
| `_app_exec.txt` | `e3b0c44298fc1c14` | 0 | recover_candidate |
| `_audit_all.py` | `11b6708093027b4f` | 10568 | recover_candidate |
| `_audit_all_report.txt` | `4253da1e0a9188c7` | 20648 | recover_candidate |
| `_clash_verge_watchdog.py` | `348920e8ef7e7918` | 1773 | recover_candidate |
| `_clash_verge_watchdog_runner.cmd` | `5519b7b6aee4c3df` | 322 | recover_candidate |
| `_defender_history.txt` | `c9a6aa3c6af429da` | 886 | recover_candidate |
| `_desktop_screenshot.bmp` | `f713d3a1886f2155` | 8294454 | recover_candidate |
| `_event_log.txt` | `e3b0c44298fc1c14` | 0 | recover_candidate |
| `_eventlog_5min.txt` | `e3b0c44298fc1c14` | 0 | recover_candidate |
| `_gen2.py` | `3efba6d49e6c33f4` | 497 | recover_candidate |
| `_gen3.py` | `b0d3a81c5b92e897` | 397 | recover_candidate |
| `_gen_r1130.py` | `8c437ee4cb974e8d` | 846 | recover_candidate |
| `_heartbeat_test.py` | `a26c07059a462647` | 1122 | recover_candidate |
| `_hide_console_windows.py` | `784be44e7c3c28df` | 2912 | recover_candidate |
| `_hkcu_register.txt` | `ad9edea6f044de13` | 653 | recover_candidate |
| `_hkml_services.txt` | `843f7471eb864109` | 917 | recover_candidate |
| `_kill_aios_daemon_tree.py` | `0b3f1ee0a0750244` | 4806 | recover_candidate |
| `_kill_aios_daemon_tree_v3.py` | `bac0458bd4dfdedc` | 6645 | recover_candidate |
| `_kill_list.txt` | `7a963aa7607f2876` | 8139 | recover_candidate |
| `_kill_vscode_chatgpt.cmd` | `67c1603c1668bbed` | 190 | recover_candidate |
| `_mcp_full.txt` | `b366f17177eef628` | 2502 | recover_candidate |
| `_multi_watchdog.py` | `e9fde71e7fa74483` | 1123 | recover_candidate |
| `_multi_watchdog_runner.cmd` | `602b1c3784eed14c` | 436 | recover_candidate |
| `_multi_watchdog_runner.vbs` | `596bde95c4c4c061` | 260 | recover_candidate |
| `_multi_watchdog_runner_inner.cmd` | `bde1da4bd875648e` | 179 | recover_candidate |
| `_openai_codex_beta_watchdog.py` | `b17f7060d43adac4` | 7675 | recover_candidate |
| `_openai_codex_beta_watchdog_runner.cmd` | `8faae32225b0c1bc` | 337 | recover_candidate |
| `_openai_codex_desktop_watchdog.DISABLED` | `e9f8c0fe74060fb4` | 324 | recover_candidate |
| `_openai_codex_desktop_watchdog.py` | `b4eb81a3c2102e73` | 2672 | recover_candidate |
| `_openclaw_18792_watchdog.cooldown` | `875435b625a95c2b` | 19 | recover_candidate |
| `_openclaw_18792_watchdog.py` | `3e10bb140465532b` | 2248 | recover_candidate |
| `_pid_15408.txt` | `0ebb7aea102267aa` | 2004 | recover_candidate |
| `_popup_ultimate_shield.py` | `cbc902eef7ab5646` | 8365 | recover_candidate |
| `_popup_watchdog_parent.py` | `fd73494758cc094e` | 9489 | recover_candidate |
| `_popup_watchdog_parent_supervisor.py` | `30de85caa196f26c` | 5861 | recover_candidate |
| `_proc_count.txt` | `09915074a768ab65` | 681 | recover_candidate |
| `_proc_inventory.txt` | `af088ac78225b115` | 843 | recover_candidate |
| `_proc_python_cmd.txt` | `00da2ea1040bc892` | 12926 | recover_candidate |
| `_proc_python_cmd_now.txt` | `f8dfb96af9b7bf2c` | 9838 | recover_candidate |
| `_proc_snoop.py` | `1c9b4308a54dde3f` | 4038 | recover_candidate |
| `_proc_terminator_snoop.ps1` | `277c9365314c243b` | 2517 | recover_candidate |
| `_r1130_gen.py` | `8c8fd2252a1ec43e` | 756 | recover_candidate |
| `_r1130a.py` | `e3b0c44298fc1c14` | 0 | recover_candidate |
| `_r1130c.py` | `9fc6982c94b55ec3` | 1506 | recover_candidate |
| `_reprowler.txt` | `caf5762337520a47` | 806 | recover_candidate |
| `_schtasks_register.txt` | `e3b0c44298fc1c14` | 0 | recover_candidate |
| `_spawn_monitor.ps1` | `4f630a868a382a25` | 1869 | recover_candidate |
| `_spawn_sources.txt` | `204eda4651ec3bf3` | 8750 | recover_candidate |
| `_watchdog_alive_check_multi.py` | `e30973238db344eb` | 9470 | recover_candidate |
| `_watchdog_alive_check_multi_history.json` | `530311ba8081a1d1` | 382 | recover_candidate |
| `_watchdog_alive_check_multi_state.json` | `b4ffe4c8e7863879` | 325 | recover_candidate |
| `_wetype_info.txt` | `eb7b1526b13a4047` | 3055 | recover_candidate |
| `_wr1130.py` | `b4df04b1d70d43bf` | 1544 | recover_candidate |
| `_wr1130b.py` | `d3e285e3a38ce8ec` | 1553 | recover_candidate |
| `admin_one_click.cmd` | `a1b748b0ddbf862c` | 2449 | recover_candidate |
| `check_svc_admin.py` | `de46cb8c7d67b2d8` | 2045 | recover_candidate |
| `codex_health_check.py` | `e2ff15e20b690a11` | 9400 | recover_candidate |
| `daily_codex_health_check.cmd` | `21b4c9bb5e14875d` | 1905 | recover_candidate |
| `disable_r313_watchdog.cmd` | `b2a88864ae50ae29` | 2926 | recover_candidate |
| `disable_watchdogs_admin.py` | `92f1288535eb95f6` | 2343 | recover_candidate |
| `fix_codex_cli_shim.cmd` | `e9b2f8e015f4b9a0` | 1735 | recover_candidate |
| `full_setup_admin.py` | `57f851f9f8ec1a27` | 2014 | recover_candidate |
| `install_codex_sandbox_service.cmd` | `5c6d1c1e2736349b` | 3154 | recover_candidate |
| `kill_codex_watchdog.py` | `3ca16e8e5d226c33` | 2894 | recover_candidate |
| `query` | `781b776cbdbfbd43` | 7 | recover_candidate |
| `register_sandbox_service.py` | `1629249db9cc22a0` | 4469 | recover_candidate |
| `register_sandbox_service_admin.py` | `24251774b7ad79c9` | 3626 | recover_candidate |
| `run_admin.py` | `20af47ef7daf1d2c` | 2345 | recover_candidate |
| `start_codex_safe.cmd` | `684b61fed137e53b` | 5664 | recover_candidate |
| `stop_codex_watchdog_now.cmd` | `cfb2e9977fa08cee` | 3094 | recover_candidate |
| `sync_codex_hook_hash.py` | `bcd6c1ab37cd13d1` | 6910 | recover_candidate |
| `trigger_admin_one_click.py` | `44f8957fb0849ae4` | 2044 | recover_candidate |
| `uninstall_wetype.cmd` | `a7349fc66ad1c21f` | 2298 | recover_candidate |
| `uninstall_wetype.ps1` | `80fb8fcb2351e470` | 3652 | recover_candidate |
| `vacuum_codex_sqlite.py` | `453cf3e408328596` | 3767 | recover_candidate |
| `wmic_forensics/00_setup_baseline.ps1` | `acc8ead99065a12b` | 3650 | recover_candidate |
| `wmic_forensics/01_PROCESS_BASELINE.csv` | `f1945cd6c19e56b3` | 3 | recover_candidate |
| `wmic_forensics/01_wmic_listener.ps1` | `24e1d0509c57d988` | 3256 | recover_candidate |
| `wmic_forensics/02_static_scan.ps1` | `5730df20e2b59ba4` | 8327 | recover_candidate |
| `wmic_forensics/03_launch_listener.ps1` | `dad41de730a6ec11` | 1369 | recover_candidate |
| `wmic_forensics/04_full_4104.ps1` | `4fa5b0dd6f893d35` | 840 | recover_candidate |
| `wmic_forensics/05_investigate_runner.ps1` | `f3578ade3d1657ab` | 3453 | recover_candidate |
| `wmic_forensics/06_phase2_analysis.ps1` | `aff3ee992d984370` | 6037 | recover_candidate |
| `wmic_forensics/07_pid8480_and_timeline.ps1` | `4da690e7b16e0213` | 4366 | recover_candidate |
| `wmic_forensics/08_full_caller_scan.ps1` | `acee762d57e6dabe` | 5326 | recover_candidate |
| `wmic_forensics/09_targeted_caller_scan.ps1` | `2fe96b96db3899c8` | 2969 | recover_candidate |
| `wmic_forensics/10_final_minimal_scan.ps1` | `18e888b5a8345f57` | 1261 | recover_candidate |
| `wmic_forensics/_listener_runner.ps1` | `e4e8f403ffba0691` | 779 | recover_candidate |
| `wmic_forensics/evidence/02_related_processes.csv` | `18b6499a2b514b3f` | 29186 | recover_candidate |
| `wmic_forensics/evidence/03_audit_policy_proc_creation.txt` | `ef1f6a9904daa5b0` | 1035 | recover_candidate |
| `wmic_forensics/evidence/04_sysmon_check.txt` | `e3b0c44298fc1c14` | 0 | recover_candidate |
| `wmic_forensics/evidence/05_4688_wmic_sample.txt` | `780536e4b3322f06` | 94 | recover_candidate |
| `wmic_forensics/evidence/06_scheduled_tasks_all.csv` | `86d703a189cdb02d` | 30104 | recover_candidate |
| `wmic_forensics/evidence/06b_scheduled_tasks_wmic_suspect.csv` | `cc891e8cec63ae30` | 13865 | recover_candidate |
| `wmic_forensics/evidence/07_services_all.csv` | `8581559110416465` | 37839 | recover_candidate |
| `wmic_forensics/evidence/07b_services_wmic_suspect.csv` | `6f0093de2395dcd2` | 2499 | recover_candidate |
| `wmic_forensics/evidence/08_wmi_eventfilters.csv` | `2f6d127a7b78a76e` | 193 | recover_candidate |
| `wmic_forensics/evidence/08b_wmi_cmdlineconsumers.csv` | `f1945cd6c19e56b3` | 3 | recover_candidate |
| `wmic_forensics/evidence/08c_wmi_scriptconsumers.csv` | `f1945cd6c19e56b3` | 3 | recover_candidate |
| `wmic_forensics/evidence/08d_wmi_bindings.csv` | `979990613f0906ea` | 290 | recover_candidate |
| `wmic_forensics/evidence/09_autoruns_registry.csv` | `12d4ec0ed5fad6e2` | 2461 | recover_candidate |
| `wmic_forensics/evidence/09b_autoruns_wmic_suspect.csv` | `cf19802418d82fc8` | 1116 | recover_candidate |
| `wmic_forensics/evidence/10_ps4104_wmic.csv` | `fb76251e68130ec3` | 9330 | recover_candidate |
| `wmic_forensics/evidence/10b_ps4104_full.csv` | `71a2856834f86c46` | 162724 | recover_candidate |
| `wmic_forensics/evidence/14_wmi_activity_wmic.csv` | `898487237b9dc475` | 10273 | recover_candidate |
| `wmic_forensics/evidence/15_registry_wmic.csv` | `f3b0832ca022b2c0` | 169 | recover_candidate |
| `wmic_forensics/evidence/16_deep_wmic_code_refs.csv` | `e10e99bb14c5b365` | 2841 | recover_candidate |
| `wmic_forensics/evidence/17_ps4103_wmic.csv` | `74c559d2cf0bf0f0` | 3387 | recover_candidate |
| `wmic_forensics/evidence/18_process_snapshot.csv` | `2862a585cc18d794` | 28630 | recover_candidate |
| `wmic_forensics/evidence/24_post_curse_wmic_callers.csv` | `cd802888402acae5` | 2087 | recover_candidate |
| `wmic_forensics/evidence/25_tasks_wmic_arg.csv` | `f1945cd6c19e56b3` | 3 | recover_candidate |
| `wmic_forensics/evidence/26_final_wmic_callers.csv` | `e821258a3d442d95` | 1347 | recover_candidate |

## 8. Hard-constraint compliance

- No git write commands used (only rev-parse, ls-tree, cat-file, log, show, stash show).  
- No worktree files were modified.  
- Only the two report files in D:\AIOS\_agent-hub\v2\reports\channel-audit-20260930\ were written.  
- Secrets / tokens were NOT extracted; only path / hash / size recorded.  
- No processes or services were started/stopped/killed.  
- stash@{0} was NOT modified (no apply/pop/drop/clear).  

---

End of report.