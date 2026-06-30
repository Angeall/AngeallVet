"""CLI entry point so `python -m app.licensing ...` works.

The implementation lives in :mod:`app.core.licensing`; this thin shim just
exposes its command-line interface (keygen / sign / inspect).
"""
from app.core.licensing import _main

if __name__ == "__main__":  # pragma: no cover
    _main()
