## Structure (aka Types)

Go does not know the concept of enums. The idiomatic Go way is to introduce a new type with `int32` as base type;
E.g. `type Identifier int32`. Enum iterals are modeled as constants with the newly created type. For lookups during de-/encoding and stringification, name and value maps are provided

```golang
var Identifier_name = map[Identifier]string {
  0: "IRDI",
  1: "IRI",
}
```

Since different enums can have the same literal value (e.g. AssetKind and ModelingKind) the constants are prefixed with the enum name `ModelingKind_TEMPLATE` and `AssetKind_TEMPLATE`. Although Go will introduce Generics in Go 1.18, I think they won't provide any big value for the representation for the meta-model. The closest to interfaces or abstract classes what we can get in Go is type embedding.

```golang
 type myStruct {}
 type mySecondStruct{
     myStruct
}
```

The object is just passed as a nameless parameter within the other object so that all exported parameters and methods are accessible. The types can be generated with embedded types. As I am not a big fan of it, I am just rendering the interfaces as type <Name> struct with all its properties.

## JSON De-/Encoding

It would be nice, if the API (Package) in Go for De-/Encoding would feel like using the API from the standard lib, provided by Go. The De-/Encode of objects in Go looks like the following:

```golang
import encoding/json

func main() {
	dec := json.NewDecoder(myReader)
	var myStruct MyStruct
	dec.Decode(&myStruct)
}
```

Using the standard lib, we can create a decoder from a provided `io.Reader`. The decoder lazily reads from the io.Reader until EOF. Internally, reflection is used to determine the appropriate type by providing tags on the object property `json:"myProp, omitEmty"`. This obviously has advantages when working with dynamic APIs, but makes processing also pretty slow (standard parser is anyway slow). In case of the AAS-Meta-Model we exactly know the objects, their properties and their types. So we do not need reflection, as we can write out a "hand-written-deserializer/serializer". Since we might deal with large JSON objects, a streaming-based approach is needed, where we can pull from the stream so that parsing can be done in chunks (bytes are not just loaded in one big array).

