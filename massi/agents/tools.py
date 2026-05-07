from csv import Sniffer
import logging
import os
import pathlib as pl
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator
import warnings
import itertools as itx

import pandas as pd
import xmlschema as xs

from massi.agents.team._dto import CSVDetails

logger = logging.getLogger(__name__)

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
        ...     list(glob_file_search("**/*.test.txt", tdn))    # doctest: +ELLIPSIS
        [PosixPath('.../simple-test.test.txt')]
    """
    return pl.Path(root).resolve().glob(pattern)


def walk_working_dir_for_files(seed_path: str = ".") -> Iterator[pl.Path]:
    paths = glob_file_search("**/*", seed_path)
    return filter(lambda p: p.is_file(), paths)


def get_file_stats(path: pl.Path) -> tuple[pl.Path, os.stat_result]:
    return (path, path.stat())


def get_raw_file_head(
    path: pl.Path, head_size: int = 10, max_line_length: int | None = None
) -> str:
    with open(path) as fp:
        head_lines = itx.islice(fp, head_size)
        if max_line_length is not None:
            head_lines = [hl[:max_line_length] for hl in head_lines]
        raw_head = "\n".join(head_lines)
    return raw_head


def get_csv_details(csv: pl.Path, separator: str | None = None) -> CSVDetails:
    head_size: int = 5
    raw_head = get_raw_file_head(csv, head_size=head_size)
    df = pd.read_csv(csv, sep=separator, on_bad_lines="warn")
    details: CSVDetails = {
        "delimiter": separator,
        "column_count": df.shape[1],
        "row_count": df.shape[0],
        "head_size": head_size,
        "raw_head": raw_head,
        "dataframe_head": df.head(head_size).to_csv(None, sep=",", index=False),
        "descriptive_stats": df.describe(include="all").to_csv(
            None, sep=",", index=False
        ),
    }
    del df
    return details


def detect_delim(file, num_rows=1):
    sniffer = Sniffer()
    with open(file, "r") as f:
        for _ in range(num_rows):
            line = next(f).strip()
            sniffed = sniffer.sniff(line)

    return sniffed.delimiter


def safe_get_csv_details(csv: pl.Path) -> CSVDetails | None:
    try:
        separator = detect_delim(csv, num_rows=1)
        return get_csv_details(csv, separator)
    except Exception as e:
        logger.error(e)
        logger.warning(e)
        warnings.warn(f"Could not read the CSV: {csv=} -->\n{e=}")
        return None


class AbstractXMLSchema(ABC):
    @abstractmethod
    def validate(self, resource: str) -> tuple[bool, list[Any]]: ...

    @abstractmethod
    def to_string(self) -> str: ...


@dataclass
class MassiXMLSchemaXmlschemalWrapper(AbstractXMLSchema):
    schema: xs.XMLSchema

    def validate(self, resource: str) -> tuple[bool, list[Any]]:
        errors = list(self.schema.iter_errors(xs.XMLResource(resource)))
        return (len(errors) == 0, errors)

    def to_string(self):
        return self.schema.source.tostring(encoding="utf-8")


def get_xmlschema_validator(
    schema_spec: str | xs.XMLResource,
) -> MassiXMLSchemaXmlschemalWrapper:
    """
    Reads and compiles an XSD validator.

    Examples:
        >>> xsd_spec = (
        ...     '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
        ...     '<xs:element name="book">'
        ...     '<xs:complexType>'
        ...     '<xs:sequence>'
        ...     '<xs:element name="title" type="xs:string"/>'
        ...     '<xs:element name="author" type="xs:string"/>'
        ...     '<xs:element name="year" type="xs:int"/>'
        ...     '</xs:sequence>'
        ...     '</xs:complexType>'
        ...     '</xs:element>'
        ...     '</xs:schema>'
        ... )
        >>> data = (
        ...     '<book>'
        ...     '<title>Python Programming</title>'
        ...     '<author>John Doe</author>'
        ...     '<year>2023</year>'
        ...     '</book>'
        ... )
        >>> schema = get_xmlschema_validator(xsd_spec)
        >>> schema.validate(data)
        (True, [])
        >>> schema.validate('<empty/>') # doctest: +ELLIPSIS
        (False, [...'empty'...])
    """
    return MassiXMLSchemaXmlschemalWrapper(
        schema=xs.XMLSchema(schema_spec, validation="lax")
    )
