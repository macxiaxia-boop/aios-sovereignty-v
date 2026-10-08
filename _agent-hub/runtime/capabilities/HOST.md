# 宿主能力清单 · <host_id>

- host_id
- os
- user
- cwd
- available_tools: [git, powershell, node, python, docker, ...]
- credential_refs: [~/.workbuddy/secrets/github-token, ...]
- egress_allowlist: [MiniMax 官方域名, ...]
- sandbox_boundary: <描述>
- known_unavailable: [list of things that don't work here]

# 评审准则
- 不假设所有 host 权限相同
- 缺关键工具/凭据 → SOP 不能在该 host 注册为 auto
