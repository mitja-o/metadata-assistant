# FIXME(reuse): don't reinvent the wheel!

import pathlib as pl
from typing import Iterator

# file system
# -----------


def glob_file_search(pattern: str, root: str = "./") -> Iterator[pl.Path]:
    """
    Return all files matching pattern under root directory

    :param pattern: file path pattern with wildcards (e.g., *.py). No tilde expansion is done, but *, ?, and character ranges expressed with [] will be correctly matched.
    :param root: starting point for search in cwd by default
    :return: iterator of matched paths

    Examples:
        >>> import tempfile as tf
        >>> from pathlib import Path
        >>> with tf.TemporaryDirectory() as tdn:
        ...     tdp = Path(tdn)
        ...     test_file = tdp / "simple-test.test.txt"
        ...     _ = test_file.write_text("test content")
        ...
        ...     list(glob_file_search("**/*.test.txt", tdn))  # doctest: +ELLIPSIS
        [PosixPath('.../simple-test.test.txt')]
    """
    return pl.Path(root).resolve().glob(pattern)


def walk_working_dir_for_files(seed_path: str = ".") -> Iterator[pl.Path]:
    paths = glob_file_search("**/*", seed_path)
    return filter(lambda p: p.is_file(), paths)
