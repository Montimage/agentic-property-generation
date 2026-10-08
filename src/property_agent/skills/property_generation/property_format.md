# MMT Event-Based Property Format

This document describes the XML representation of MMT event-based monitoring properties.

The examples in this document are intentionally generic and illustrate only the property language and structure.

Complete validated monitoring properties are maintained separately in the property knowledge base and are not part of this format description.

---

## 1. General XML Structure

An MMT monitoring rule is defined using a `<property>` element.

One or more properties are contained inside a `<beginning>` element.

The general structure is:

```xml
<beginning>

    <property ...>

        ...

    </property>

</beginning>
```

The `<beginning>` element may also contain an optional `<embedded_functions>` section:

```xml
<beginning>

    <embedded_functions><![CDATA[

        ...

    ]]></embedded_functions>

    <property ...>

        ...

    </property>

</beginning>
```

---

## 2. Property Tree Model

A property is represented as a **general ordered tree**.

The possible nodes of the property tree are:

- `<property>` — required;
- `<operator>` — optional;
- `<event>` — required.

The `<property>` node is always the root node.

The `<event>` nodes are always leaf nodes.

When a property represents a relationship between a context and a trigger:

- the left branch represents the **context**;
- the right branch represents the **trigger**.

The trigger is checked only when the context is valid.

The property is considered valid when the trigger is found valid.

---

## 3. `<beginning>` Element

The `<beginning>` element is the container for property definitions.

It can contain:

- one or more `<property>` elements;
- an optional `<embedded_functions>` element.

Generic structure:

```xml
<beginning>

    <property ...>

        ...

    </property>

</beginning>
```

Structure including embedded functions:

```xml
<beginning>

    <embedded_functions><![CDATA[

        ...

    ]]></embedded_functions>

    <property ...>

        ...

    </property>

</beginning>
```

The `<embedded_functions>` element must be placed directly inside `<beginning>`, outside the `<property>` element.

---

## 4. `<property>` Element

A `<property>` defines a monitoring rule.

The documented property types are:

- `SECURITY`
- `ATTACK`
- `EVASION`
- `TEST`

A `<property>` element may contain at most two direct child
expressions/events.

Do not add a third direct `<event>` in order to represent an
additional condition.

When more complex stateful or aggregate behavior is required,
use only a mechanism explicitly supported by the MMT property
language. Do not invent additional direct property children.

A `<property>` element can contain the following attributes.

### 4.1 `property_id`

Required.

Uniquely identifies the property.

The identifier is supplied by the monitoring task and must not be invented or changed by the generator.

Generic example:

```xml
property_id="1000"
```

The numerical value above is illustrative only.

---

### 4.2 `description`

Required.

Provides a textual description of the monitoring property.

Generic example:

```xml
description="Description of the monitoring condition"
```

The description should reflect the actual monitoring objective represented by the executable property.

---

### 4.3 `type_property`

Required.

Defines the type of monitoring property.

Supported values are:

```text
SECURITY
ATTACK
EVASION
TEST
```

Example:

```xml
type_property="ATTACK"
```

---

### 4.4 `value`

Optional.

The value:

```text
THEN
```

defines a temporal or logical relationship between a context and a trigger.

Example:

```xml
value="THEN"
```

If this attribute is absent, the documented default value for a property is:

```text
COMPUTE
```

---

### 4.5 `delay_min`

Optional.

Defines a lower temporal constraint on when the trigger may occur relative to the context.

Documented forms and existing valid properties indicate values such as:

```text
-1
0
0+
10
```

The documented interpretation includes:

- a negative delay, such as `-1`, indicates a relation before the context;
- `0` indicates simultaneous timing;
- positive values constrain events occurring after the context;
- existing valid properties also use forms such as `0+`.

Example:

```xml
delay_min="0"
```

---

### 4.6 `delay_max`

Optional.

Defines an upper bound on the temporal relationship between the context and the trigger.

Example:

```xml
delay_max="10"
```

If absent, the documented default value is:

```text
0
```

---

### 4.7 `delay_units`

Defines the unit associated with delay values.

Existing valid properties demonstrate units such as:

```xml
delay_units="s"
```

and:

```xml
delay_units="ms"
```

If absent, the documented default value is:

```text
0
```

The available property-format information does not provide a complete enumeration of all supported delay units.

The generator must therefore use only units supported by available verified knowledge or task requirements and must not invent new units.

---

### 4.8 `if_satisfied`

Optional.

Specifies an action to execute when the property condition is satisfied.

The action is performed through a reactive function.

