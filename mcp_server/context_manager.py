from contextlib import contextmanager
from pathlib import Path
from .config import settings


@contextmanager
def working_dir(path: str | None = None):
    target = Path(path or settings.dspy_root).resolve()
    original = Path.cwd()
    try:
        target.mkdir(parents=True, exist_ok=True)
        import os
        os.chdir(target)
        yield target
    finally:
        import os
        os.chdir(original)
