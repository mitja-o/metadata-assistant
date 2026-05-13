from abc import ABC, abstractmethod
import random

from lxml import etree

from massi.agents.team._dto import MetadataBlueprint, XMLBlueprintGapPattern

# Agent inteface
# --------------


class MetadataMasker(ABC):
    @abstractmethod
    def invoke(self, metadata: str) -> MetadataBlueprint: ...


# Agent instances
# ---------------

__EXAMPLE_XML__ = dict(
    dwc_text="""
<?xml version="1.0" encoding="UTF-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xsi:schemaLocation="http://rs.tdwg.org/dwc/text/ http://rs.tdwg.org/dwc/text/tdwg_dwc_text.xsd">
    <core rowType="http://rs.tdwg.org/dwc/xsd/simpledarwincore/SimpleDarwinRecord" ignoreHeaderLines="1">
        <files>
            <location>http://data.gbif.org/download/specimens.csv</location>
        </files>
        <field index="0" term="http://rs.tdwg.org/dwc/terms/occurrenceID" />
        <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName" />
        <field index="2" term="http://rs.tdwg.org/dwc/terms/individualCount" />
        <!-- A constant value has no index, but applies to all rows -->
        <field term="http://rs.tdwg.org/dwc/terms/datasetID" default="urn:lsid:tim.lsid.tdwg.org:collections:1"/>
    </core>
</archive>
""".strip(),
    eml="""
<?xml version="1.0"?>
<eml:eml
    packageId="doi:10.xxxx/eml.1.1" system="https://doi.org"
    xmlns:eml="https://eml.ecoinformatics.org/eml-2.2.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:stmml="http://www.xml-cml.org/schema/stmml-1.1"
    xsi:schemaLocation="https://eml.ecoinformatics.org/eml-2.2.0 xsd/eml.xsd">
    <dataset>
        <title>Primary production of algal species from Southeast Alaska, 1990-2002</title>
        <creator id="https://orcid.org/0000-0003-0077-4738">
            <individualName>
                <givenName>Matthew</givenName>
                <givenName>B.</givenName>
                <surName>Jones</surName>
            </individualName>
            <electronicMailAddress>jones@nceas.ucsb.edu</electronicMailAddress>
            <userId directory="https://orcid.org">https://orcid.org/0000-0003-0077-4738</userId>
        </creator>
        <keywordSet>
            <keyword>biomass</keyword>
            <keyword>productivity</keyword>
        </keywordSet>
        <contact>
            <references>https://orcid.org/0000-0003-0077-4738</references>
        </contact>
    </dataset>
</eml:eml>
""".strip(),
)


