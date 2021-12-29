// Code generated by aas-core-codegen. DO NOT EDIT.

package aascore

type HasSemantics struct {
	SemanticId *Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type Extension struct {
	SemanticId *Reference
	Name       string
	ValueType  *DataTypeDef
	Value      string
	RefersTo   *Reference
}

type HasExtensions struct {
	Extensions []Extension
}

type Referable struct {
	Extensions  []Extension
	IdShort     string
	DisplayName *LangStringSet
	Category    string
	Description *LangStringSet
}

type Identifiable struct {
	Extensions     []Extension
	IdShort        string
	DisplayName    *LangStringSet
	Category       string
	Description    *LangStringSet
	Id             string
	Administration *AdministrativeInformation
}

//TODO: transform_document NOT_IMPLEMENTED
type ModelingKind int32

const (
	ModelingKind_TEMPLATE ModelingKind = iota
	ModelingKind_INSTANCE
)

var ModelingKind_name = map[ModelingKind]string{
	0: "TEMPLATE",
	1: "INSTANCE",
}

var ModelingKind_value = map[string]ModelingKind{
	"TEMPLATE": 0,
	"INSTANCE": 1,
}

func (s ModelingKind) String() string {
	return ModelingKind_name[s]
}

func GetModelingKindValue(n string) ModelingKind {
	return ModelingKind_value[n]
}

func GetModelingKindName(v ModelingKind) string {
	return ModelingKind_name[v]
}

type HasKind struct {
	Kind *ModelingKind
}

type HasDataSpecification struct {
	DataSpecifications []Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type AdministrativeInformation struct {
	DataSpecifications []Reference
	Version            string
	Revision           string
}

type Constraint struct {
}

type Qualifiable struct {
	Qualifiers []Constraint
}

//TODO: transform_document NOT_IMPLEMENTED
type Qualifier struct {
	SemanticId *Reference
	Type       string
	ValueType  *DataTypeDef
	Value      string
	ValueId    *Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type Formula struct {
	DependsOn []Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type AssetAdministrationShell struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Id                 string
	Administration     *AdministrativeInformation
	DerivedFrom        Todo
	AssetInformation   *AssetInformation
	Submodels          []Todo
}

//TODO: transform_document NOT_IMPLEMENTED
type AssetInformation struct {
	AssetKind        *AssetKind
	GlobalAssetId    *Reference
	SpecificAssetId  *IdentifierKeyValuePair
	DefaultThumbnail *File
}

//TODO: transform_document NOT_IMPLEMENTED
type AssetKind int32

const (
	AssetKind_TYPE AssetKind = iota
	AssetKind_INSTANCE
)

var AssetKind_name = map[AssetKind]string{
	0: "TYPE",
	1: "INSTANCE",
}

var AssetKind_value = map[string]AssetKind{
	"TYPE":     0,
	"INSTANCE": 1,
}

func (s AssetKind) String() string {
	return AssetKind_name[s]
}

func GetAssetKindValue(n string) AssetKind {
	return AssetKind_value[n]
}

func GetAssetKindName(v AssetKind) string {
	return AssetKind_name[v]
}

//TODO: transform_document NOT_IMPLEMENTED
type IdentifierKeyValuePair struct {
	SemanticId        *Reference
	Key               string
	Value             string
	ExternalSubjectId *Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type Submodel struct {
	DataSpecifications []Reference
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Id                 string
	Administration     *AdministrativeInformation
	SubmodelElements   []SubmodelElement
}

type SubmodelElement struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
}

type RelationshipElement struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	First              *Reference
	Second             *Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type SubmodelElementList struct {
	DataSpecifications        []Reference
	Extensions                []Extension
	IdShort                   string
	DisplayName               *LangStringSet
	Category                  string
	Description               *LangStringSet
	Kind                      *ModelingKind
	SemanticId                *Reference
	Qualifiers                []Constraint
	SubmodelElementTypeValues *SubmodelElements
	Values                    []SubmodelElement
	SemanticIdValues          *Reference
	ValueTypeValues           *DataTypeDef
}

//TODO: transform_document NOT_IMPLEMENTED
type SubmodelElementStruct struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	Values             []SubmodelElement
}

type DataElement struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
}

//TODO: transform_document NOT_IMPLEMENTED
type Property struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	ValueType          *DataTypeDef
	Value              string
	ValueId            *Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type MultiLanguageProperty struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	Translatable       *LangStringSet
	ValueId            *Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type Range struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	ValueType          *DataTypeDef
	Min                string
	Max                string
}

//TODO: transform_document NOT_IMPLEMENTED
type ReferenceElement struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	Reference          *Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type Blob struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	MimeType           string
	Content            []byte
}

