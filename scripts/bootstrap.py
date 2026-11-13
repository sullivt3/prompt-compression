"""Prepare public tokenizer data and migrate the configured database; no inference."""

import subprocess

import tiktoken

if __name__ == "__main__":
    for name in ["o200k_base", "cl100k_base"]:
        tiktoken.get_encoding(name)
    subprocess.run(["alembic", "upgrade", "head"], check=True)
