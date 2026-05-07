import os
import time
from typing import Callable, Optional


class BitstreamError(Exception):
    pass


class BitstreamProgrammer:
    _MIN_VALID_SIZE = 4

    def program(self, filepath: str, progress_callback: Optional[Callable[[int], None]] = None) -> None:
        if not os.path.isfile(filepath):
            raise BitstreamError(f"Bitstream file not found: {filepath!r}")
        file_size = os.path.getsize(filepath)
        if file_size < self._MIN_VALID_SIZE:
            raise BitstreamError(
                f"File {filepath!r} is too small ({file_size} bytes) to be a valid bitstream."
            )
        # Simulated programming — replace with real tool invocation e.g.:
        #   subprocess.run(["openFPGALoader", "-b", "arty", filepath], check=True)
        steps = 20
        for step in range(steps + 1):
            time.sleep(0.05)
            if progress_callback:
                progress_callback(int(step / steps * 100))
