# Smoke Task P0-001 (2026-10-08)

你是 Codex 监督下的 Claude Code 施工子。

请执行：
1. 读取本文件证明你能读 (echo 'READ OK')
2. 写入一行到 evidence.txt： 'SMOKE_P0_001_OK <你的进程PID> <UTC ISO8601 时间>'
3. 返回一个 1-2 行的最终报告，注明 PID、退出码、耗时

禁止：调用 MCP / 启动子进程 / 修改本文件以外的任何文件。