Example structure:

```xml
if_satisfied="em_example_action"
```

The referenced function must exist in the corresponding embedded-function context when a custom reactive function is used.

---

## 5. Property Default Values

According to the available property description, if some attributes are absent, default values are applied.

For `<property>` and `<operator>`, documented defaults include:

```text
value        = COMPUTE
delay_units  = s
delay_max    = 0
```

When the effective value is `COMPUTE`, the construct represents direct computation of an event condition.

The documented format indicates that a `COMPUTE` property or operator must contain exactly one `<event>`.

In that case, the delays are:

```text
delay_min = 0
delay_max = 0
```

---

## 6. `<event>` Element

An `<event>` represents an observable condition evaluated by the property.

An event is a leaf node and does not contain child XML elements.

An event contains the following attributes.

### 6.1 `value`

The supported event value is:

```xml
value="COMPUTE"
```

This indicates that the event is evaluated using its boolean expression.

---

### 6.2 `event_id`

Required.

Assigns an identifier to the event.

Event identifiers are unique within the complete property.

They allow data captured when one event occurred to be referenced by another event in the same property.

Example:

```xml
event_id="1"
```

---

### 6.3 `description`

Required.

Provides a textual description of the observable event.

Generic example:

```xml
description="First monitored event"
```

The description should remain consistent with the executable `boolean_expression`.

---

### 6.4 `boolean_expression`

Required.

Defines the executable condition that determines when the event is detected.

Schematic example:

```xml
boolean_expression="protocol.attribute == value"
```

A real generated property must replace schematic placeholders with protocol attributes and values supported by the task and available MMT knowledge.

Boolean expressions can use:

- protocol attributes;
- packet or metadata attributes;
- values captured by previous events;
- supported comparison and logical operators;
- embedded functions.

---

## 7. Protocol Attribute References

Packet or message attributes are represented using:

```text
<protocol_name>.<field_name>
```

For example:

```text
ngap.procedure_code
```

Other possible namespaces include protocol or metadata namespaces exposed by the monitored MMT environment.

Examples of valid attribute-reference forms include:

```text
ngap.procedure_code
ngap.amf_ue_id
ngap.ran_ue_id
sctp.dest_port
ip.src
ip.dst
meta.utime
```

These examples demonstrate syntax and known available attributes only. They do not prescribe when those attributes should be used.

Only protocol attributes actually available in the MMT environment may be used.

The generator must rely on supplied protocol knowledge rather than inventing protocol fields.

---

## 8. Event Attribute References

A property can reference a value captured when another event occurred.

The syntax is:

```text
<protocol_name>.<field_name>.<event_id>
```

For example:

```text
ngap.amf_ue_id.1
```

This represents the value of `ngap.amf_ue_id` captured when event `1` occurred.

Another syntactic example is:

```text
sctp.dest_port.2
```

This mechanism allows different events in the same property to be correlated.

Generic comparisons may therefore have forms such as:

```text
protocol.attribute == protocol.attribute.1
```

or:

```text
protocol.attribute != protocol.attribute.1
```

Event identifiers are scoped to the complete property.

Therefore, an event may reference a previous event even when the two events are contained in different sibling `<operator>` elements.

---

## 9. Boolean Expressions

The `boolean_expression` attribute contains the logical condition evaluated by an event.

A boolean expression may contain a single comparison or combine multiple conditions using logical operators.

A simple condition may be written as a parenthesized comparison:

```xml
boolean_expression="(protocol.attribute == value)"
```

The tokens `protocol`, `attribute`, and `value` are placeholders and must not be copied literally into generated properties.

When multiple conditions are combined using logical operators, the complete compound expression must also be enclosed within an additional outer pair of parentheses.

For example, the following structure is valid:

```xml
boolean_expression="((protocol.attribute == value1) &amp;&amp; (other_protocol.attribute == value2))"
```

The following form must not be generated:
```xml
boolean_expression="(protocol.attribute == value1) &amp;&amp; (other_protocol.attribute == value2)"
```

Although the individual comparisons are parenthesized, the complete logical expression is not grouped. This form was rejected by the real MMT `compile_rule` parser.

Compound expressions should therefore follow the general structure: `((condition_1) LOGICAL_OPERATOR (condition_2))`

For expressions containing additional conditions, explicit grouping must be preserved throughout the complete expression.

Because `boolean_expression` is stored inside an XML attribute, characters with special meaning in XML must be escaped where necessary.

Logical AND is represented in the XML source as: `&amp;&amp;`
which is interpreted by MMT as: `&&`

