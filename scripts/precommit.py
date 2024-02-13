import contextlib
import json
import pathlib
import subprocess
import sys


def main():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],  # noqa: S603, S607
        stdout=subprocess.PIPE,
        check=True,
    )
    files = result.stdout.decode("utf-8").splitlines()
    error_files = []
    for file in [f for f in files if pathlib.Path(f).suffix == ".ipynb"]:
        with pathlib.Path.open(file, encoding="UTF-8") as json_file, contextlib.suppress(json.JSONDecodeError, KeyError):
            json_contents = json.load(json_file)
            cells = json_contents["cells"]
            for cell in cells:
                output = cell.get("outputs", None)
                metadata = cell.get("metadata", {})
                if output or metadata.keys():
                    error_files.append(file)
    if error_files:
        print("Notebook file(s) contain outputs or metadata:", *error_files, sep=" ")  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    main()
