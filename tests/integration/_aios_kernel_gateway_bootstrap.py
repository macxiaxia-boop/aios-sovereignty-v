"""Bootstrap for spawning AIOS kernel gateway subprocess in tests/integration."""
import sys
from pathlib import Path

import uvicorn

# Add src/ to path (bootstrap is at tests/integration/, src is at root/)
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from aios_kernel.gateway.http import create_app  # noqa: E402
from aios_kernel.scheduler import AIOSScheduler, SchedulerConfig  # noqa: E402
from aios_kernel.workers.adapters import register_four_agent_team  # noqa: E402
from aios_kernel.workers.registry import WorkerRegistry  # noqa: E402

reg = WorkerRegistry()
register_four_agent_team(reg)
sched = AIOSScheduler(registry=reg, config=SchedulerConfig(max_concurrent=2))
uvicorn.run(create_app(sched), host="127.0.0.1", port=9001, log_level="warning")