Existing validated properties also demonstrate logical OR: `||`

and comparison operators such as:
```text
==
!=
>=
```

Cross-event references may be used inside boolean expressions when the referenced event exists within the same property. For example:
```xml
boolean_expression="((protocol.attribute == value) &amp;&amp; (protocol.identifier == protocol.identifier.1))"
```

Here, `.1` refers to the value of the corresponding attribute observed in event `1`.

The complete set of supported boolean operators and expression forms is not specified in the available property-format documentation. The generator must therefore use only expression structures supported by the available validated examples and confirmed MMT compiler behavior, and must not invent unsupported boolean-expression syntax.

---

## 10. Context and Trigger Structure

A property using `value="THEN"` may define a context event followed by a trigger event.

Generic structure:

```xml
<beginning>

    <property
        value="THEN"
        delay_units="s"
        delay_min="0"
        delay_max="1"
        property_id="1000"
        type_property="ATTACK"
        description="Generic context-trigger monitoring property">

        <event
            value="COMPUTE"
            event_id="1"
            description="Context event"
            boolean_expression="protocol.attribute == value1"/>

        <event
            value="COMPUTE"
            event_id="2"
            description="Trigger event"
            boolean_expression="other_protocol.attribute == value2"/>

    </property>

</beginning>
```

This example is schematic.

The placeholder protocol names, attributes, and values must be replaced using task-specific verified knowledge.

In this form:

- event `1` represents the context;
- event `2` represents the trigger;
- the trigger is evaluated relative to the context;
- delay attributes define the allowed temporal relationship.

---

## 11. `<operator>` Elements

An `<operator>` is an optional internal node of the MMT property tree.

Verified MMT properties demonstrate that an `<operator>` may appear directly inside a `<property>` element and may contain multiple `<event>` elements.

An operator may contain the following attributes:

- `value`
- `delay_units`
- `delay_min`
- `delay_max`

Generic operator structure:

```xml
<operator
    value="THEN"
    delay_units="ms"
    delay_min="0+"
    delay_max="10">

    <event
        value="COMPUTE"
        event_id="1"
        description="First event"
        boolean_expression="protocol.attribute == value1"/>

    <event
        value="COMPUTE"
        event_id="2"
        description="Second event"
        boolean_expression="protocol.attribute == protocol.attribute.1"/>

</operator>
```

The example above illustrates syntax only.

Up to two direct child elements may occur inside the same `<property>`. Those children may include `<operator>` elements when the corresponding operator structure is supported.

Generic structure:

```xml
<property
    value="THEN"
    property_id="1000"
    type_property="ATTACK"
    description="Generic multi-stage monitoring property">

    <operator
        value="THEN"
        delay_units="ms"
        delay_min="0+"
        delay_max="10">

        <event
            value="COMPUTE"
            event_id="1"
            description="First event"
            boolean_expression="protocol.attribute == value1"/>

        <event
            value="COMPUTE"
            event_id="2"
            description="Second event"
            boolean_expression="protocol.attribute == value2"/>

    </operator>

    <operator
        value="THEN"
        delay_units="ms"
        delay_min="0+"
        delay_max="10">

        <event
            value="COMPUTE"
            event_id="3"
            description="Third event"
            boolean_expression="protocol.attribute == protocol.attribute.1"/>

        <event
            value="COMPUTE"
            event_id="4"
            description="Fourth event"
            boolean_expression="protocol.attribute != protocol.attribute.2"/>

    </operator>

</property>
```

Event identifiers belong to the property as a whole rather than only to the operator in which they appear.

Therefore, an event contained in one operator may reference values captured by an event contained in a previous operator.

The currently available verified examples do not establish whether operators may contain nested `<operator>` elements.

Nested operators must therefore not be generated unless additional verified MMT documentation or examples confirm that structure.

### 11.1 Supported `<operator>` Values

The supported values for the XML `<operator>` element are:

```text
THEN
COMPUTE
```

These values describe relationships in the MMT property tree.

They are distinct from logical operators used inside an event
`boolean_expression`.

Logical conjunction and disjunction are expressed inside
`boolean_expression` using the supported boolean syntax.

For example: `boolean_expression="((condition_1) &amp;&amp; (condition_2))"` uses logical AND.

The following structures must not be generated:
```xml
<operator value="AND">
<operator value="OR">
```

`AND` and `OR` are not documented XML `<operator>` values.

If multiple conditions describe the same event, combine those conditions
inside the event's `boolean_expression` rather than creating an XML
operator for boolean conjunction or disjunction.


