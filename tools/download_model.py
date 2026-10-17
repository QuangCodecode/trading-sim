"""Download the Laya English checkpoint (~808 MB) into models/laya. Run once: python3 tools/download_model.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # let `tradesim` import from tools/

from huggingface_hub import snapshot_download

from tradesim import config

REPO_ID = "convaiinnovations/laya"
# Only the English checkpoint; the repo also holds other variants we don't need.
FILES = ["rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*"]


def main() -> None:
    """Fetch the weights unless they are already there."""
    if (config.MODEL_DIR / "model.safetensors").exists():
        print(f"Laya is already in {config.MODEL_DIR}")
        return
    print(f"Downloading {REPO_ID} (~808 MB) into {config.MODEL_DIR} …")
    snapshot_download(REPO_ID, local_dir=config.MODEL_DIR, allow_patterns=FILES)
    print("Done. The Headline Lab (hl) can now ask Laya.")


if __name__ == "__main__":
    main()