For this purpose, we could use the _[jsoniter package](https://jsoniter.com/)_ . Its widely used (also by big Go projects) and offers an API, where we can directly operate on the Stream. In general, the documentation of the package is not that good, so that we have to dig into the internals to take out the parts we need.

To offer an API wich can be used as a drop in replacement for the standard API we implement the following interface:

```golang
// AasCoreMarshaler is the interface implemented by all types of the meta-model
// that can marshal themselves into a valid JSON.
type AasCoreMarshaler interface {
	marshalJSON(stream *json.Stream)
}
// AasCoreUnmarshaler is the interface implemented by all types of the meta-model
// that can unmarshal a JSON description of themselves.
type AasCoreUnmarshaler interface {
	unmarshalJSON(iter *json.Iterator)
}
// Encoder writes JSON values to an output stream.
type Encoder struct {
	stream *json.Stream
}
// Decoder reads and decodes JSON values from an input stream.
type Decoder struct {
	iter *json.Iterator
}

// isNonNilPointer checks, if a given value v is a pointer or not nil
func isNonNilPointer(v interface{}) bool {
	rv := reflect.ValueOf(v)
	if rv.Kind() != reflect.Ptr || rv.IsNil() {
		return false
	}
	return true
}
// Unmarshal parses the JSON-encoded data and stores
// the result in the value pointed by v. If v is nil or not a pointer
// Unmarshal returns an error. If v implements the AasCoreUnmarshaler interface
// of the AAS-Meta-Model, data will be decoded according to the specifications of
// the meta-model. If not, Unmarshal will decode the data in complience with
// the standard library. It can be used as a drop-in replacement
// of the encoding/json standard library.
func Unmarshal(data []byte, v interface{}) error {
	if isNonNilPointer(v) {
		return fmt.Errorf(NonNilPointerError)
	}

	if u, ok := v.(AasCoreUnmarshaler); !ok {
		return json.Unmarshal(data, data)
	} else {
		iter := json.ParseBytes(json.ConfigDefault, data)
		dec := &Decoder{iter}
		err := dec.Decode(u)
		return err
	}
}
// Marshal traverses the value v recursively. If v implements the AasCoreMarshaler
// interface and is not a nil pointer, Marshal calls the marshalJSON method to encode
// v according to the specifications of the AAS-Meta-Model. If v does not implement the
// AasCoreMarshaler interface, Marshal will decode the data in complience with standard
// library. It can be used as a drop-in replacement of the encoding/json standard library.
func Marshal(v interface{}) ([]byte, error) {
	if m, ok := v.(AasCoreMarshaler); !ok {
		return json.Marshal(v)
	} else {
		stream := json.ConfigDefault.BorrowStream(nil)
		enc := &Encoder{stream}
		err := enc.Encode(m)
		if err != nil {
			return nil, err
		}
		bytes := enc.stream.Buffer()
		return bytes, nil
	}
}

// NewDecoder returns a new Decoder that reads from r.
// Bs is the internal buffer size set in the NewDecoder.
func NewDecoder(bs int, r io.Reader) *Decoder {
	iter := json.Parse(json.ConfigCompatibleWithStandardLibrary, r, bs)
	return &Decoder{iter}
}

// NewEcoder returns a new Encoder that writes to w.
// Bs is the internal buffer size set in the NewEncoder.
func NewEncoder(bs int, w io.Writer) *Encoder {
	stream := json.NewStream(json.ConfigCompatibleWithStandardLibrary, w, bs)
	return &Encoder{stream}
}

// Decode reads the next encoded value from its input and
// writes it in the value pointed to by v. If v implements
// the AasCoreUnmarshaler interface, v will be decoded according
// to the specifications of the AAS-Meta-Model. If not,
// Decode will decode the data in complience with the standard library.
// It can be used as a drop-in replacement of the encoding/json standard library.
func (d *Decoder) Decode(v interface{}) error {
	if isNonNilPointer(v) {
		return fmt.Errorf(NonNilPointerError)
	}
	if u, ok := v.(AasCoreUnmarshaler); !ok {
		d.iter.ReadVal(v)
	} else {
		u.unmarshalJSON(d.iter)
	}
	err := d.iter.Error
	if err == io.EOF {
		return nil
	}
	return d.iter.Error
}
// Encode writes the encoding of v to the input stream v.
// If v implements the AasCoreMarshaler interface and v is
// not a nil pointer, Encode calls the marshalJSON method recursively
// and encodes the data according to the specifications of the AAS-Meta-Model.
// If v does not implement AasCoreMarshaler interface, Encode will encode the
// data in complience with the standard library. It can be used as a drop-in
// replacement of the encoding/json standard library.
func (e *Encoder) Encode(v interface{}) error {
	if m, ok := v.(AasCoreMarshaler); !ok {
		e.stream.WriteVal(v)
	} else {
		m.marshalJSON(e.stream)
	}
	e.stream.WriteRaw("\n")
	e.stream.Flush()
	return e.stream.Error
}

```

To use the custom De-/Encoder instead of importing `encoding/json`, the user of the API would import `aascore/json`. That might look like that:

```golang
func main() {
	var shell AssetAdministrationShell
	dec := json.NewDecoder(r)
	dec.Decode(&shell)

    var assetInformation AssetInformation
	enc := json.NewEncoder(w)
	enc.Encode(&assetInformation)
}
```

Types that must be de/encoded according to the specifications of the AAS-Meta-Model must implement the AasCoreMarshaler / AasCoreUnmarshaler interface. This provides safeguarding for objects passed, that do not implement this interface. The interface do not export the decode / encode methods, as this are some internals. If new types are provided, they have to be included in the Meta-Model and generated by aas-core-codgen. Its also nice to see in the IDE only those methods, I can use as a developer.

The process of de/encoding would roughly look like this (nearly analog to the C# API):

- Instantiate the Decoder with any bbject that implements io.Reader interface (e.g. http.Request)
- Check if the object implements AasCoreUnmarshaler interface
- If so, start reading from the stream by calling <myStruct>.decodeJSON(iter) with the iterator passed
- every type would then implement s.th. like `golang for f := iter.ReadObject(); f != ""; f = iter.ReadObject()`
- We would then check with a switch / if statement the current propertyName in the byteArray
- As we know the property types before, we could do some checking, if the propertyValue is correct like

```golang
 if next := iter.WhatIsNext(); next != json.StringValue {
	// do whatever with the error
 }
```

- if the type safety check is passed, we simply read the corresponding value
- for primitives:

```golang
 someObject.someProperty = iter.ReadString()
```

- for non-primities, we call the <someStruct>.<someProperty>.unmarshalJSON(iter) receiver function

```golang

myProp := &someObject{}
myProp.unmarshalJSON(iter)
someOtherObject.myProp = myProp
```

As the Meta-Model comes with some required and some optional properties, we have to make sure to throw an error, if a required property is not present. This looks a little bit tricky to me, as we can not just instantiate our properties with null or empty. Because when instantiating a property in Go without any initial value, it gets assigned the `zero` value. E.g. in case of a `slice` that is nil (this might be easy to check). But for a string it is the empty String ("") or a bool it is false.

An easy workaround for now(?, or later :D) might be:

- Generate a map with all the required properties and init them with false

```golang
requiredProps := map[string]bool {
 "myProp": false
}
```

- when going through the objects in the stream, set the value to true, if the property is present and has been visited

```golang
myProp := &someObject{}
myProp.unmarshalJSON(iter)
someOtherObject.myProp = myProp
requiredProps["myProp"] = true
```

- at the end of the reading of that objects loop through the map and check, if all props are true

# Example, using aascore/json as a drop in replacement

Since the library is compatible with the standard library we can easily use it as a drop in replacement or in conjunction with some other tooling, e.g. GRPC-Gateway. This might be a common use-case where Microservices using the AAS-Meta-Model are implemented in GRPC. To make it compatible with the REST-API-Spec, you might want to use GRPC-Gateway as a proxy. GRPC-Gateway offers the possibility to inject Custom-(Un)Marshalers for different Content-Types:

```golang
	gwMuxOpts := runtime.WithMarshalerOption(runtime.MIMEWildcard, new(json.JSONMarshaler))
```

In order to inject a custom Marshaler, the Marshaler has to fulfill the runtime.Marshaler interface:

```golang
// Marshaler defines a conversion between byte sequence and gRPC payloads / fields.
type Marshaler interface {
	// Marshal marshals "v" into byte sequence.
	Marshal(v interface{}) ([]byte, error)
	// Unmarshal unmarshals "data" into "v".
	// "v" must be a pointer value.
	Unmarshal(data []byte, v interface{}) error
	// NewDecoder returns a Decoder which reads byte sequence from "r".
	NewDecoder(r io.Reader) Decoder
	// NewEncoder returns an Encoder which writes bytes sequence into "w".
	NewEncoder(w io.Writer) Encoder
	// ContentType returns the Content-Type which this marshaler is responsible for.
	ContentType() string
}
```

The implementation using aascore/json would look like:

```golang
import (
	"io"

	"github.com/grpc-ecosystem/grpc-gateway/runtime"

	json "aascore/json"
)

type JSONMarshaler struct{}

func (m *JSONMarshaler) ContentType() string {
	return "application/json"
}

func (m *JSONMarshaler) Marshal(v interface{}) ([]byte, error) {
	return json.Marshal(v)
}

func (m *JSONMarshaler) Unmarshal(data []byte, v interface{}) error {
	return json.Unmarshal(data, v)
}

func (m *JSONMarshaler) NewDecoder(r io.Reader) runtime.Decoder {
	return json.NewDecoder(r)
}

func (m *JSONMarshaler) NewEncoder(w io.Writer) runtime.Encoder {
	return json.NewEncoder(w)
}
```