---

## 12. Embedded Functions

Custom C logic can be declared using the `<embedded_functions>` element.

The `<embedded_functions>` element is placed directly inside `<beginning>` and outside `<property>`.

Generic structure:

```xml
<beginning>

    <embedded_functions><![CDATA[

static inline bool em_example_function(double value) {
    /*
     * Example only.
     * The supplied protocol knowledge defines the corresponding security_c_type as double.
     */
    return value > 0;
}

    ]]></embedded_functions>

    <property ...>

        ...

    </property>

</beginning>
```

Embedded functions provide an extension mechanism for monitoring logic
whose required computation cannot be adequately expressed using the
ordinary MMT property constructs and classical operators available in
boolean expressions.

MMT allows either existing embedded functions to be used or new custom
functions to be implemented in C.

Custom embedded functions may therefore implement task-specific
computation or state required by a monitoring scenario. The MMT property
format defines how such functions are integrated into the rule; the
specific C algorithm remains dependent on the monitoring requirement.

Embedded functions should not be introduced when ordinary MMT property
constructs are sufficient to represent the complete monitoring requirement.

New custom embedded functions should normally be declared using `static inline`, following the MMT-Security documentation and examples.

Example:
```c
static inline bool em_example_function(...) {
    ...
}
```

### 12.1 Embedded-Function Parameter Types

Protocol attribute knowledge may provide a `security_c_type` for an
attribute.

When a protocol attribute is passed to an embedded function and its
`security_c_type` is known, the corresponding C function parameter must use
a compatible type.

For example, if the supplied protocol knowledge contains:

```text
qualified_name: ngap.amf_ue_id
security_c_type: double
```

then a compatible embedded-function signature is:
```c
static inline bool em_example_function(double amf_ue_id) {
    ...
}
```

A known `security_c_type` must not be replaced with another guessed or generic C type.

If `security_c_type` is null or unavailable, the embedded-function parameter type must not be invented.

A null `security_c_type` does not mean that the protocol attribute is unavailable. It means only that its C representation for embedded-function parameters is not established by the supplied knowledge.

---

## 13. Calling Embedded Functions

An embedded function can be called inside the `boolean_expression` of an `<event>`.

The syntax is:

```text
#<name_of_function>(<list_of_parameters>)
```

Generic example:

```text
#em_example_function(meta.utime)
```

New custom embedded functions should use the prefix:

```text
em_
```

The invoked custom function must be defined in the `<embedded_functions>` section.

Protocol, packet, or metadata attributes available to the property may be
passed as parameters to an embedded function.

For example:

```text
#em_example_function(meta.utime)
```

The type and interpretation of each argument must be compatible with the corresponding C function parameter.

When the supplied protocol knowledge provides `security_c_type` for an attribute, that value must be used to determine the compatible C parameter representation.

For example, if:

```text
ngap.amf_ue_id
security_c_type: double
```

is supplied, then: `#em_example_function(ngap.amf_ue_id)` must correspond to a compatible function signature such as:

```c
static inline bool em_example_function(double amf_ue_id) {
    ...
}
```

If the required `security_c_type` is not available, the C parameter type must not be guessed


Embedded functions used in boolean expressions are evaluated when the
corresponding boolean expression is verified by MMT-Security.

The return value of the function may participate in the event condition,
for example:

```text
(#em_example_function(meta.utime) == true)
```

---

## 14. Embedded Function Lifecycle Functions

The `<embedded_functions>` section may contain:

```c
void on_load(){

    ...

}
```

`on_load()` is called when the rules contained in the XML file are loaded into MMT-Security.

The section may also contain:

```c
void on_unload(){
    ...
}
```

`on_unload()` is called when exiting MMT-Security.

Lifecycle functions should only be introduced when required by the custom embedded logic.

The documented MMT execution model also permits initialization performed once in `on_load()` to be reused by embedded functions during rule evaluation.

Persistent or reusable C state may therefore be used when required by the task-specific monitoring algorithm, subject to the normal constraints of the available C execution environment.

The property format does not prescribe the state representation or algorithm. These are implementation decisions of the generated embedded function and must remain consistent with the monitoring requirement.

---

## 15. Libraries Available to Embedded Functions

The existing property description states that the following libraries are pre-included:

```c
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "mmt_lib.h"
#include "pre_embedded_functions.h"
```

Standard C functions provided by these libraries may also be called
directly from embedded logic.

Additional headers may be included inside `<embedded_functions>` when
required by the generated implementation, provided that the corresponding
library is available in the target MMT-Security execution environment.