class ProbabilityValueXMLMasker(MetadataMasker):
    def __init__(self, probability: float = 1.0):
        self._probability = probability

    def invoke(self, metadata: str) -> MetadataBlueprint:
        """Masks all attributes and values of the XML.
        Preserves the comments and the XML configuration attributes.

        Args:
            xml_string (str): original XML

        Returns:
            str: string representation of the masked XML

        Examples:
            >>> masker = ProbabilityValueXMLMasker(1.0)
            >>> dwc_xml = __EXAMPLE_XML__.get("dwc_text")
            >>> print(masker.invoke(dwc_xml)["content"])
            <archive xmlns="http://rs.tdwg.org/dwc/text/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:schemaLocation="http://rs.tdwg.org/dwc/text/ http://rs.tdwg.org/dwc/text/tdwg_dwc_text.xsd">
                <core rowType="{{GAP_000001:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}CORE-ROWTYPE}}" ignoreHeaderLines="{{GAP_000002:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}CORE-IGNOREHEADERLINES}}">
                    <files>
                        <location>{{GAP_000003:TEXT:{HTTP://RS.TDWG.ORG/DWC/TEXT/}LOCATION}}</location>
                    </files>
                    <field index="{{GAP_000004:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-INDEX}}" term="{{GAP_000005:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-TERM}}"/>
                    <field index="{{GAP_000006:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-INDEX}}" term="{{GAP_000007:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-TERM}}"/>
                    <field index="{{GAP_000008:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-INDEX}}" term="{{GAP_000009:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-TERM}}"/>
                    <!-- A constant value has no index, but applies to all rows -->
                    <field term="{{GAP_000010:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-TERM}}" default="{{GAP_000011:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-DEFAULT}}"/>
                </core>
            </archive>
            >>> eml_xml =  __EXAMPLE_XML__.get("eml")
            >>> print(masker.invoke(eml_xml)["content"])
            <eml:eml xmlns:eml="https://eml.ecoinformatics.org/eml-2.2.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:stmml="http://www.xml-cml.org/schema/stmml-1.1" packageId="{{GAP_000001:ATTRIBUTE:{HTTPS://EML.ECOINFORMATICS.ORG/EML-2.2.0}EML-PACKAGEID}}" system="{{GAP_000002:ATTRIBUTE:{HTTPS://EML.ECOINFORMATICS.ORG/EML-2.2.0}EML-SYSTEM}}" xsi:schemaLocation="https://eml.ecoinformatics.org/eml-2.2.0 xsd/eml.xsd">
                <dataset>
                    <title>{{GAP_000003:TEXT:TITLE}}</title>
                    <creator id="{{GAP_000004:ATTRIBUTE:CREATOR-ID}}">
                        <individualName>
                            <givenName>{{GAP_000005:TEXT:GIVENNAME}}</givenName>
                            <givenName>{{GAP_000006:TEXT:GIVENNAME}}</givenName>
                            <surName>{{GAP_000007:TEXT:SURNAME}}</surName>
                        </individualName>
                        <electronicMailAddress>{{GAP_000008:TEXT:ELECTRONICMAILADDRESS}}</electronicMailAddress>
                        <userId directory="{{GAP_000010:ATTRIBUTE:USERID-DIRECTORY}}">{{GAP_000009:TEXT:USERID}}</userId>
                    </creator>
                    <keywordSet>
                        <keyword>{{GAP_000011:TEXT:KEYWORD}}</keyword>
                        <keyword>{{GAP_000012:TEXT:KEYWORD}}</keyword>
                    </keywordSet>
                    <contact>
                        <references>{{GAP_000013:TEXT:REFERENCES}}</references>
                    </contact>
                </dataset>
            </eml:eml>
        """
        config_namespaces = {
            "http://www.w3.org/2000/xmlns/",
            "http://www.w3.org/2001/XMLSchema-instance",
        }
        parser = etree.XMLParser(remove_blank_text=False)
        root = etree.fromstring(metadata.encode("utf-8"), parser=parser)

        running_idx = 1
        for elem in root.iter():
            if isinstance(elem, etree._Comment):
                continue

            tag = str(elem.tag.__name__) if callable(elem.tag) else str(elem.tag)

            # Mask Element Text
            if elem.text and elem.text.strip() and random.random() < self._probability:
                elem.text = XMLBlueprintGapPattern.get_gap_pattern(
                    f"GAP_{running_idx:06d}", "TEXT", str(tag).upper()
                )
                running_idx += 1

            # Mask Element Tail (text following the tag)
            if elem.tail and elem.tail.strip() and random.random() < self._probability:
                elem.tail = XMLBlueprintGapPattern.get_gap_pattern(
                    f"GAP_{running_idx:06d}", "TAIL", str(tag).upper()
                )
                running_idx += 1

            # Mask Attributes
            for attr_name, _ in elem.attrib.items():
                is_config = any(ns in attr_name for ns in config_namespaces)
                if not is_config and random.random() < self._probability:
                    elem.attrib[attr_name] = XMLBlueprintGapPattern.get_gap_pattern(
                        f"GAP_{running_idx:06d}",
                        "ATTRIBUTE",
                        f"{tag}-{attr_name}".upper(),
                    )
                    running_idx += 1

        return {
            "content": etree.tostring(
                root,
                encoding="unicode",
                method="xml",
            )
        }
