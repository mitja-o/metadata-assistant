from lxml import etree
from abc import ABC, abstractmethod

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


class XMLMasker(MetadataMasker):
    def invoke(self, metadata: str) -> MetadataBlueprint:
        """Mask all attributes and values of the XML.

        Args:
            xml_string (str): original XML

        Returns:
            str: string representation of the masked XML

        Examples:
            >>> masker = XMLMasker()
            >>> dwc_xml = __EXAMPLE_XML__.get("dwc_text")
            >>> print(masker.invoke(dwc_xml))
            <archive xmlns="http://rs.tdwg.org/dwc/text/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema" xsi:schemaLocation="{{GAP_001:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}ARCHIVE-{HTTP://WWW.W3.ORG/2001/XMLSCHEMA-INSTANCE}SCHEMALOCATION}}">
                <core rowType="{{GAP_002:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}CORE-ROWTYPE}}" ignoreHeaderLines="{{GAP_003:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}CORE-IGNOREHEADERLINES}}">
                    <files>
                        <location>{{GAP_004:TEXT:{HTTP://RS.TDWG.ORG/DWC/TEXT/}LOCATION}}</location>
                    </files>
                    <field index="{{GAP_005:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-INDEX}}" term="{{GAP_006:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-TERM}}"/>
                    <field index="{{GAP_007:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-INDEX}}" term="{{GAP_008:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-TERM}}"/>
                    <field index="{{GAP_009:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-INDEX}}" term="{{GAP_010:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-TERM}}"/>
                    <!--{{GAP_011:TEXT:COMMENT}}-->
                    <field term="{{GAP_012:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-TERM}}" default="{{GAP_013:ATTRIBUTE:{HTTP://RS.TDWG.ORG/DWC/TEXT/}FIELD-DEFAULT}}"/>
                </core>
            </archive>
            >>> eml_xml =  __EXAMPLE_XML__.get("eml")
            >>> print(masker.invoke(eml_xml))
            <eml:eml xmlns:eml="https://eml.ecoinformatics.org/eml-2.2.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:stmml="http://www.xml-cml.org/schema/stmml-1.1" packageId="{{GAP_001:ATTRIBUTE:{HTTPS://EML.ECOINFORMATICS.ORG/EML-2.2.0}EML-PACKAGEID}}" system="{{GAP_002:ATTRIBUTE:{HTTPS://EML.ECOINFORMATICS.ORG/EML-2.2.0}EML-SYSTEM}}" xsi:schemaLocation="{{GAP_003:ATTRIBUTE:{HTTPS://EML.ECOINFORMATICS.ORG/EML-2.2.0}EML-{HTTP://WWW.W3.ORG/2001/XMLSCHEMA-INSTANCE}SCHEMALOCATION}}">
                <dataset>
                    <title>{{GAP_004:TEXT:TITLE}}</title>
                    <creator id="{{GAP_005:ATTRIBUTE:CREATOR-ID}}">
                        <individualName>
                            <givenName>{{GAP_006:TEXT:GIVENNAME}}</givenName>
                            <givenName>{{GAP_007:TEXT:GIVENNAME}}</givenName>
                            <surName>{{GAP_008:TEXT:SURNAME}}</surName>
                        </individualName>
                        <electronicMailAddress>{{GAP_009:TEXT:ELECTRONICMAILADDRESS}}</electronicMailAddress>
                        <userId directory="{{GAP_011:ATTRIBUTE:USERID-DIRECTORY}}">{{GAP_010:TEXT:USERID}}</userId>
                    </creator>
                    <keywordSet>
                        <keyword>{{GAP_012:TEXT:KEYWORD}}</keyword>
                        <keyword>{{GAP_013:TEXT:KEYWORD}}</keyword>
                    </keywordSet>
                    <contact>
                        <references>{{GAP_014:TEXT:REFERENCES}}</references>
                    </contact>
                </dataset>
            </eml:eml>
        """
        parser = etree.XMLParser(remove_blank_text=False)
        root = etree.fromstring(metadata.encode("utf-8"), parser=parser)

        running_idx = 1
        for _, elem in enumerate(root.iter()):
            tag = str(elem.tag.__name__) if callable(elem.tag) else str(elem.tag)

            # Mask Element Text
            if elem.text and elem.text.strip():
                elem.text = XMLBlueprintGapPattern.get_gap_pattern(
                    f"GAP_{running_idx:03d}", "TEXT", str(tag).upper()
                )
                running_idx += 1

            # Mask Element Tail (text following the tag)
            if elem.tail and elem.tail.strip():
                elem.tail = XMLBlueprintGapPattern.get_gap_pattern(
                    f"GAP_{running_idx:03d}", "TAIL", str(tag).upper()
                )
                running_idx += 1

            # Mask Attributes
            if elem.attrib:
                for attr in elem.attrib:
                    elem.attrib[attr] = XMLBlueprintGapPattern.get_gap_pattern(
                        f"GAP_{running_idx:03d}",
                        "ATTRIBUTE",
                        f"{tag}-{attr}".upper(),
                    )
                    running_idx += 1

        return etree.tostring(
            root,
            encoding="unicode",
            method="xml",
        )
