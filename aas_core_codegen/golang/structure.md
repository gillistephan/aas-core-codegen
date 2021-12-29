## Structure (aka Types)
Go does not know the concept of enums. The idiomatic Go way is to introduce a new type with `int32` as base type; 
E.g. `type Identifier int32`. Enum iterals are modeled as constants with the newly created type. For lookups during de-/encoding and stringification,  name and value maps are provided 
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

To offer a native like / compatible API (which can also be used as a drop in replacement) we implement the following interface:

```golang
// Marshaler is the interface implemented by all types of the meta-model
// that can marshal themselves into a valid JSON.
type Marshaler interface {
	marshalJSON(stream *json.Stream) error
}

// Unmarshaler is the interface implemented by all types of the meta-model
// that can unmarshal a JSON description of themselves.
type Unmarshaler interface {
	unmarshalJSON(iter *json.Iterator) error
}

// Encoder writes JSON values to an output stream.
type Encoder struct {
	stream *json.Stream
}

// Decoder reads and decodes JSON values from an input stream.
type Decoder struct {
	iter *json.Iterator
}

// NewDecoder returns a new Decoder that reads from r.
// Bs is the internal buffer size set in the NewDecoder.
func NewDecoder(bs int, r io.Reader) *Decoder {
	iter := json.Parse(json.ConfigDefault, r, bs)
	return &Decoder{iter}
}

// NewEcoder returns a new Encoder that writes to w.
// Bs is the internal buffer size set in the NewEncoder.
func NewEncoder(bs int, w io.Writer) *Encoder {
	stream := json.NewStream(json.ConfigDefault, w, bs)
	return &Encoder{stream}
}

// Decode reads the next encoded value from its input and
// writes it in the value pointed to by v. V must implement
// the Unmarshaler interface.
func (d *Decoder) Decode(v Unmarshaler) error {
	v.unmarshalJSON(d.iter)
	err := d.iter.Error
	if err == io.EOF {
		return nil
	}
	return d.iter.Error
}

// Encode writes the encoding of v to the input stream v
// V must implement the Marshaler interface.
func (e *Encoder) Encode(v Marshaler) error {
	v.marshalJSON(e.stream)
	e.stream.WriteRaw("\n")
	e.stream.Flush()
	return e.stream.Error
}
```

To use the custom De-/Encoder instead of importing `encoding/json`, the customer would import `aascore/json`. That might look like that:

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

In contrary to the standard lib (where the decoder takes an empty `interface{}`), all pointer objects passed to the Decode / Encode receiver function must implement the Marshaler / Unmarshaler interface. This provides safeguarding for objects passed, that do not implement this interface. So all generated types from the AAS-Meta-Model must implement this interfaces. The interface do not export the decode / encode methods, as this are some internals (?). Its also nice to see in the IDE only those methods, I can use as a developer.

So the process would roughly look like this (nearly analog to the C# API):

- Instantiate the Decoder with any Object that implements io.Reader interface (e.g. http.Request)
- Start reading from the stream by calling <myStruct>.decodeJSON(iter) with the iterator passed
- Every Type would then implement s.th. like `golang for f := iter.ReadObject(); f != ""; f = iter.ReadObject()`
- We would then check with a switch / if statement the current propertyName in the byteArray
- As we know the property types before, we could do some checking, if the propertyValue is correct like

```golang
 if next := iter.WhatIsNext(); next != json.StringValue {
	// do whatever with the error
 }
```

- if the type safety check is passed, we simply read the corresponding value
- for primitives

```golang
 someObject.someProperty = iter.ReadString()
```

- for non-primities, we simply call the <someStruct>.<someProperty>.unmarshalJSON(iter) receiver function

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
