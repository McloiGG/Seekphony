# Repository Instructions

This is the fresh Seekphony repository. Do not reuse assumptions, file paths, or
architecture decisions from older similar projects unless the user explicitly
asks for them.

For development prompts that change code, configuration, workflows, or scripts:

- Run `python scripts/check_all.py` before the final response.
- If the local machine cannot run the full required toolchain, run the largest
  available subset and clearly report which checks were skipped.
- Add future automated checks as zero-argument `scripts/check_*.py` or
  `scripts/scan_*.py` scripts so `scripts/check_all.py`, GitHub Actions, and
  local hooks pick them up automatically.
- Keep dependencies exact-pinned in `pyproject.toml`, and remove unused runtime
  packages unless they are OS-specific.
- Never commit API keys, tokens, private keys, passwords, or other secrets.

For documentation-pass prompts:

- Review the full codebase before editing documentation.
- Make README, QA docs, agent instructions, and development docs reflect the
  current implementation.
- Follow `docs/development/documentation_pass.md`.
- Verify the changes, then open a pull request.
