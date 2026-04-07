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

> Prompt

## **PROMPT FOR SUB-AGENT: DwC-A XML ARCHITECT**

### **Role**

You are a precision XML Developer specializing in Darwin Core Archive (DwC-A) structures. Your task is to generate a `meta.xml` file that accurately reflects a **Star Schema** organization derived from a set of provided CSV files and an XSD metadata schema.

### **Contextual Building Blocks**

* **XSD Schema:**
--- BEGIN: XSD Schema ---
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
    <!--  The root element of the document is an archive  -->
    <xs:element name="archive">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="core" type="arch:coreFileType" maxOccurs="1" minOccurs="1" />
                <xs:element name="extension" type="arch:extensionFileType" maxOccurs="unbounded" minOccurs="0" />
            </xs:sequence>
            <xs:attribute name="metadata" type="xs:anyURI" use="optional" />
        </xs:complexType>
    </xs:element>
    <!--  attributes shared across all file types, core or extensions  -->
    <xs:attributeGroup name="fileAttributes">
        <xs:attribute name="linesTerminatedBy" type="xs:string" use="optional" default="\n" />
        <xs:attribute name="fieldsTerminatedBy" type="xs:string" use="optional" default="," />
        <xs:attribute name="fieldsEnclosedBy" type="xs:string" use="optional" default="""/>
<xs:attribute name=" ignoreHeaderLines" type="xs:integer" use="optional" default="0" />
        <xs:attribute name="rowType" type="xs:string" use="required" />
        <xs:attribute name="encoding" type="xs:string" use="optional" default="UTF-8" />
        <xs:attribute name="dateFormat" type="xs:string" use="optional" default="YYYY-MM-DD" />
    </xs:attributeGroup>
    <!--  The file within an archive defines the description and it's fields  -->
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
    <!--  a file representing the core file in a star schema  -->
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
    <!--  a file representing an extension file in a star schema  -->
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
    <!--  A field represents a column within the file  -->
    <xs:complexType name="idFieldType">
        <xs:attribute name="index" type="xs:integer" use="optional" />
    </xs:complexType>
    <!--  A field represents a column within the file  -->
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
--- END: XSD Schema ---

* **CSV Overview:**
--- BEGIN: CSV Overview ---

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

---

> Response

Based on an analysis of your provided CSV files and the Darwin Core Archive (DwC-A) Star Schema requirements, I have identified the following structure:

* **Core Entity:** `budburst_event.csv` (Event Core).
* **Extensions:** `budburst_occurrence.csv` and `budburst_extendedmeasurementorfact.csv`.
* **Linkage:** Both extensions link back to the Core via the `eventID` column.

Here is the generated `meta.xml` file following your mapping logic and gap-filling requirements.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="{{GAP_001:URI:METADATA_LOCATION}}">
  
  <core rowType="http://rs.tdwg.org/dwc/terms/Event" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" linesTerminatedBy="\n" ignoreHeaderLines="1" encoding="UTF-8">
    <files>
      <location>budburst_event.csv</location>
    </files>
    <id index="0" /> <field index="1" term="http://rs.tdwg.org/dwc/terms/parentEventID"/>
    <field index="2" term="http://rs.tdwg.org/dwc/terms/samplingProtocol"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/sampleSizeValue"/>
    <field index="4" term="http://rs.tdwg.org/dwc/terms/sampleSizeUnit"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/eventDate"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/year"/>
    <field index="7" term="http://rs.tdwg.org/dwc/terms/month"/>
    <field index="8" term="http://rs.tdwg.org/dwc/terms/day"/>
    <field index="9" term="http://rs.tdwg.org/dwc/terms/country"/>
    <field index="10" term="http://rs.tdwg.org/dwc/terms/countryCode"/>
    <field index="11" term="http://rs.tdwg.org/dwc/terms/verbatimLocality"/>
    <field index="12" term="http://rs.tdwg.org/dwc/terms/minimumElevationInMeters"/>
    <field index="13" term="http://rs.tdwg.org/dwc/terms/maximumElevationInMeters"/>
    <field index="14" term="http://rs.tdwg.org/dwc/terms/decimalLatitude"/>
    <field index="15" term="http://rs.tdwg.org/dwc/terms/decimalLongitude"/>
    <field index="16" term="http://rs.tdwg.org/dwc/terms/geodeticDatum"/>
    <field index="17" term="http://purl.org/dc/terms/type"/>
    <field index="18" term="http://purl.org/dc/terms/language"/>
    <field index="19" term="http://rs.tdwg.org/dwc/terms/institutionID"/>
    <field index="20" term="http://rs.tdwg.org/dwc/terms/institutionCode"/>
  </core>

  <extension rowType="http://rs.tdwg.org/dwc/terms/Occurrence" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" linesTerminatedBy="\n" ignoreHeaderLines="1" encoding="UTF-8">
    <files>
      <location>budburst_occurrence.csv</location>
    </files>
    <coreid index="0" /> <field index="1" term="http://rs.tdwg.org/dwc/terms/occurrenceID"/>
    <field index="2" term="http://rs.tdwg.org/dwc/terms/recordedByID"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/individualCount"/>
    <field index="4" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/occurrenceStatus"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/occurrenceRemarks"/>
    <field index="7" term="http://rs.tdwg.org/dwc/terms/organismID"/>
    <field index="8" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
    <field index="9" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
    <field index="10" term="http://rs.tdwg.org/dwc/terms/phylum"/>
    <field index="11" term="http://rs.tdwg.org/dwc/terms/class"/>
    <field index="12" term="http://rs.tdwg.org/dwc/terms/order"/>
    <field index="13" term="http://rs.tdwg.org/dwc/terms/family"/>
    <field index="14" term="http://rs.tdwg.org/dwc/terms/genus"/>
    <field index="15" term="http://rs.tdwg.org/dwc/terms/specificEpithet"/>
  </extension>

  <extension rowType="http://rs.gbif.org/terms/1.0/MeasurementOrFact" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" linesTerminatedBy="\n" ignoreHeaderLines="1" encoding="UTF-8">
    <files>
      <location>budburst_extendedmeasurementorfact.csv</location>
    </files>
    <coreid index="1" /> <field index="0" term="http://rs.tdwg.org/dwc/terms/measurementID"/>
    <field index="2" term="http://rs.tdwg.org/dwc/terms/measurementType"/>
    <field index="3" term="http://rs.tdwg.org/dwc/terms/measurementValue"/>
    <field index="4" term="http://rs.tdwg.org/dwc/terms/measurementUnit"/>
    <field index="5" term="http://rs.tdwg.org/dwc/terms/measurementMethod"/>
    <field index="6" term="http://rs.tdwg.org/dwc/terms/measurementRemarks"/>
  </extension>

</archive>
```
