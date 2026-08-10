# TASK-028 Verification

Local structural verification covers compilation, schema equality and resolver behavior. Native Windows release gate:

```powershell
python -m pip install -e ".[dev]"
python -c "import ai_video_production; print(ai_video_production.__version__)"
python -m pytest -q
python -m compileall -q src tests
```

Expected package version: `0.6.2`. Expected current suite: `293 passed`.

Owner verification for package 0.6.0: `273 passed in 29.91s` and compileall PASS. The routing-core Windows Gate is accepted.

This is a repository regression test and does not create a behavior Evidence directory.
