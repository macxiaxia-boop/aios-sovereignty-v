@echo off
rem run_all_tests.cmd - run v2 test suite via pytest.
setlocal
set PYTHONPATH=%~dp0..
python -m pytest %~dp0 -v --tb=short 2>&1
endlocal