An embedded implementation may use available embedded functionality or define new custom functions.

If an additional C library is required by a custom function, that library must be available in the target execution environment.

The generator must not assume that arbitrary external libraries are available.

---

## 16. Reactive Functions

Reactive functions allow an action to be performed when a property is satisfied.

A custom reactive function is associated with the property using:

```text
if_satisfied
```

To define and use a custom reactive function:

1. implement the C function inside the `<embedded_functions>` section;
2. use the `em_` prefix for a newly defined function;
3. associate the function with the property through `if_satisfied`.

The callback format documented by the available property description is:

```c
typedef void (*mmt_rule_satisfied_callback)(
    const rule_t *rule,
    int verdict,
    uint64_t timestamp,
    uint64_t counter,
    const mmt_array_t * const trace
);
```

The parameters represent:

- `rule`: the rule being validated;
- `verdict`: the resulting verdict;
- `timestamp`: the moment at which the rule is validated;
- `counter`: the message-order position at which the rule is validated;
- `trace`: the history of messages associated with validation of the rule.

---

## 17. Generic Embedded-Function Property Structure

The following schematic example illustrates how an embedded function can be connected to an event without encoding a complete validated monitoring scenario.

```xml
<beginning>

    <embedded_functions><![CDATA[

static inline bool em_check_condition(double value) {

    /*
     * Task-specific logic must be implemented here.
     */

    return true;
}

    ]]></embedded_functions>

    <property
        value="COMPUTE"
        delay_min="0"
        delay_max="0"
        property_id="1000"
        type_property="SECURITY"
        description="Generic property using an embedded function">

        <event
            value="COMPUTE"
            event_id="1"
            description="Evaluate a custom monitoring condition"
            boolean_expression="(#em_check_condition(meta.utime) == true)"/>

    </property>

</beginning>
```
This example does not establish `double` as a universal embedded-function parameter type. The type must be obtained from the task-specific protocol knowledge when `security_c_type` is available.

This example demonstrates only:

- placement of `<embedded_functions>`;
- definition of a custom `em_` function;
- invocation of the custom function from an event;
- relationship between the embedded code and the XML property.

The custom function body shown above is deliberately non-domain-specific and must not be interpreted as a complete monitoring implementation.

---

## 18. Separation Between Format Knowledge and Verified Examples

This document defines the MMT property language available to the generation agent.

It intentionally does not contain complete validated attack, security, evasion, or test properties.

Complete verified properties are stored separately in the property knowledge base.

This separation is important because:

- property-format knowledge describes how valid XML can be constructed;
- protocol knowledge describes which observable attributes are available;
- verified examples represent concrete monitoring solutions;
- retrieved examples may later be supplied explicitly when an example-retrieval mechanism is enabled.

The generator must not assume access to verified example properties unless they are explicitly supplied by the generation workflow.

---

## 19. Important Generation Principles

The property format describes how an MMT property can be represented.

It does not imply that arbitrary protocol fields are available.

Protocol attributes used in a generated property must be verified against protocol knowledge available to the generation system.

The generator must therefore:

- use only protocol attributes present in the supplied task-specific knowledge;
- use exactly the `property_id` supplied by the monitoring task;
- preserve numerical thresholds, timing constraints, ordering requirements, and other explicit task requirements;
- not invent unsupported property types, tags, attributes, delay units, protocol fields, functions, or operators;
- prefer ordinary documented MMT property constructs when they are
  sufficient to represent the complete monitoring requirement;
- when additional computation or state is necessary, use the documented
  embedded-function mechanism and synthesize task-specific C logic as
  required by the canonical monitoring task;
- do not substitute semantically unrelated protocol attributes for required
  computation or state merely because their names suggest counting,
  timing, aggregation, or similar behavior;
- do not invent MMT APIs, helper functions, runtime facilities, or library
  availability when implementing embedded C logic;
- keep event descriptions consistent with their executable boolean expressions;
- preserve event correlation whenever the scenario requires relationships between observations;
- return a complete `<beginning>...</beginning>` XML document.
- when a protocol attribute is passed to an embedded function, use its supplied `security_c_type` to determine the compatible C parameter type when that information is available, and do not guess a parameter type when it is not;

Syntactic correctness alone does not guarantee that a generated property correctly represents the intended monitoring behavior.

The agentic property-generation architecture therefore treats the following as separate concerns:

1. XML well-formedness;
2. MMT property syntax;
3. availability of protocol attributes and other static references;
4. semantic correctness of the monitoring logic;
5. runtime and behavioral validity.