//TODO: transform_document NOT_IMPLEMENTED
type File struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	MimeType           string
	Value              string
}

//TODO: transform_document NOT_IMPLEMENTED
type AnnotatedRelationshipElement struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	First              *Reference
	Second             *Reference
	Annotation         []DataElement
}

//TODO: transform_document NOT_IMPLEMENTED
type EntityType int32

const (
	EntityType_CO_MANAGED_ENTITY EntityType = iota
	EntityType_SELF_MANAGED_ENTITY
)

var EntityType_name = map[EntityType]string{
	0: "CO_MANAGED_ENTITY",
	1: "SELF_MANAGED_ENTITY",
}

var EntityType_value = map[string]EntityType{
	"CO_MANAGED_ENTITY":   0,
	"SELF_MANAGED_ENTITY": 1,
}

func (s EntityType) String() string {
	return EntityType_name[s]
}

func GetEntityTypeValue(n string) EntityType {
	return EntityType_value[n]
}

func GetEntityTypeName(v EntityType) string {
	return EntityType_name[v]
}

//TODO: transform_document NOT_IMPLEMENTED
type Entity struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	EntityType         *EntityType
	Statements         []SubmodelElement
	GlobalAssetId      *Reference
	SpecificAssetId    *IdentifierKeyValuePair
}

type Event struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
}

//TODO: transform_document NOT_IMPLEMENTED
type BasicEvent struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	Observed           Todo
}

//TODO: transform_document NOT_IMPLEMENTED
type Operation struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
	InputVariables     []OperationVariable
	OutputVariables    []OperationVariable
	InoutputVariables  []OperationVariable
}

//TODO: transform_document NOT_IMPLEMENTED
type OperationVariable struct {
	Value *SubmodelElement
}

//TODO: transform_document NOT_IMPLEMENTED
type Capability struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Kind               *ModelingKind
	SemanticId         *Reference
	Qualifiers         []Constraint
}

//TODO: transform_document NOT_IMPLEMENTED
type ConceptDescription struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	Id                 string
	Administration     *AdministrativeInformation
	IsCaseOf           []Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type View struct {
	DataSpecifications []Reference
	Extensions         []Extension
	IdShort            string
	DisplayName        *LangStringSet
	Category           string
	Description        *LangStringSet
	SemanticId         *Reference
	ContainedElements  []Todo
}

type Reference struct {
}

//TODO: transform_document NOT_IMPLEMENTED
type GlobalReference struct {
	Values []string
}

