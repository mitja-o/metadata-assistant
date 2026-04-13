<!-- markdownlint-disable MD036 -->

# Prompt collection

---

<!-- This context should be added to the messages below -->

CONTEXT:

--- BEGIN: XSD metadata schema ---
<xs:schema xmlns:xs="<http://www.w3.org/2001/XMLSchema>" xmlns:arch="<http://rs.tdwg.org/dwc/text/>"
    xmlns:dwc="<http://rs.tdwg.org/dwc/terms/>" version="0.1" targetNamespace="<http://rs.tdwg.org/dwc/text/>"
    attributeFormDefault="unqualified" elementFormDefault="qualified">
    <xs:import namespace="<http://rs.tdwg.org/dwc/terms/>"
        schemaLocation="<https://raw.githubusercontent.com/tdwg/dwc/master/docs/xml/tdwg_dwcterms.xsd>" />
    <xs:import namespace="<http://www.w3.org/XML/1998/namespace>" schemaLocation="<http://rs.gbif.org/schema/xml.xsd">>
        <xs:annotation>
            <xs:documentation> Get access to the xml: attribute groups for xml:lang </xs:documentation>
        </xs:annotation>
    </xs:import>
    <!--  The root element of the document is an archive  -->
    <xs:element name="archive">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="core" type="arch:coreFileType" maxOccurs="1" minOccurs="1" />
                <xs:element name="extension" type="arch:extensionFileType" maxOccurs="unbounded" minOccurs="0" />
            </xs:sequence>
            <xs:attribute name="metadata" type="xs:anyURI" use="optional" />
        </xs:complexType>
    </xs:element>
    <!--  attributes shared across all file types, core or extensions  -->
    <xs:attributeGroup name="fileAttributes">
        <xs:attribute name="linesTerminatedBy" type="xs:string" use="optional" default="\n" />
        <xs:attribute name="fieldsTerminatedBy" type="xs:string" use="optional" default="," />
        <xs:attribute name="fieldsEnclosedBy" type="xs:string" use="optional" default="""/>
<xs:attribute name=" ignoreHeaderLines" type="xs:integer" use="optional" default="0" />
        <xs:attribute name="rowType" type="xs:string" use="required" />
        <xs:attribute name="encoding" type="xs:string" use="optional" default="UTF-8" />
        <xs:attribute name="dateFormat" type="xs:string" use="optional" default="YYYY-MM-DD" />
    </xs:attributeGroup>
    <!--  The file within an archive defines the description and it's fields  -->
    <xs:complexType name="fileType">
        <xs:sequence>
            <xs:element name="files" minOccurs="1" maxOccurs="1">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="location" type="xs:string" minOccurs="1" maxOccurs="unbounded" />
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
        </xs:sequence>
        <xs:attributeGroup ref="arch:fileAttributes" />
    </xs:complexType>
    <!--  a file representing the core file in a star schema  -->
    <xs:complexType name="coreFileType">
        <xs:complexContent>
            <xs:extension base="arch:fileType">
                <xs:sequence>
                    <xs:element name="id" type="arch:idFieldType" minOccurs="0" maxOccurs="1" />
                    <xs:element name="field" type="arch:fieldType" minOccurs="1" maxOccurs="unbounded" />
                </xs:sequence>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>
    <!--  a file representing an extension file in a star schema  -->
    <xs:complexType name="extensionFileType">
        <xs:complexContent>
            <xs:extension base="arch:fileType">
                <xs:sequence>
                    <xs:element name="coreid" type="arch:idFieldType" minOccurs="1" maxOccurs="1" />
                    <xs:element name="field" type="arch:fieldType" minOccurs="1" maxOccurs="unbounded" />
                </xs:sequence>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>
    <!--  A field represents a column within the file  -->
    <xs:complexType name="idFieldType">
        <xs:attribute name="index" type="xs:integer" use="optional" />
    </xs:complexType>
    <!--  A field represents a column within the file  -->
    <xs:complexType name="fieldType">
        <xs:attribute name="index" type="xs:integer" use="optional">
            <xs:annotation>
                <xs:documentation>The index number of the column this field is represented in the source file(s).
                    Indices start with 0.</xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="term" type="xs:anyURI" use="required">
            <xs:annotation>
                <xs:documentation>The unique, qualified identifier for the term, usually a URI. E.g.
                    <http://rs.tdwg.org/dwc/terms/scientificName></xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="default" type="xs:string" use="optional">
            <xs:annotation>
                <xs:documentation>A global default value that should be used in case the field doesnt have a column
                    index or the actual value for the source record is NULL.</xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="vocabulary" type="xs:anyURI" use="optional">
            <xs:annotation>
                <xs:documentation>A URI that identifies a vocabulary used for the values found for the field in the
                    source files. The URI ideally should resolve to some machine readable definition like SKOS, RDF, the
                    GBIF vocabulary schema or a simple text file as often found for ISO or RFC standards. E.g.
                    <http://rs.gbif.org/vocabulary/gbif/nomenclatural_code.xml>; <http://www.ietf.org/rfc/rfc3066.txt>;
                    <http://www.iso.org/iso/list-en1-semic-3.txt></xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="delimitedBy" type="xs:string" use="optional">
            <xs:annotation>
                <xs:documentation>Indicates an optional delimiter used for concatenating multiple values in a list.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
</xs:schema>
--- END: XSD metadata schema ---

--- BEGIN: CSV File overview ---

==> budburst_event.csv <==

"eventID","parentEventID","samplingProtocol","sampleSizeValue","sampleSizeUnit","eventDate","year","month","day","country","countryCode","verbatimLocality","minimumElevationInMeters","maximumElevationInMeters","decimalLatitude","decimalLongitude","geodeticDatum","type","language","institutionID","institutionCode"

"HV1988",NA,NA,NA,NA,"1988",1988,NA,NA,"Netherlands","NL","Hoge Veluwe",NA,NA,NA,NA,NA,"Event","en","<https://ror.org/01g25jp36","NIOO>"

"HV1988_119","HV1988",NA,NA,NA,"1988-04-28",1988,4,28,"Netherlands","NL","Hoge Veluwe",NA,NA,NA,NA,NA,"Event","en","<https://ror.org/01g25jp36","NIOO>"

==> budburst_extendedmeasurementorfact.csv <==

"measurementID","eventID","measurementType","measurementValue","measurementUnit","measurementMethod","measurementRemarks"

"DO1997_93_1_1_m1","DO1997_93_1","bud burst stage (PO:0025532) of the tree crown",1.5,NA,"<https://doi.org/10.1098/rspb.2000.1363",NA>

"DO1997_93_1_1_m2","DO1997_93_1","bud burst stage (PO:0025532) of the whole tree",1,NA,"<https://doi.org/10.1098/rspb.2000.1363",NA>

==> budburst_occurrence.csv <==

"eventID","occurrenceID","recordedByID","individualCount","basisOfRecord","occurrenceStatus","occurrenceRemarks","organismID","scientificName","kingdom","phylum","class","order","family","genus","specificEpithet"

"DO1997_93_1","DO1997_93_1_o1",NA,1,"HumanObservation","present",NA,1,"Quercus robur L.","Plantae","Tracheophyta","Magnoliopsida","Fagales","Fagaceae","Quercus","robur"

"DO1997_100_1","DO1997_100_1_o1",NA,1,"HumanObservation","present",NA,1,"Quercus robur L.","Plantae","Tracheophyta","Magnoliopsida","Fagales","Fagaceae","Quercus","robur"

--- END: CSV File overview ----

---

<!-- This prompt should be given to the first-order planner -->

This is the refined, high-level prompt for the **Template Builder Sub-Agent**. It shifts the "intelligence" of schema architectural design to the Metadata Assistant while providing a clear, abstract framework for the sub-agent to execute the XML generation.

***

## **PROMPT FOR SUB-AGENT: DwC-A XML ARCHITECT**

### **Role**

You are a precision XML Developer specializing in Darwin Core Archive (DwC-A) structures. Your task is to generate a `meta.xml` file that accurately reflects a **Star Schema** organization derived from a set of provided CSV files and an XSD metadata schema.

### **Contextual Building Blocks**

* **XSD Schema:** [Insert XSD metadata schema here]
* **CSV Overview:** [Insert CSV File overview here]

### **Task: Star Schema Identification**

Before generating the XML, you must analyze the relationship between the provided CSV files to establish the Star Schema:

* **Identify the Core:** Locate the primary entity file (the "Core") which contains the base records (e.g., Events or Taxa) that other files reference.
* **Identify Extensions:** Locate subordinate files (the "Extensions") that provide many-to-one supplemental data to the Core records.
* **Identify the Linkage:** Determine the specific column (the foreign key) used to join Extension records back to the Core's unique identifier.

### **Technical Logic & Mapping Rules**

Generate the XML following the `<archive>` structure. Where metadata is missing or ambiguous, you must insert placeholders using the syntax: `{{GAP_XXX:TYPE:DESCRIPTION}}`.

**1. Disambiguation of Gap TYPEs:**

* **INDEX:** Use for `0-based` column positions.
* **URI:** Use for the `rowType` or `term` attributes.
* **STRING:** Use for general file attributes (e.g., `encoding`, `fieldsTerminatedBy`).

**2. Strict Mapping Rules:**

* **Term Mapping:** If a CSV header name matches a known Darwin Core term, use that URI for the `term` attribute; **otherwise**, generate a `{{GAP_XXX:URI:HEADER_NAME}}` placeholder.
* **Index Mapping:** If the column index can be provided with absolute certainty from the CSV header order, specify it directly (e.g., `index="0"`); **otherwise**, generate a `{{GAP_XXX:INDEX:COLUMN_NAME}}` placeholder.

### **Mapping Instructions**

1. **Archive Attributes:** Set the `metadata` attribute to a `URI` gap.
2. **Core Component:** * Identify the appropriate `rowType` URI.
    * Map the primary key to the `<id>` element.
    * Map all remaining columns to `<field>` elements using the Mapping Rules above.
3. **Extension Components:**
    * For each extension, map the foreign key to the `<coreid>` element.
    * Map extension columns to `<field>` elements using the Mapping Rules above.

### **Expected Output Format**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="{{GAP_001:URI:METADATA_LOCATION}}">
  <core rowType="[CORE_URI]" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" ignoreHeaderLines="1">
    <files>
      <location>[CORE_FILENAME]</location>
    </files>
    <id index="[PRIMARY_KEY_INDEX]" />
    <field index="1" term="http://rs.tdwg.org/dwc/terms/exampleTerm"/>
    <field index="{{GAP_002:INDEX:UNCERTAIN_COL}}" term="{{GAP_003:URI:UNMAPPED_HEADER}}"/>
  </core>
  <extension rowType="[EXTENSION_URI]">
    <files>
      <location>[EXTENSION_FILENAME]</location>
    </files>
    <coreid index="[FOREIGN_KEY_INDEX]" />
    </extension>
</archive>
```

---

<!-- 
  The prompt above should generate something like the following prompt.
  It should be enriched with the context and passed to the second-order planner (template builder).
-->

### **Updated Sub-Agent Prompt: Darwin Core Archive XML Generator**

**Role**
You are a precision XML developer specializing in Biodiversity Data Standards (Darwin Core). Your task is to generate a `meta.xml` file that describes a Darwin Core Archive (DwC-A) based on a provided Star Schema.

**Contextual Data**
You must map the following CSV files to the provided XSD structure:

1. **Core File:** `budburst_event.csv` (RowType: `http://rs.tdwg.org/dwc/terms/Event`)
2. **Extension 1:** `budburst_occurrence.csv` (RowType: `http://rs.tdwg.org/dwc/terms/Occurrence`)
3. **Extension 2:** `budburst_extendedmeasurementorfact.csv` (RowType: `http://rs.gbif.org/terms/1.0/ExtendedMeasurementOrFact`)

**Technical Logic & Gap Handling**
You must generate a valid XML document following the `<archive>` schema. Where metadata is not explicitly provided in the source context, you must insert placeholders using the syntax: `{{GAP_XXX:TYPE:DESCRIPTION}}`.

**Disambiguation of Gap TYPEs:**

* **INDEX:** Use for `0-based` column positions.
* **URI:** Use for the `rowType` or `term` attributes.
* **STRING:** Use for general attributes (e.g., `encoding`, `fieldsTerminatedBy`).

**Strict Mapping Rules:**

* **Term Mapping:** If a CSV header name matches a known Darwin Core term, use that URI for the `term` attribute; **otherwise**, generate a `{{GAP_XXX:URI:TERM_NAME}}` placeholder.
* **Index Mapping:** If the column index can be determined with absolute certainty from the provided CSV overview, specify it directly (e.g., `index="0"`); **otherwise**, generate a `{{GAP_XXX:INDEX:COLUMN_NAME}}` placeholder.

**Mapping Instructions**

1. **Archive Attributes:** Set `metadata` to a GAP placeholder.
2. **Core (`budburst_event.csv`):**
    * Map `eventID` to the `<id>` element.
    * Map all other headers to `<field>` elements following the Term/Index mapping rules above.
3. **Extensions:**
    * Link both extensions to the core using `eventID` in the `<coreid>` element.
    * Map headers to `<field>` elements following the Term/Index mapping rules above.

**Expected Output Format**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="{{GAP_001:URI:METADATA_LOCATION}}">
  <core rowType="http://rs.tdwg.org/dwc/terms/Event" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" ignoreHeaderLines="1">
    <files>
      <location>budburst_event.csv</location>
    </files>
    <id index="0" />
    <field index="1" term="http://rs.tdwg.org/dwc/terms/parentEventID"/>
    <field index="{{GAP_002:INDEX:SAMPLING_PROTOCOL}}" term="http://rs.tdwg.org/dwc/terms/samplingProtocol"/>
    <field index="{{GAP_003:INDEX:UNKNOWN_COL}}" term="{{GAP_004:URI:UNKNOWN_TERM}}"/>
  </core>
  </archive>
```

---

Examples:

> -- BEGIN: Prompt

## **PROMPT FOR SUB-AGENT: DwC-A XML ARCHITECT**

### **Role**

You are a precision XML Developer specializing in Darwin Core Archive (DwC-A) structures. Your task is to generate a `meta.xml` file that accurately reflects a **Star Schema** organization derived from a set of provided CSV files and an XSD metadata schema.

### **Contextual Building Blocks**

* **XSD Schema:**
--- BEGIN: XSD Schema ---

```xml
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" version="0.1" targetNamespace="http://rs.tdwg.org/dwc/text/" attributeFormDefault="unqualified" elementFormDefault="qualified">
    <xs:import namespace="http://rs.tdwg.org/dwc/terms/" schemaLocation="https://raw.githubusercontent.com/tdwg/dwc/master/docs/xml/tdwg_dwcterms.xsd" />
    <xs:import namespace="http://www.w3.org/XML/1998/namespace" schemaLocation="http://rs.gbif.org/schema/xml.xsd">
        <xs:annotation>
            <xs:documentation>
                Get access to the xml: attribute groups for xml:lang
            </xs:documentation>
        </xs:annotation>
    </xs:import>
    
    
    <xs:element name="archive">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="core" type="arch:coreFileType" maxOccurs="1" minOccurs="1" />
                <xs:element name="extension" type="arch:extensionFileType" maxOccurs="unbounded" minOccurs="0" />
            </xs:sequence>
            <xs:attribute name="metadata" type="xs:anyURI" use="optional" />
        </xs:complexType>
    </xs:element>

    
    <xs:attributeGroup name="fileAttributes">
        <xs:attribute name="linesTerminatedBy" type="xs:string" use="optional" default="\n" />
        <xs:attribute name="fieldsTerminatedBy" type="xs:string" use="optional" default="," />
        <xs:attribute name="fieldsEnclosedBy" type="xs:string" use="optional" default="&quot;" />
        <xs:attribute name="ignoreHeaderLines" type="xs:integer" use="optional" default="0" />
        <xs:attribute name="rowType" type="xs:string" use="required" />
        <xs:attribute name="encoding" type="xs:string" use="optional" default="UTF-8" />
        <xs:attribute name="dateFormat" type="xs:string" use="optional" default="YYYY-MM-DD" />
    </xs:attributeGroup>

    
    <xs:complexType name="fileType">
        <xs:sequence>
            <xs:element name="files" minOccurs="1" maxOccurs="1">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="location" type="xs:string" minOccurs="1" maxOccurs="unbounded" />
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
        </xs:sequence>
        <xs:attributeGroup ref="arch:fileAttributes" />
    </xs:complexType>

    
    <xs:complexType name="coreFileType">
        <xs:complexContent>
            <xs:extension base="arch:fileType">
                <xs:sequence>
                    <xs:element name="id" type="arch:idFieldType" minOccurs="0" maxOccurs="1" />
                    <xs:element name="field" type="arch:fieldType" minOccurs="1" maxOccurs="unbounded" />
                </xs:sequence>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>

    
    <xs:complexType name="extensionFileType">
        <xs:complexContent>
            <xs:extension base="arch:fileType">
                <xs:sequence>
                    <xs:element name="coreid" type="arch:idFieldType" minOccurs="1" maxOccurs="1" />
                    <xs:element name="field" type="arch:fieldType" minOccurs="1" maxOccurs="unbounded" />
                </xs:sequence>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>

    
    <xs:complexType name="idFieldType">
        <xs:attribute name="index" type="xs:integer" use="optional" />
    </xs:complexType>

    
    <xs:complexType name="fieldType">
        <xs:attribute name="index" type="xs:integer" use="optional">
            <xs:annotation>
                <xs:documentation>The index number of the column this field is represented in the source file(s). Indices start with 0.</xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="term" type="xs:anyURI" use="required">
            <xs:annotation>
                <xs:documentation>The unique, qualified identifier for the term, usually a URI. E.g. http://rs.tdwg.org/dwc/terms/scientificName</xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="default" type="xs:string" use="optional">
            <xs:annotation>
                <xs:documentation>A global default value that should be used in case the field doesnt have a column index or the actual value for the source record is NULL.</xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="vocabulary" type="xs:anyURI" use="optional">
            <xs:annotation>
                <xs:documentation>A URI that identifies a vocabulary used for the values found for the field in the source files. The URI ideally should resolve to some machine readable definition like SKOS, RDF, the GBIF vocabulary schema or a simple text file as often found for ISO or RFC standards. E.g. http://rs.gbif.org/vocabulary/gbif/nomenclatural_code.xml;   http://www.ietf.org/rfc/rfc3066.txt;   http://www.iso.org/iso/list-en1-semic-3.txt</xs:documentation> 
            </xs:annotation>
        </xs:attribute>
                <xs:attribute name="delimitedBy" type="xs:string" use="optional">
                        <xs:annotation>
                                <xs:documentation>Indicates an optional delimiter used for concatenating multiple values in a list.</xs:documentation>
                        </xs:annotation>
                </xs:attribute>
    </xs:complexType>
</xs:schema>
```

--- END: XSD Schema ---

* **Dataset file overview:**
--- BEGIN: Dataset file overview ---
==> /home/jovyan/work/_demo/dwc_data/masked-doi-10.34894-72gq4c/budburst_occurrence.csv <==
-- file stats --
os.stat_result(st_mode=33204, st_ino=3628, st_dev=36, st_nlink=1, st_uid=1000, st_gid=100, st_size=15323870, st_atime=1775803418, st_mtime=1774878780, st_ctime=1775548026)
==> /home/jovyan/work/_demo/dwc_data/masked-doi-10.34894-72gq4c/.DS_Store <==
-- file stats --
os.stat_result(st_mode=33188, st_ino=3992, st_dev=36, st_nlink=1, st_uid=1000, st_gid=100, st_size=6148, st_atime=1775737882, st_mtime=1775737882, st_ctime=1775737882)
==> /home/jovyan/work/_demo/dwc_data/masked-doi-10.34894-72gq4c/MANIFEST.TXT <==
-- file stats --
os.stat_result(st_mode=33204, st_ino=3629, st_dev=36, st_nlink=1, st_uid=1000, st_gid=100, st_size=249, st_atime=1775124087, st_mtime=1774878782, st_ctime=1774878925)
==> /home/jovyan/work/_demo/dwc_data/masked-doi-10.34894-72gq4c/budburst_extendedmeasurementorfact.csv <==
-- file stats --
os.stat_result(st_mode=33204, st_ino=3631, st_dev=36, st_nlink=1, st_uid=1000, st_gid=100, st_size=23804914, st_atime=1775803418, st_mtime=1774878780, st_ctime=1775742358)
==> /home/jovyan/work/_demo/dwc_data/masked-doi-10.34894-72gq4c/budburst_event.csv <==
-- file stats --
os.stat_result(st_mode=33204, st_ino=3632, st_dev=36, st_nlink=1, st_uid=1000, st_gid=100, st_size=19919400, st_atime=1775803418, st_mtime=1774878778, st_ctime=1775548026)
--- END: Dataset file overview ---

* **CSV Overview:**
--- BEGIN: CSV Overview ---
==> /home/jovyan/work/_demo/dwc_data/masked-doi-10.34894-72gq4c/budburst_occurrence.csv <==
-- head (3/86412 rows) --

```csv
eventID,occurrenceID,recordedByID,individualCount,basisOfRecord,occurrenceStatus,occurrenceRemarks,organismID,scientificName,kingdom,phylum,class,order,family,genus,specificEpithet
DO1997_93_1,DO1997_93_1_o1,,1,HumanObservation,present,,1,Quercus robur L.,Plantae,Tracheophyta,Magnoliopsida,Fagales,Fagaceae,Quercus,robur
DO1997_100_1,DO1997_100_1_o1,,1,HumanObservation,present,,1,Quercus robur L.,Plantae,Tracheophyta,Magnoliopsida,Fagales,Fagaceae,Quercus,robur
DO1997_108_1,DO1997_108_1_o1,,1,HumanObservation,present,,1,Quercus robur L.,Plantae,Tracheophyta,Magnoliopsida,Fagales,Fagaceae,Quercus,robur

```

-- column descriptive statistics (16 columns) --

```csv
eventID,occurrenceID,recordedByID,individualCount,basisOfRecord,occurrenceStatus,occurrenceRemarks,organismID,scientificName,kingdom,phylum,class,order,family,genus,specificEpithet
86412,86412,30681.0,86412.0,86412,86412,0.0,86412.0,86412,86412,86412,86412,86412,86412,86412,86412
86412,86412,,,1,1,,,3,1,1,1,1,2,2,3
DO1997_93_1,DO1997_93_1_o1,,,HumanObservation,present,,,Quercus robur L.,Plantae,Tracheophyta,Magnoliopsida,Fagales,Fagaceae,Quercus,robur
1,1,,,86412,86412,,,79075,86412,86412,86412,86412,84050,84050,79075
,,112.19334441511033,1.0,,,,289.740545294635,,,,,,,,
,,57.57223428350856,0.0,,,,188.55765865659922,,,,,,,,
,,53.0,1.0,,,,1.0,,,,,,,,
,,58.0,1.0,,,,109.0,,,,,,,,
,,162.0,1.0,,,,347.0,,,,,,,,
,,162.0,1.0,,,,442.0,,,,,,,,
,,461.0,1.0,,,,1054.0,,,,,,,,

```

==> /home/jovyan/work/_demo/dwc_data/masked-doi-10.34894-72gq4c/budburst_extendedmeasurementorfact.csv <==
-- head (3/172824 rows) --

```csv
measurementID,eventID,measurementType,measurementValue,measurementUnit,measurementMethod,measurementRemarks
DO1997_93_1_1_m1,DO1997_93_1,bud burst stage (PO:0025532) of the tree crown,1.5,,https://doi.org/10.1098/rspb.2000.1363,
DO1997_93_1_1_m2,DO1997_93_1,bud burst stage (PO:0025532) of the whole tree,1.0,,https://doi.org/10.1098/rspb.2000.1363,
DO1997_100_1_1_m1,DO1997_100_1,bud burst stage (PO:0025532) of the tree crown,2.0,,https://doi.org/10.1098/rspb.2000.1363,

```

-- column descriptive statistics (7 columns) --

```csv
measurementID,eventID,measurementType,measurementValue,measurementUnit,measurementMethod,measurementRemarks
172824,172824,172824,168621.0,0.0,172824,0.0
172824,86412,2,,,1,
DO1997_93_1_1_m1,DO1997_93_1,bud burst stage (PO:0025532) of the tree crown,,,https://doi.org/10.1098/rspb.2000.1363,
1,2,86412,,,172824,
,,,1.2968432164439778,,,
,,,1.228758095551537,,,
,,,0.0,,,
,,,0.0,,,
,,,1.0,,,
,,,3.0,,,
,,,3.0,,,

```

==> /home/jovyan/work/_demo/dwc_data/masked-doi-10.34894-72gq4c/budburst_event.csv <==
-- head (3/87901 rows) --

```csv
eventID,parentEventID,samplingProtocol,sampleSizeValue,sampleSizeUnit,eventDate,year,month,day,country,countryCode,verbatimLocality,minimumElevationInMeters,maximumElevationInMeters,decimalLatitude,decimalLongitude,geodeticDatum,type,language,institutionID,institutionCode
HV1988,,,,,1988,1988,,,Netherlands,NL,Hoge Veluwe,,,,,,Event,en,https://ror.org/01g25jp36,NIOO
HV1988_119,HV1988,,,,1988-04-28,1988,4.0,28.0,Netherlands,NL,Hoge Veluwe,,,,,,Event,en,https://ror.org/01g25jp36,NIOO
HV1988_119_100,HV1988_119,https://doi.org/10.1098/rspb.2000.1363,1.0,tree,1988-04-28,1988,4.0,28.0,Netherlands,NL,Hoge Veluwe,44.714127,44.714127,52.038898,5.854294,EPSG:4326,Event,en,https://ror.org/01g25jp36,NIOO

```

-- column descriptive statistics (21 columns) --

```csv
eventID,parentEventID,samplingProtocol,sampleSizeValue,sampleSizeUnit,eventDate,year,month,day,country,countryCode,verbatimLocality,minimumElevationInMeters,maximumElevationInMeters,decimalLatitude,decimalLongitude,geodeticDatum,type,language,institutionID,institutionCode
87901,87762,86412,86412.0,86412,87901,87901.0,87762.0,87762.0,87901,87901,87901,58254.0,58254.0,79646.0,79646.0,79646,87901,87901,87901,87901
87901,1489,1,,1,757,,,,1,1,12,,,,,1,1,1,1,1
HV1988,HV2009_100,https://doi.org/10.1098/rspb.2000.1363,,tree,2003-04-18,,,,Netherlands,NL,Hoge Veluwe,,,,,EPSG:4326,Event,en,https://ror.org/01g25jp36,NIOO
1,228,86412,,86412,471,,,,87901,87901,52930,,,,,79646,87901,87901,87901,87901
,,,1.0,,,2007.883414295628,4.30938219274857,14.980276201545088,,,,38.56538479153363,38.56538479153363,52.00101690285915,5.845161293323469,,,,,
,,,0.0,,,10.083909185243117,0.5283375437980385,8.597487059799164,,,,7.854076203376951,7.854076203376951,0.06333611346133271,0.021302588498345872,,,,,
,,,1.0,,,1988.0,3.0,1.0,,,,11.011856,11.011856,51.871706,5.772055,,,,,
,,,1.0,,,1999.0,4.0,8.0,,,,36.651417,36.651417,51.976436,5.842932,,,,,
,,,1.0,,,2008.0,4.0,14.0,,,,40.933384,40.933384,52.03532802,5.847082,,,,,
,,,1.0,,,2016.0,5.0,23.0,,,,43.856155,43.856155,52.040435,5.854766,,,,,
,,,1.0,,,2025.0,6.0,31.0,,,,50.767769,50.767769,52.046317,5.867651,,,,,

```

--- END: CSV Overview ---

### **Task: Star Schema Identification**

Before generating the XML, you must analyze the relationship between the provided CSV files to establish the Star Schema:

* **Identify the Core:** Locate the primary entity file (the "Core") which contains the base records (e.g., Events or Taxa) that other files reference.
* **Identify Extensions:** Locate subordinate files (the "Extensions") that provide many-to-one supplemental data to the Core records.
* **Identify the Linkage:** Determine the specific column (the foreign key) used to join Extension records back to the Core's unique identifier.

### **Technical Logic & Mapping Rules**

Generate the XML following the `<archive>` structure. Where metadata is missing or ambiguous, you must insert placeholders using the syntax: `{{GAP_XXX:TYPE:DESCRIPTION}}`.

**1. Disambiguation of Gap TYPEs:**

* **INDEX:** Use for `0-based` column positions.
* **URI:** Use for the `rowType` or `term` attributes.
* **STRING:** Use for general file attributes (e.g., `encoding`, `fieldsTerminatedBy`).

**2. Strict Mapping Rules:**

* **Term Mapping:** If a CSV header name matches a known Darwin Core term, use that URI for the `term` attribute; **otherwise**, generate a `{{GAP_XXX:URI:HEADER_NAME}}` placeholder.
* **Index Mapping:** If the column index can be provided with absolute certainty from the CSV header order, specify it directly (e.g., `index="0"`); **otherwise**, generate a `{{GAP_XXX:INDEX:COLUMN_NAME}}` placeholder.

### **Mapping Instructions**

1. **Archive Attributes:** Set the `metadata` attribute to a `URI` gap.
2. **Core Component:** * Identify the appropriate `rowType` URI.
    * Map the primary key to the `<id>` element.
    * Map all remaining columns to `<field>` elements using the Mapping Rules above.
3. **Extension Components:**
    * For each extension, map the foreign key to the `<coreid>` element.
    * Map extension columns to `<field>` elements using the Mapping Rules above.

### **Expected Output Format**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="{{GAP_001:URI:METADATA_LOCATION}}">
  <core rowType="[CORE_URI]" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" ignoreHeaderLines="1">
    <files>
      <location>[CORE_FILENAME]</location>
    </files>
    <id index="[PRIMARY_KEY_INDEX]" />
    <field index="1" term="http://rs.tdwg.org/dwc/terms/exampleTerm"/>
    <field index="{{GAP_002:INDEX:UNCERTAIN_COL}}" term="{{GAP_003:URI:UNMAPPED_HEADER}}"/>
  </core>
  <extension rowType="[EXTENSION_URI]">
    <files>
      <location>[EXTENSION_FILENAME]</location>
    </files>
    <coreid index="[FOREIGN_KEY_INDEX]" />
    </extension>
</archive>
```

> -- END: Prompt

---

> -- BEGIN: Response

```xml
<?xml version="1.0" encoding="UTF-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="{{GAP_001:URI:METADATA_LOCATION}}">
  <!-- Star Schema: Core = occurrence records; Extensions = measurements (many-to-one by eventID) -->

  <core rowType="http://rs.tdwg.org/dwc/terms/Occurrence" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" ignoreHeaderLines="1">
    <files>
      <location>budburst_occurrence.csv</location>
    </files>

    <!-- eventID, occurrenceID exist; choose occurrence-level primary key -->
    <id index="1" />

    <field index="0" term="http://rs.tdwg.org/dwc/terms/eventID"/>
    <field index="2" term="http://rs.tdwg.org/dwc/terms/recordedByID"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/individualCount"/>
    <field index="4" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/occurrenceStatus"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/occurrenceRemarks"/>
    <field index="7" term="http://rs.tdwg.org/dwc/terms/organismID"/>
    <field index="8" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
    <field index="9" term="{{GAP_010:URI:KINGDOM}}"/>
    <field index="10" term="{{GAP_011:URI:PHYLUM}}"/>
    <field index="11" term="{{GAP_012:URI:CLASS}}"/>
    <field index="12" term="{{GAP_013:URI:ORDER}}"/>
    <field index="13" term="{{GAP_014:URI:FAMILY}}"/>
    <field index="14" term="{{GAP_015:URI:GENUS}}"/>
    <field index="15" term="{{GAP_016:URI:SPECIFIC_EPITHET}}"/>
  </core>

  <extension rowType="http://rs.tdwg.org/dwc/terms/MeasurementOrFact" linesTerminatedBy="\n" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" ignoreHeaderLines="1">
    <files>
      <location>budburst_extendedmeasurementorfact.csv</location>
    </files>

    <!-- measurement file links to core via eventID -->
    <coreid index="0"/>

    <field index="0" term="http://rs.tdwg.org/dwc/terms/eventID"/>
    <field index="-1" term="{{GAP_020:URI:MEASUREMENT_FACT_PRIMARY_KEY}}" default="{{GAP_021:STRING:USE_MEASUREMENT_ID_AS_ID}}"/>
    <field index="0" term="http://rs.tdwg.org/dwc/terms/measurementID"/>

    <!-- Column indices in measurement CSV (from header order):
         measurementID(0), eventID(1), measurementType(2), measurementValue(3), measurementUnit(4), measurementMethod(5), measurementRemarks(6)
    -->
    <field index="2" term="http://rs.tdwg.org/dwc/terms/type"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/measurementValue"/>
    <field index="4" term="http://rs.tdwg.org/dwc/terms/measurementUnit"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/measurementMethod"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/measurementRemarks"/>
  </extension>
</archive>
```

> -- END: Response

---

# XML Blueprint Review Agent

This is a sophisticated multi-agent design. The critical success factor here is ensuring the **XML Blueprint Reviewer** doesn't just "copy-paste" the gap text, but actually synthesizes the architectural context from the blueprint and maps it to the file metadata provided in the initial context.

Here is a structured system prompt designed for the **XML Blueprint Reviewer Agent**.

---

## System Prompt: XML Blueprint Reviewer

### Role

You are a **Technical Metadata Analyst** specializing in Darwin Core (DwC) standards and XML Schema validation. Your purpose is to bridge the gap between a high-level XML blueprint and actionable data exploration tasks.

### Input Context

You will be provided with:

1. **The Original Design Context:** The XSD schema goals and high-level overviews of the available CSV datasets (columns and headers).
2. **The XML Blueprint:** A draft `meta.xml` or DwC-Archive metadata file containing placeholders in the format `{{GAP_ID:GAP_TYPE:GAP_DESCRIPTION}}`.

### Instructions

1. **Analyze the Blueprint:** Locate every placeholder matching the pattern `{{GAP_ID:GAP_TYPE:GAP_DESCRIPTION}}`.
2. **Scope Determination:** For each gap, identify which CSV file(s) from the Dataset Inventory contain the raw data necessary to resolve it (e.g., if the gap is in `dwc:scientificName`, scope it to the file containing taxonomic strings).
3. **Draft Derivation Requests:** Write a specific, standalone instruction for the **Gap Derivation Agent**. This agent can execute Python/SQL to explore CSVs. Your instruction must:
    * State exactly what to look for.
    * Provide logic for handling anomalies (e.g., "If `eventDate` is null, use the file's 'Date Collected' column").
    * Define a **Meaningful Default** (e.g., "If no coordinate system is found, default to 'WGS84'").
4. **Output Format:** Return a valid JSON list of objects matching the `MetadataGap` schema.

---

### Extraction Schema

Return the data in this structure:

```json
[
  {
    "gap_id": "Unique string from the gap pattern",
    "gap_type": "The category (e.g., Attribute, Element, Mapping)",
    "gap_description": "Brief explanation of what is missing",
    "gap_replacement_pattern": "The exact full string to be replaced (e.g., '{{GAP_001:ELEMENT:Collection_Code}}')",
    "gap_scope_files": ["list_of_relevant_filenames.csv"],
    "gap_derivation_request": "Detailed prompt for the execution agent. Include: 1. Goal 2. Column logic 3. Transformation rules (if any) 4. Fallback/Default value strategy."
  }
]
```

### Constraints & Quality Gates

* **No Hallucinations:** Only include gaps explicitly marked in the Blueprint.
* **Atomicity:** Each `gap_derivation_request` must be a self-contained prompt. Do not refer to "the previous message" or "other gaps."
* **Precision:** The `gap_replacement_pattern` must be an **exact string match** to allow for programmatic `string.replace()` operations later.

---

## Review Execution

**Please process the following input:**

**[ORIGINAL CONTEXT]**
{Insert context from Step 4 here}

**[XML BLUEPRINT]**
{Insert output from Step 6 here}

---

> -- BEGIN: Response

```json
[
  {
    "gap_id": "GAP_001",
    "gap_type": "URI",
    "gap_description": "Metadata location for the archive",
    "gap_replacement_pattern": "{{GAP_001:URI:METADATA_LOCATION}}",
    "gap_scope_files": ["MANIFEST.TXT"],
    "gap_derivation_request": "Goal: Identify the URI or relative path for the metadata description file (e.g., eml.xml). Logic: Check MANIFEST.TXT for any filenames ending in .xml that are not meta.xml. Fallback: If no dedicated metadata file is referenced, use an empty string or 'eml.xml' as a placeholder."
  },
  {
    "gap_id": "GAP_010",
    "gap_type": "URI",
    "gap_description": "Darwin Core URI for KINGDOM",
    "gap_replacement_pattern": "{{GAP_010:URI:KINGDOM}}",
    "gap_scope_files": ["budburst_occurrence.csv"],
    "gap_derivation_request": "Goal: Map the 'kingdom' column to the formal Darwin Core URI. Logic: Verify if 'kingdom' values align with biological taxonomy. Transformation: Map to 'http://rs.tdwg.org/dwc/terms/kingdom'. Default: 'http://rs.tdwg.org/dwc/terms/kingdom'."
  },
  {
    "gap_id": "GAP_011",
    "gap_type": "URI",
    "gap_description": "Darwin Core URI for PHYLUM",
    "gap_replacement_pattern": "{{GAP_011:URI:PHYLUM}}",
    "gap_scope_files": ["budburst_occurrence.csv"],
    "gap_derivation_request": "Goal: Map the 'phylum' column to the formal Darwin Core URI. Logic: Confirm column contains taxonomic phylum data. Transformation: Map to 'http://rs.tdwg.org/dwc/terms/phylum'. Default: 'http://rs.tdwg.org/dwc/terms/phylum'."
  },
  {
    "gap_id": "GAP_012",
    "gap_type": "URI",
    "gap_description": "Darwin Core URI for CLASS",
    "gap_replacement_pattern": "{{GAP_012:URI:CLASS}}",
    "gap_scope_files": ["budburst_occurrence.csv"],
    "gap_derivation_request": "Goal: Map the 'class' column to the formal Darwin Core URI. Logic: Confirm column contains taxonomic class data. Transformation: Map to 'http://rs.tdwg.org/dwc/terms/class'. Default: 'http://rs.tdwg.org/dwc/terms/class'."
  },
  {
    "gap_id": "GAP_013",
    "gap_type": "URI",
    "gap_description": "Darwin Core URI for ORDER",
    "gap_replacement_pattern": "{{GAP_013:URI:ORDER}}",
    "gap_scope_files": ["budburst_occurrence.csv"],
    "gap_derivation_request": "Goal: Map the 'order' column to the formal Darwin Core URI. Logic: Confirm column contains taxonomic order data. Transformation: Map to 'http://rs.tdwg.org/dwc/terms/order'. Default: 'http://rs.tdwg.org/dwc/terms/order'."
  },
  {
    "gap_id": "GAP_014",
    "gap_type": "URI",
    "gap_description": "Darwin Core URI for FAMILY",
    "gap_replacement_pattern": "{{GAP_014:URI:FAMILY}}",
    "gap_scope_files": ["budburst_occurrence.csv"],
    "gap_derivation_request": "Goal: Map the 'family' column to the formal Darwin Core URI. Logic: Confirm column contains taxonomic family data. Transformation: Map to 'http://rs.tdwg.org/dwc/terms/family'. Default: 'http://rs.tdwg.org/dwc/terms/family'."
  },
  {
    "gap_id": "GAP_015",
    "gap_type": "URI",
    "gap_description": "Darwin Core URI for GENUS",
    "gap_replacement_pattern": "{{GAP_015:URI:GENUS}}",
    "gap_scope_files": ["budburst_occurrence.csv"],
    "gap_derivation_request": "Goal: Map the 'genus' column to the formal Darwin Core URI. Logic: Confirm column contains taxonomic genus data. Transformation: Map to 'http://rs.tdwg.org/dwc/terms/genus'. Default: 'http://rs.tdwg.org/dwc/terms/genus'."
  },
  {
    "gap_id": "GAP_016",
    "gap_type": "URI",
    "gap_description": "Darwin Core URI for SPECIFIC_EPITHET",
    "gap_replacement_pattern": "{{GAP_016:URI:SPECIFIC_EPITHET}}",
    "gap_scope_files": ["budburst_occurrence.csv"],
    "gap_derivation_request": "Goal: Map the 'specificEpithet' column to the formal Darwin Core URI. Logic: Confirm column contains the species-specific part of the scientific name. Transformation: Map to 'http://rs.tdwg.org/dwc/terms/specificEpithet'. Default: 'http://rs.tdwg.org/dwc/terms/specificEpithet'."
  },
  {
    "gap_id": "GAP_020",
    "gap_type": "URI",
    "gap_description": "Primary key term for MeasurementOrFact",
    "gap_replacement_pattern": "{{GAP_020:URI:MEASUREMENT_FACT_PRIMARY_KEY}}",
    "gap_scope_files": ["budburst_extendedmeasurementorfact.csv"],
    "gap_derivation_request": "Goal: Identify the appropriate term URI for the primary identifier of the extension records. Logic: If the file uses 'measurementID' as its unique record identifier, the term should reflect that. Transformation: Map to 'http://rs.tdwg.org/dwc/terms/measurementID'. Default: 'http://rs.tdwg.org/dwc/terms/measurementID'."
  },
  {
    "gap_id": "GAP_021",
    "gap_type": "STRING",
    "gap_description": "Logic for primary key fallback",
    "gap_replacement_pattern": "{{GAP_021:STRING:USE_MEASUREMENT_ID_AS_ID}}",
    "gap_scope_files": ["budburst_extendedmeasurementorfact.csv"],
    "gap_derivation_request": "Goal: Determine a fallback value or mapping logic for the primary key if the index is -1. Logic: Check if 'measurementID' is globally unique across the file. Fallback: If 'measurementID' is unique, return the string 'measurementID'. Otherwise, suggest a row-index based default."
  }
]
```
