from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
import pathlib as pl
from typing import Any, Iterator, TypedDict

import pandas as pd
import urllib.request as ur


# opener = ur.build_opener()
# opener.addheaders = [
#     ("User-Agent", "Mozilla/5.0"),
# ]
# ur.install_opener(opener)


import xmlschema as xs
from lxml import etree

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


class CSVDetails(TypedDict):
    overview: str
    column_count: int
    row_count: int


def get_csv_details(csv: pl.Path) -> CSVDetails:
    df = pd.read_csv(csv)
    details: CSVDetails = {
        "column_count": df.shape[1],
        "row_count": df.shape[0],
        "head": df.head(3).to_csv(None, sep=","),
        "descriptive_stats": df.describe(include="all").to_csv(None, sep=","),
    }
    del df
    return details


class AbstractXMLSchema(ABC):
    @abstractmethod
    def validate(self, resource: str) -> tuple[bool, list[Any]]: ...


@dataclass
class MassiXMLSchemaXmlschemalWrapper(AbstractXMLSchema):
    schema: xs.XMLSchema

    def validate(self, resource: str) -> tuple[bool, list[Any]]:
        errors = list(self.schema.iter_errors(xs.XMLResource(resource)))
        return (len(errors) == 0, errors)


class MassiXmlSchemaLoader(xs.SchemaLoader):
    opener: ur.OpenerDirector

    def load_schema(
        self, source, namespace=None, base_url=None, build=False, partial=False
    ):
        print(self.opener)
        return super().load_schema(
            xs.XMLResource(source, opener=self.opener),
            namespace,
            base_url,
            build,
            partial,
        )


class MassiXmlSchemaLoaderFactory:
    @staticmethod
    def create_loader_class(opener: ur.OpenerDirector) -> type[MassiXmlSchemaLoader]:
        MassiXmlSchemaLoader.opener = opener
        return MassiXmlSchemaLoader


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
    opener = ur.build_opener()
    opener.addheaders = [
        ("User-Agent", "bot"),
    ]
    return MassiXMLSchemaXmlschemalWrapper(
        schema=xs.XMLSchema(
            xs.XMLResource(schema_spec, opener=opener),
            validation="lax",
            loader_class=MassiXmlSchemaLoaderFactory.create_loader_class(opener),
        )
    )


@dataclass
class MassiXMLSchemaLxmlWrapper(AbstractXMLSchema):
    schema: etree.XMLSchema

    def validate(self, resource: str) -> tuple[bool, list[Any]]:
        is_valid = self.schema.validate(etree.XML(resource))
        errors = [e for e in self.schema.error_log]
        return (is_valid, errors)


def get_lxml_validator(schema_spec: str) -> MassiXMLSchemaLxmlWrapper:
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
        >>> schema = get_lxml_validator(xsd_spec)
        >>> schema.validate(data)
        (True, [])
        >>> schema.validate('<empty/>') # doctest: +ELLIPSIS
        (False, [...'empty'...])
    """
    return MassiXMLSchemaLxmlWrapper(schema=etree.XMLSchema(etree.XML(schema_spec)))