//TODO: transform_document NOT_IMPLEMENTED
type ModelReference struct {
	Keys               []Key
	ReferredSemanticId *Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type Key struct {
	Type  *KeyElements
	Value string
}

//TODO: transform_document NOT_IMPLEMENTED
type IdentifiableElements int32

const (
	IdentifiableElements_ASSET_ADMINISTRATION_SHELL IdentifiableElements = iota
	IdentifiableElements_CONCEPT_DESCRIPTION
	IdentifiableElements_SUBMODEL
)

var IdentifiableElements_name = map[IdentifiableElements]string{
	0: "ASSET_ADMINISTRATION_SHELL",
	1: "CONCEPT_DESCRIPTION",
	2: "SUBMODEL",
}

var IdentifiableElements_value = map[string]IdentifiableElements{
	"ASSET_ADMINISTRATION_SHELL": 0,
	"CONCEPT_DESCRIPTION":        1,
	"SUBMODEL":                   2,
}

func (s IdentifiableElements) String() string {
	return IdentifiableElements_name[s]
}

func GetIdentifiableElementsValue(n string) IdentifiableElements {
	return IdentifiableElements_value[n]
}

func GetIdentifiableElementsName(v IdentifiableElements) string {
	return IdentifiableElements_name[v]
}

//TODO: transform_document NOT_IMPLEMENTED
type ReferableElements int32

const (
	ReferableElements_ACCESS_PERMISSION_RULE ReferableElements = iota
	ReferableElements_ANNOTATED_RELATIONSHIP_ELEMENT
	ReferableElements_ASSET
	ReferableElements_ASSET_ADMINISTRATION_SHELL
	ReferableElements_BASIC_EVENT
	ReferableElements_BLOB
	ReferableElements_CAPABILITY
	ReferableElements_CONCEPT_DESCRIPTION
	ReferableElements_DATA_ELEMENT
	ReferableElements_ENTITY
	ReferableElements_EVENT
	ReferableElements_FILE
	ReferableElements_MULTI_LANGUAGE_PROPERTY
	ReferableElements_OPERATION
	ReferableElements_PROPERTY
	ReferableElements_RANGE
	ReferableElements_REFERENCE_ELEMENT
	ReferableElements_RELATIONSHIP_ELEMENT
	ReferableElements_SUBMODEL
	ReferableElements_SUBMODEL_ELEMENT
	ReferableElements_SUBMODEL_ELEMENT_LIST
	ReferableElements_SUBMODEL_ELEMENT_STRUCT
)

var ReferableElements_name = map[ReferableElements]string{
	0:  "ACCESS_PERMISSION_RULE",
	1:  "ANNOTATED_RELATIONSHIP_ELEMENT",
	2:  "ASSET",
	3:  "ASSET_ADMINISTRATION_SHELL",
	4:  "BASIC_EVENT",
	5:  "BLOB",
	6:  "CAPABILITY",
	7:  "CONCEPT_DESCRIPTION",
	8:  "DATA_ELEMENT",
	9:  "ENTITY",
	10: "EVENT",
	11: "FILE",
	12: "MULTI_LANGUAGE_PROPERTY",
	13: "OPERATION",
	14: "PROPERTY",
	15: "RANGE",
	16: "REFERENCE_ELEMENT",
	17: "RELATIONSHIP_ELEMENT",
	18: "SUBMODEL",
	19: "SUBMODEL_ELEMENT",
	20: "SUBMODEL_ELEMENT_LIST",
	21: "SUBMODEL_ELEMENT_STRUCT",
}

var ReferableElements_value = map[string]ReferableElements{
	"ACCESS_PERMISSION_RULE":         0,
	"ANNOTATED_RELATIONSHIP_ELEMENT": 1,
	"ASSET":                          2,
	"ASSET_ADMINISTRATION_SHELL":     3,
	"BASIC_EVENT":                    4,
	"BLOB":                           5,
	"CAPABILITY":                     6,
	"CONCEPT_DESCRIPTION":            7,
	"DATA_ELEMENT":                   8,
	"ENTITY":                         9,
	"EVENT":                          10,
	"FILE":                           11,
	"MULTI_LANGUAGE_PROPERTY":        12,
	"OPERATION":                      13,
	"PROPERTY":                       14,
	"RANGE":                          15,
	"REFERENCE_ELEMENT":              16,
	"RELATIONSHIP_ELEMENT":           17,
	"SUBMODEL":                       18,
	"SUBMODEL_ELEMENT":               19,
	"SUBMODEL_ELEMENT_LIST":          20,
	"SUBMODEL_ELEMENT_STRUCT":        21,
}

func (s ReferableElements) String() string {
	return ReferableElements_name[s]
}

func GetReferableElementsValue(n string) ReferableElements {
	return ReferableElements_value[n]
}

func GetReferableElementsName(v ReferableElements) string {
	return ReferableElements_name[v]
}

//TODO: transform_document NOT_IMPLEMENTED
type KeyElements int32

const (
	KeyElements_FRAGMENT_REFERENCE KeyElements = iota
	KeyElements_ACCESS_PERMISSION_RULE
	KeyElements_ANNOTATED_RELATIONSHIP_ELEMENT
	KeyElements_ASSET
	KeyElements_ASSET_ADMINISTRATION_SHELL
	KeyElements_BASIC_EVENT
	KeyElements_BLOB
	KeyElements_CAPABILITY
	KeyElements_CONCEPT_DESCRIPTION
	KeyElements_DATA_ELEMENT
	KeyElements_ENTITY
	KeyElements_EVENT
	KeyElements_FILE
	KeyElements_MULTI_LANGUAGE_PROPERTY
	KeyElements_OPERATION
	KeyElements_PROPERTY
	KeyElements_RANGE
	KeyElements_GLOBAL_REFERENCE
	KeyElements_REFERENCE_ELEMENT
	KeyElements_RELATIONSHIP_ELEMENT
	KeyElements_SUBMODEL
	KeyElements_SUBMODEL_ELEMENT
	KeyElements_SUBMODEL_ELEMENT_LIST
	KeyElements_SUBMODEL_ELEMENT_STRUCT
)

var KeyElements_name = map[KeyElements]string{
	0:  "FRAGMENT_REFERENCE",
	1:  "ACCESS_PERMISSION_RULE",
	2:  "ANNOTATED_RELATIONSHIP_ELEMENT",
	3:  "ASSET",
	4:  "ASSET_ADMINISTRATION_SHELL",
	5:  "BASIC_EVENT",
	6:  "BLOB",
	7:  "CAPABILITY",
	8:  "CONCEPT_DESCRIPTION",
	9:  "DATA_ELEMENT",
	10: "ENTITY",
	11: "EVENT",
	12: "FILE",
	13: "MULTI_LANGUAGE_PROPERTY",
	14: "OPERATION",
	15: "PROPERTY",
	16: "RANGE",
	17: "GLOBAL_REFERENCE",
	18: "REFERENCE_ELEMENT",
	19: "RELATIONSHIP_ELEMENT",
	20: "SUBMODEL",
	21: "SUBMODEL_ELEMENT",
	22: "SUBMODEL_ELEMENT_LIST",
	23: "SUBMODEL_ELEMENT_STRUCT",
}

var KeyElements_value = map[string]KeyElements{
	"FRAGMENT_REFERENCE":             0,
	"ACCESS_PERMISSION_RULE":         1,
	"ANNOTATED_RELATIONSHIP_ELEMENT": 2,
	"ASSET":                          3,
	"ASSET_ADMINISTRATION_SHELL":     4,
	"BASIC_EVENT":                    5,
	"BLOB":                           6,
	"CAPABILITY":                     7,
	"CONCEPT_DESCRIPTION":            8,
	"DATA_ELEMENT":                   9,
	"ENTITY":                         10,
	"EVENT":                          11,
	"FILE":                           12,
	"MULTI_LANGUAGE_PROPERTY":        13,
	"OPERATION":                      14,
	"PROPERTY":                       15,
	"RANGE":                          16,
	"GLOBAL_REFERENCE":               17,
	"REFERENCE_ELEMENT":              18,
	"RELATIONSHIP_ELEMENT":           19,
	"SUBMODEL":                       20,
	"SUBMODEL_ELEMENT":               21,
	"SUBMODEL_ELEMENT_LIST":          22,
	"SUBMODEL_ELEMENT_STRUCT":        23,
}

func (s KeyElements) String() string {
	return KeyElements_name[s]
}

func GetKeyElementsValue(n string) KeyElements {
	return KeyElements_value[n]
}

func GetKeyElementsName(v KeyElements) string {
	return KeyElements_name[v]
}

//TODO: transform_document NOT_IMPLEMENTED
type SubmodelElements int32

const (
	SubmodelElements_ANNOTATED_RELATIONSHIP_ELEMENT SubmodelElements = iota
	SubmodelElements_ASSET
	SubmodelElements_ASSET_ADMINISTRATION_SHELL
	SubmodelElements_BASIC_EVENT
	SubmodelElements_BLOB
	SubmodelElements_CAPABILITY
	SubmodelElements_CONCEPT_DESCRIPTION
	SubmodelElements_DATA_ELEMENT
	SubmodelElements_ENTITY
	SubmodelElements_EVENT
	SubmodelElements_FILE
	SubmodelElements_MULTI_LANGUAGE_PROPERTY
	SubmodelElements_OPERATION
	SubmodelElements_PROPERTY
	SubmodelElements_RANGE
	SubmodelElements_REFERENCE_ELEMENT
	SubmodelElements_RELATIONSHIP_ELEMENT
	SubmodelElements_SUBMODEL
	SubmodelElements_SUBMODEL_ELEMENT
	SubmodelElements_SUBMODEL_ELEMENT_LIST
	SubmodelElements_SUBMODEL_ELEMENT_STRUCT
)

var SubmodelElements_name = map[SubmodelElements]string{
	0:  "ANNOTATED_RELATIONSHIP_ELEMENT",
	1:  "ASSET",
	2:  "ASSET_ADMINISTRATION_SHELL",
	3:  "BASIC_EVENT",
	4:  "BLOB",
	5:  "CAPABILITY",
	6:  "CONCEPT_DESCRIPTION",
	7:  "DATA_ELEMENT",
	8:  "ENTITY",
	9:  "EVENT",
	10: "FILE",
	11: "MULTI_LANGUAGE_PROPERTY",
	12: "OPERATION",
	13: "PROPERTY",
	14: "RANGE",
	15: "REFERENCE_ELEMENT",
	16: "RELATIONSHIP_ELEMENT",
	17: "SUBMODEL",
	18: "SUBMODEL_ELEMENT",
	19: "SUBMODEL_ELEMENT_LIST",
	20: "SUBMODEL_ELEMENT_STRUCT",
}

var SubmodelElements_value = map[string]SubmodelElements{
	"ANNOTATED_RELATIONSHIP_ELEMENT": 0,
	"ASSET":                          1,
	"ASSET_ADMINISTRATION_SHELL":     2,
	"BASIC_EVENT":                    3,
	"BLOB":                           4,
	"CAPABILITY":                     5,
	"CONCEPT_DESCRIPTION":            6,
	"DATA_ELEMENT":                   7,
	"ENTITY":                         8,
	"EVENT":                          9,
	"FILE":                           10,
	"MULTI_LANGUAGE_PROPERTY":        11,
	"OPERATION":                      12,
	"PROPERTY":                       13,
	"RANGE":                          14,
	"REFERENCE_ELEMENT":              15,
	"RELATIONSHIP_ELEMENT":           16,
	"SUBMODEL":                       17,
	"SUBMODEL_ELEMENT":               18,
	"SUBMODEL_ELEMENT_LIST":          19,
	"SUBMODEL_ELEMENT_STRUCT":        20,
}

func (s SubmodelElements) String() string {
	return SubmodelElements_name[s]
}

func GetSubmodelElementsValue(n string) SubmodelElements {
	return SubmodelElements_value[n]
}

func GetSubmodelElementsName(v SubmodelElements) string {
	return SubmodelElements_name[v]
}

type BuildInListTypes int32

const (
	BuildInListTypes_ENTITIES BuildInListTypes = iota
	BuildInListTypes_ID_REFS
	BuildInListTypes_N_M_TOKENS
)

var BuildInListTypes_name = map[BuildInListTypes]string{
	0: "ENTITIES",
	1: "ID_REFS",
	2: "N_M_TOKENS",
}

var BuildInListTypes_value = map[string]BuildInListTypes{
	"ENTITIES":   0,
	"ID_REFS":    1,
	"N_M_TOKENS": 2,
}

func (s BuildInListTypes) String() string {
	return BuildInListTypes_name[s]
}

func GetBuildInListTypesValue(n string) BuildInListTypes {
	return BuildInListTypes_value[n]
}

func GetBuildInListTypesName(v BuildInListTypes) string {
	return BuildInListTypes_name[v]
}

type DecimalBuildInTypes int32

const (
	DecimalBuildInTypes_INTEGER DecimalBuildInTypes = iota
	DecimalBuildInTypes_LONG
	DecimalBuildInTypes_INT
	DecimalBuildInTypes_SHORT
	DecimalBuildInTypes_BYTE
	DecimalBuildInTypes_NON_NEGATIVE_INTEGER
	DecimalBuildInTypes_POSITIVE_INTEGER
	DecimalBuildInTypes_UNSIGNED_INTEGER
	DecimalBuildInTypes_UNSIGNED_LONG
	DecimalBuildInTypes_UNSIGNED_INT
	DecimalBuildInTypes_UNSIGNED_SHORT
	DecimalBuildInTypes_UNSIGNED_BYTE
	DecimalBuildInTypes_NON_POSITIVE_INTEGER
	DecimalBuildInTypes_NEGATIVE_INTEGER
)

var DecimalBuildInTypes_name = map[DecimalBuildInTypes]string{
	0:  "INTEGER",
	1:  "LONG",
	2:  "INT",
	3:  "SHORT",
	4:  "BYTE",
	5:  "NON_NEGATIVE_INTEGER",
	6:  "POSITIVE_INTEGER",
	7:  "UNSIGNED_INTEGER",
	8:  "UNSIGNED_LONG",
	9:  "UNSIGNED_INT",
	10: "UNSIGNED_SHORT",
	11: "UNSIGNED_BYTE",
	12: "NON_POSITIVE_INTEGER",
	13: "NEGATIVE_INTEGER",
}

var DecimalBuildInTypes_value = map[string]DecimalBuildInTypes{
	"INTEGER":              0,
	"LONG":                 1,
	"INT":                  2,
	"SHORT":                3,
	"BYTE":                 4,
	"NON_NEGATIVE_INTEGER": 5,
	"POSITIVE_INTEGER":     6,
	"UNSIGNED_INTEGER":     7,
	"UNSIGNED_LONG":        8,
	"UNSIGNED_INT":         9,
	"UNSIGNED_SHORT":       10,
	"UNSIGNED_BYTE":        11,
	"NON_POSITIVE_INTEGER": 12,
	"NEGATIVE_INTEGER":     13,
}

func (s DecimalBuildInTypes) String() string {
	return DecimalBuildInTypes_name[s]
}

func GetDecimalBuildInTypesValue(n string) DecimalBuildInTypes {
	return DecimalBuildInTypes_value[n]
}

func GetDecimalBuildInTypesName(v DecimalBuildInTypes) string {
	return DecimalBuildInTypes_name[v]
}

type DurationBuildInTypes int32

const (
	DurationBuildInTypes_DAY_TIME_DURATION DurationBuildInTypes = iota
	DurationBuildInTypes_YEAR_MONTH_DURATION
)

var DurationBuildInTypes_name = map[DurationBuildInTypes]string{
	0: "DAY_TIME_DURATION",
	1: "YEAR_MONTH_DURATION",
}

var DurationBuildInTypes_value = map[string]DurationBuildInTypes{
	"DAY_TIME_DURATION":   0,
	"YEAR_MONTH_DURATION": 1,
}

func (s DurationBuildInTypes) String() string {
	return DurationBuildInTypes_name[s]
}

func GetDurationBuildInTypesValue(n string) DurationBuildInTypes {
	return DurationBuildInTypes_value[n]
}

func GetDurationBuildInTypesName(v DurationBuildInTypes) string {
	return DurationBuildInTypes_name[v]
}

type PrimitiveTypes int32

const (
	PrimitiveTypes_ANY_URI PrimitiveTypes = iota
	PrimitiveTypes_BASE_64_BINARY
	PrimitiveTypes_BOOLEAN
	PrimitiveTypes_DATE
	PrimitiveTypes_DATE_TIME
	PrimitiveTypes_DECIMAL
	PrimitiveTypes_DOUBLE
	PrimitiveTypes_DURATION
	PrimitiveTypes_FLOAT
	PrimitiveTypes_G_DAY
	PrimitiveTypes_G_MONTH
	PrimitiveTypes_G_MONTH_DAY
	PrimitiveTypes_HEY_BINARY
	PrimitiveTypes_NOTATION
	PrimitiveTypes_Q_NAME
	PrimitiveTypes_STRING
	PrimitiveTypes_TIME
)

var PrimitiveTypes_name = map[PrimitiveTypes]string{
	0:  "ANY_URI",
	1:  "BASE_64_BINARY",
	2:  "BOOLEAN",
	3:  "DATE",
	4:  "DATE_TIME",
	5:  "DECIMAL",
	6:  "DOUBLE",
	7:  "DURATION",
	8:  "FLOAT",
	9:  "G_DAY",
	10: "G_MONTH",
	11: "G_MONTH_DAY",
	12: "HEY_BINARY",
	13: "NOTATION",
	14: "Q_NAME",
	15: "STRING",
	16: "TIME",
}

var PrimitiveTypes_value = map[string]PrimitiveTypes{
	"ANY_URI":        0,
	"BASE_64_BINARY": 1,
	"BOOLEAN":        2,
	"DATE":           3,
	"DATE_TIME":      4,
	"DECIMAL":        5,
	"DOUBLE":         6,
	"DURATION":       7,
	"FLOAT":          8,
	"G_DAY":          9,
	"G_MONTH":        10,
	"G_MONTH_DAY":    11,
	"HEY_BINARY":     12,
	"NOTATION":       13,
	"Q_NAME":         14,
	"STRING":         15,
	"TIME":           16,
}

func (s PrimitiveTypes) String() string {
	return PrimitiveTypes_name[s]
}

func GetPrimitiveTypesValue(n string) PrimitiveTypes {
	return PrimitiveTypes_value[n]
}

func GetPrimitiveTypesName(v PrimitiveTypes) string {
	return PrimitiveTypes_name[v]
}

type StringBuildInTypes int32

const (
	StringBuildInTypes_NORMALIZED_STRING StringBuildInTypes = iota
	StringBuildInTypes_TOKEN
	StringBuildInTypes_LANGUAGE
	StringBuildInTypes_N_C_NAME
	StringBuildInTypes_ENTITY
	StringBuildInTypes_ID
	StringBuildInTypes_IDREF
)

var StringBuildInTypes_name = map[StringBuildInTypes]string{
	0: "NORMALIZED_STRING",
	1: "TOKEN",
	2: "LANGUAGE",
	3: "N_C_NAME",
	4: "ENTITY",
	5: "ID",
	6: "IDREF",
}

var StringBuildInTypes_value = map[string]StringBuildInTypes{
	"NORMALIZED_STRING": 0,
	"TOKEN":             1,
	"LANGUAGE":          2,
	"N_C_NAME":          3,
	"ENTITY":            4,
	"ID":                5,
	"IDREF":             6,
}

func (s StringBuildInTypes) String() string {
	return StringBuildInTypes_name[s]
}

func GetStringBuildInTypesValue(n string) StringBuildInTypes {
	return StringBuildInTypes_value[n]
}

func GetStringBuildInTypesName(v StringBuildInTypes) string {
	return StringBuildInTypes_name[v]
}

//TODO: transform_document NOT_IMPLEMENTED
type DataTypeDef int32

const (
	DataTypeDef_ENTITIES DataTypeDef = iota
	DataTypeDef_ID_REFS
	DataTypeDef_N_M_TOKENS
	DataTypeDef_INTEGER
	DataTypeDef_LONG
	DataTypeDef_INT
	DataTypeDef_SHORT
	DataTypeDef_BYTE
	DataTypeDef_NON_NEGATIVE_INTEGER
	DataTypeDef_POSITIVE_INTEGER
	DataTypeDef_UNSIGNED_INTEGER
	DataTypeDef_UNSIGNED_LONG
	DataTypeDef_UNSIGNED_INT
	DataTypeDef_UNSIGNED_SHORT
	DataTypeDef_UNSIGNED_BYTE
	DataTypeDef_NON_POSITIVE_INTEGER
	DataTypeDef_NEGATIVE_INTEGER
	DataTypeDef_DAY_TIME_DURATION
	DataTypeDef_YEAR_MONTH_DURATION
	DataTypeDef_ANY_URI
	DataTypeDef_BASE_64_BINARY
	DataTypeDef_BOOLEAN
	DataTypeDef_DATE
	DataTypeDef_DATE_TIME
	DataTypeDef_DECIMAL
	DataTypeDef_DOUBLE
	DataTypeDef_DURATION
	DataTypeDef_FLOAT
	DataTypeDef_G_DAY
	DataTypeDef_G_MONTH
	DataTypeDef_G_MONTH_DAY
	DataTypeDef_HEY_BINARY
	DataTypeDef_NOTATION
	DataTypeDef_Q_NAME
	DataTypeDef_STRING
	DataTypeDef_TIME
	DataTypeDef_NORMALIZED_STRING
	DataTypeDef_TOKEN
	DataTypeDef_LANGUAGE
	DataTypeDef_N_C_NAME
	DataTypeDef_ENTITY
	DataTypeDef_ID
	DataTypeDef_IDREF
)

var DataTypeDef_name = map[DataTypeDef]string{
	0:  "ENTITIES",
	1:  "ID_REFS",
	2:  "N_M_TOKENS",
	3:  "INTEGER",
	4:  "LONG",
	5:  "INT",
	6:  "SHORT",
	7:  "BYTE",
	8:  "NON_NEGATIVE_INTEGER",
	9:  "POSITIVE_INTEGER",
	10: "UNSIGNED_INTEGER",
	11: "UNSIGNED_LONG",
	12: "UNSIGNED_INT",
	13: "UNSIGNED_SHORT",
	14: "UNSIGNED_BYTE",
	15: "NON_POSITIVE_INTEGER",
	16: "NEGATIVE_INTEGER",
	17: "DAY_TIME_DURATION",
	18: "YEAR_MONTH_DURATION",
	19: "ANY_URI",
	20: "BASE_64_BINARY",
	21: "BOOLEAN",
	22: "DATE",
	23: "DATE_TIME",
	24: "DECIMAL",
	25: "DOUBLE",
	26: "DURATION",
	27: "FLOAT",
	28: "G_DAY",
	29: "G_MONTH",
	30: "G_MONTH_DAY",
	31: "HEY_BINARY",
	32: "NOTATION",
	33: "Q_NAME",
	34: "STRING",
	35: "TIME",
	36: "NORMALIZED_STRING",
	37: "TOKEN",
	38: "LANGUAGE",
	39: "N_C_NAME",
	40: "ENTITY",
	41: "ID",
	42: "IDREF",
}

var DataTypeDef_value = map[string]DataTypeDef{
	"ENTITIES":             0,
	"ID_REFS":              1,
	"N_M_TOKENS":           2,
	"INTEGER":              3,
	"LONG":                 4,
	"INT":                  5,
	"SHORT":                6,
	"BYTE":                 7,
	"NON_NEGATIVE_INTEGER": 8,
	"POSITIVE_INTEGER":     9,
	"UNSIGNED_INTEGER":     10,
	"UNSIGNED_LONG":        11,
	"UNSIGNED_INT":         12,
	"UNSIGNED_SHORT":       13,
	"UNSIGNED_BYTE":        14,
	"NON_POSITIVE_INTEGER": 15,
	"NEGATIVE_INTEGER":     16,
	"DAY_TIME_DURATION":    17,
	"YEAR_MONTH_DURATION":  18,
	"ANY_URI":              19,
	"BASE_64_BINARY":       20,
	"BOOLEAN":              21,
	"DATE":                 22,
	"DATE_TIME":            23,
	"DECIMAL":              24,
	"DOUBLE":               25,
	"DURATION":             26,
	"FLOAT":                27,
	"G_DAY":                28,
	"G_MONTH":              29,
	"G_MONTH_DAY":          30,
	"HEY_BINARY":           31,
	"NOTATION":             32,
	"Q_NAME":               33,
	"STRING":               34,
	"TIME":                 35,
	"NORMALIZED_STRING":    36,
	"TOKEN":                37,
	"LANGUAGE":             38,
	"N_C_NAME":             39,
	"ENTITY":               40,
	"ID":                   41,
	"IDREF":                42,
}

func (s DataTypeDef) String() string {
	return DataTypeDef_name[s]
}

func GetDataTypeDefValue(n string) DataTypeDef {
	return DataTypeDef_value[n]
}

func GetDataTypeDefName(v DataTypeDef) string {
	return DataTypeDef_name[v]
}

type LangStringSet struct{}

type DataSpecificationContent struct {
}

type DataTypeIec61360 int32

const (
	DataTypeIec61360_DATE DataTypeIec61360 = iota
	DataTypeIec61360_STRING
	DataTypeIec61360_STRING_TRANSLATABLE
	DataTypeIec61360_INTEGER_MEASURE
	DataTypeIec61360_INTEGER_COUNT
	DataTypeIec61360_INTEGER_CURRENCY
	DataTypeIec61360_REAL_MEASURE
	DataTypeIec61360_REAL_COUNT
	DataTypeIec61360_REAL_CURRENCY
	DataTypeIec61360_BOOLEAN
	DataTypeIec61360_IRI
	DataTypeIec61360_IRDI
	DataTypeIec61360_RATIONAL
	DataTypeIec61360_RATIONAL_MEASURE
	DataTypeIec61360_TIME
	DataTypeIec61360_TIMESTAMP
	DataTypeIec61360_FILE
	DataTypeIec61360_HTML
	DataTypeIec61360_BLOB
)

var DataTypeIec61360_name = map[DataTypeIec61360]string{
	0:  "DATE",
	1:  "STRING",
	2:  "STRING_TRANSLATABLE",
	3:  "INTEGER_MEASURE",
	4:  "INTEGER_COUNT",
	5:  "INTEGER_CURRENCY",
	6:  "REAL_MEASURE",
	7:  "REAL_COUNT",
	8:  "REAL_CURRENCY",
	9:  "BOOLEAN",
	10: "IRI",
	11: "IRDI",
	12: "RATIONAL",
	13: "RATIONAL_MEASURE",
	14: "TIME",
	15: "TIMESTAMP",
	16: "FILE",
	17: "HTML",
	18: "BLOB",
}

var DataTypeIec61360_value = map[string]DataTypeIec61360{
	"DATE":                0,
	"STRING":              1,
	"STRING_TRANSLATABLE": 2,
	"INTEGER_MEASURE":     3,
	"INTEGER_COUNT":       4,
	"INTEGER_CURRENCY":    5,
	"REAL_MEASURE":        6,
	"REAL_COUNT":          7,
	"REAL_CURRENCY":       8,
	"BOOLEAN":             9,
	"IRI":                 10,
	"IRDI":                11,
	"RATIONAL":            12,
	"RATIONAL_MEASURE":    13,
	"TIME":                14,
	"TIMESTAMP":           15,
	"FILE":                16,
	"HTML":                17,
	"BLOB":                18,
}

func (s DataTypeIec61360) String() string {
	return DataTypeIec61360_name[s]
}

func GetDataTypeIec61360Value(n string) DataTypeIec61360 {
	return DataTypeIec61360_value[n]
}

func GetDataTypeIec61360Name(v DataTypeIec61360) string {
	return DataTypeIec61360_name[v]
}

type LevelType int32

const (
	LevelType_MIN LevelType = iota
	LevelType_MAX
	LevelType_NOM
	LevelType_TYPE
)

var LevelType_name = map[LevelType]string{
	0: "MIN",
	1: "MAX",
	2: "NOM",
	3: "TYPE",
}

var LevelType_value = map[string]LevelType{
	"MIN":  0,
	"MAX":  1,
	"NOM":  2,
	"TYPE": 3,
}

func (s LevelType) String() string {
	return LevelType_name[s]
}

func GetLevelTypeValue(n string) LevelType {
	return LevelType_value[n]
}

func GetLevelTypeName(v LevelType) string {
	return LevelType_name[v]
}

//TODO: transform_document NOT_IMPLEMENTED
type ValueReferencePair struct {
	Value   string
	ValueId *Reference
}

//TODO: transform_document NOT_IMPLEMENTED
type ValueList struct {
	ValueReferencePairs []ValueReferencePair
}

//TODO: transform_document NOT_IMPLEMENTED
type DataSpecificationIec61360 struct {
	PreferredName      *LangStringSet
	ShortName          *LangStringSet
	Unit               string
	UnitId             *Reference
	SourceOfDefinition string
	Symbol             string
	DataType           *DataTypeIec61360
	Definition         *LangStringSet
	ValueFormat        string
	ValueList          *ValueList
	Value              string
	ValueId            *Reference
	LevelType          *LevelType
}

//TODO: transform_document NOT_IMPLEMENTED
type DataSpecificationPhysicalUnit struct {
	UnitName                string
	UnitSymbol              string
	Definition              *LangStringSet
	SiNotation              string
	DinNotation             string
	EceName                 string
	EceCode                 string
	NistName                string
	SourceOfDefinition      string
	ConversionFactor        string
	RegistrationAuthorityId string
	Supplier                string
}

//TODO: transform_document NOT_IMPLEMENTED
type Environment struct {
	AssetAdministrationShells []AssetAdministrationShell
	Submodels                 []Submodel
	ConceptDescriptions       []ConceptDescription
}
