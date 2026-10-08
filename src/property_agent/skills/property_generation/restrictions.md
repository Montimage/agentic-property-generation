# MMT Property Generation Restrictions

This document defines the restrictions that must be respected when generating or modifying MMT event-based monitoring properties.

The restrictions are divided into two categories:

1. **MMT property-language restrictions**, derived from the existing property-format description.
2. **Agentic-generation safeguards**, introduced to prevent recurrent LLM generation errors and to ensure that the generated property remains grounded in available protocol and monitoring knowledge.

---

## 1. General Property Structure

An MMT monitoring property must respect the XML property structure defined by the MMT property language.

A property is represented as a general ordered tree.

The possible property-tree nodes are:

- `<property>`
- `<operator>`
- `<event>`

The following structural restrictions apply:

- `<property>` is required.
- `<property>` must be the root node of the property tree.
- `<event>` nodes are required.
- `<event>` nodes must be leaf nodes.
- `<operator>` nodes are optional.
- One or more properties may be contained inside a `<beginning>` element.
- Optional embedded functions may also be declared within the `<beginning>` element.

The generator must not create unsupported tree structures.

---

## 2. Context and Trigger Semantics

When a property defines a context-trigger relationship:

- the left branch represents the context;
- the right branch represents the trigger;
- the trigger is checked only when the context is valid;
- the property is considered valid when the trigger is found valid.

The generated property must preserve this interpretation when using context and trigger events.

The generator must not arbitrarily reverse the intended context and trigger semantics.

---

## 3. Required Property Attributes

A generated `<property>` must contain the required property attributes.

These include:

- `property_id`
- `description`
- `type_property`

Example:

```xml
<property
    property_id="91"
    description="Example property"
    type_property="ATTACK">
```

The generator must not omit required property attributes.

---

## 4. Supported Property Types

The documented values for `type_property` are:

```text
SECURITY
ATTACK
EVASION
TEST
```

The generator must use one of these documented property types unless additional verified MMT documentation explicitly supports another value.

The generator must not invent new property types.

---

## 5. Property Relationship

The existing property description documents:

```xml
value="THEN"
```

as the logical relationship between a context and its trigger.

If the monitoring requirement requires this relationship, the generated property must use the property structure consistently with this interpretation.

If `value` is absent, the existing property description defines the default value as:

```text
COMPUTE
```

The generator must not assign unsupported values to the `value` attribute.

---

## 6. Temporal Restrictions

Temporal constraints must preserve the timing semantics expressed by the monitoring requirement.

The following documented interpretation applies to `delay_min`:

- a negative value such as `-1` means that the trigger must have occurred before the context;
- `0` means that the trigger must occur simultaneously with the context;
- a positive value means that the trigger must occur after the context.

Existing properties also use `delay_max` to define an upper temporal bound.

The generator must not silently modify explicit temporal requirements.

For example, if the task specifies:

```text
within 5 seconds
```

the property must not use a 10-second window unless the task explicitly permits such adaptation.

---

## 7. Delay Units

The `delay_units` attribute defines the unit associated with temporal constraints.

Existing verified properties use values including:

```text
s
ms
```

The currently available property-format description does not provide a complete enumeration of every supported delay unit.

Therefore:

- the generator should use only delay units supported by verified documentation or examples;
- the generator must not invent undocumented delay-unit identifiers.

If `delay_units` is absent, the existing description states that its default value is:

```text
s
```

---

## 8. COMPUTE Property Restrictions

According to the existing property description, when a property or operator uses:

```text
value = COMPUTE
```

only one `<event>` is required.

In this case:

```text
delay_min = 0
delay_max = 0
```

The generator must respect this constraint when creating a COMPUTE property.

---

## 9. Event Requirements

An `<event>` represents an observable condition evaluated by the monitoring property.

Events may contain:

- `value`
- `event_id`
- `description`
- `boolean_expression`

The generator should assign event identifiers consistently whenever event references are required.

Event identifiers must allow the property to unambiguously reference values captured by previous events.

The generator must not create ambiguous or duplicated event references within the same property.

---

## 10. Event Evaluation

Existing event definitions use:

```xml
value="COMPUTE"
```

to indicate that the event is evaluated using a boolean expression.

The event condition is defined through:

```xml
boolean_expression="..."
```

The generated boolean expression must represent the monitoring condition associated with that event.

The generator must not generate an event whose boolean expression is unrelated to the event description or monitoring objective.

---

## 11. Protocol Attribute Syntax

Protocol or packet attributes must use the format:

```text
<protocol_name>.<field_name>
```

Example:

```text
ngap.procedure_code
```

A value captured during another event can be referenced using:

```text
<protocol_name>.<field_name>.<event_id>
```

Example:

```text
ngap.amf_ue_id.1
```

The generator must respect this syntax when referencing protocol attributes.

---

## 12. Protocol Attribute Availability

A generated property must only use protocol attributes that are available in the monitored MMT environment.

The generator must not invent attributes because their names appear semantically appropriate.

For example, if the protocol knowledge contains:

```text
ngap.procedure_code
ngap.pdu_present
ngap.amf_ue_id
ngap.ran_ue_id
```

but does not contain:

```text
ngap.registration_request_count
```

the generator must not assume that `ngap.registration_request_count` exists.

If the monitoring requirement refers to a concept that is not directly represented by an available attribute, the generator must determine whether it can be expressed using:

- observable protocol attributes;
- multiple events;
- event correlation;
- temporal constraints;
- embedded functions;
- another supported mechanism.

The generator must not replace missing observability with invented fields.

Attribute availability does not by itself establish the operational semantics
of an attribute.

In particular, the existence of a count-like attribute such as:

`protocol.packet_count`

does not establish that the attribute represents:

- the number of events matching the current monitoring condition;
- the number of events correlated by a task-defined identifier;
- the number of matching events within the property's temporal window.

A count-like attribute must not be used as a substitute for stateful or
threshold logic unless its behavior is explicitly established by verified MMT
knowledge or other authoritative evidence.

---

## 13. Protocol Knowledge as Source of Truth

Available protocol knowledge must be treated as the authoritative source for protocol attributes exposed by the monitored MMT implementation.

General knowledge about a protocol does not guarantee that a field is observable by the deployed MMT protocol parser.

Therefore, the generator must distinguish between:

```text
a field that exists conceptually in the protocol
```

and:

```text
a field that is actually exposed by MMT
```

Only the latter may be used when generating an executable property unless additional verified monitoring support is explicitly provided.

---

## 14. Event References

Event references allow a property to reuse values captured by another event.

The syntax is:

```text
protocol.field.event_id
```

For example:

```text
ngap.amf_ue_id.1
```

The referenced event identifier must correspond to an event defined within the property.

The generator must not:

- reference a nonexistent event;
- reference an undefined event identifier;
- use an event reference without a valid source event;
- confuse the current field value with a value captured during a previous event.

Event references should be used only when the monitoring logic requires correlation between events.

---

## 15. Preservation of Correlation Semantics

When the monitoring task requires events to be correlated using a shared identifier or value, the generated property must preserve that relationship.

For example:

```text
ngap.amf_ue_id == ngap.amf_ue_id.1
```

can express that the current event refers to the same AMF UE identifier observed in event `1`.

The generator must not remove or replace correlation constraints when they are essential to the monitoring requirement.

---

## 16. Boolean Expression Restrictions

Boolean expressions may use:

- packet fields;
- protocol attributes;
- values captured by previous events;
- supported embedded functions.

The generator must ensure that every `boolean_expression` is compatible with both the XML representation and the known MMT expression syntax.

Simple comparisons should be explicitly parenthesized, for example:

```xml
boolean_expression="(protocol.attribute == value)"
````

When multiple conditions are combined using logical operators, the complete compound expression must also be enclosed within an additional outer pair of parentheses.

Correct:
```xml
boolean_expression="((protocol.attribute == value1) &amp;&amp; (other_protocol.attribute == value2))"
```

Incorrect:
```xml
boolean_expression="(protocol.attribute == value1) &amp;&amp; (other_protocol.attribute == value2)"
```

The second form must not be generated. Although the individual conditions are parenthesized, the complete compound expression is not grouped. This form has been confirmed to be rejected by the real MMT `compile_rule` parser.

For expressions containing more than two conditions, explicit grouping must be preserved throughout the complete logical expression.

Characters requiring XML escaping must be escaped correctly.

For example, logical AND inside an XML attribute must appear in the XML source as: `&amp;&amp;`
which is interpreted by MMT as: `&&`.

Raw `&&` must not be written directly inside an XML attribute because the ampersand character has special meaning in XML.

Logical OR may be represented as: `||`

when used according to expression structures demonstrated by validated properties.

The generator must not introduce operators, grouping forms, or expression constructs whose support has not been established by the available property documentation, validated property examples, or confirmed MMT compiler behavior.

Logical operators inside `boolean_expression` must not be confused with
the `value` attribute of an XML `<operator>` element.

In particular, boolean conjunction and disjunction must not be represented
using structures such as:

```xml
<operator value="AND">
<operator value="OR">
```

Logical `AND` and `OR` belong inside `boolean_expression`.

---

## 17. Embedded Function Placement

Custom embedded C functions must be declared inside an:

```xml
<embedded_functions>
```

element.

Existing valid properties place `<embedded_functions>` within the `<beginning>` container and outside individual `<property>` elements.

Example:

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

The generator must not place `<embedded_functions>` inside a `<property>` unless additional verified MMT documentation explicitly allows it.

---

## 18. Embedded Function Naming

New custom embedded functions should use the prefix:

```text
em_
```

Example:

```text
em_5g_check_msg_throughput
```

This avoids confusion with existing MMT functions.

The generator should preserve this convention when implementing new custom functions.

---

## 19. Embedded Function Invocation

An embedded function is called from an event boolean expression using:

```text
#<function_name>(<parameters>)
```

Example:

```text
#em_5g_check_msg_throughput(meta.utime)
```

The generator must ensure that:

- the function being invoked is available;
- custom functions have been defined when required;
- the number and meaning of parameters correspond to the function definition;
- the function call appears in a supported location.

The generator must not invoke a custom function that has not been defined or provided by the environment.

Protocol, packet, or metadata attributes available to the generated property may be passed as parameters to embedded functions.

The generator must ensure that:

- each argument corresponds to an available attribute or supported value;
- the argument type is compatible with the corresponding C parameter;
- the generated C function uses its parameters consistently with the monitoring requirement.

Embedded functions used in boolean expressions are evaluated when the corresponding boolean expression is verified by MMT-Security.

---

## 20. Embedded Function Lifecycle Functions

The `<embedded_functions>` section may define:

```c
void on_load(){
    ...
}
```

and:

```c
void on_unload(){
    ...
}
```

`on_load()` is executed when the XML rules are loaded into MMT-Security.

`on_unload()` is executed when MMT-Security exits.

The generator must not assume that these functions are required for every property.

They should be introduced only when their behavior is needed by the generated property.

Embedded functions may maintain reusable or persistent C state when this is required by the monitoring algorithm.

Initialization that should occur only once may be performed in `on_load()` and reused by embedded functions during subsequent rule evaluation.

The specific representation of such state and the algorithm operating on it are task-dependent implementation decisions. The generator may synthesize this C logic when necessary to implement the canonical monitoring requirement.

The generator must not invent undocumented MMT runtime APIs or lifecycle behavior in order to implement such state.

New custom embedded functions should normally use the documented `static inline` form.

---

## 21. Embedded Function Libraries

The existing property description states that the following libraries are pre-included:

```c
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "mmt_lib.h"
#include "pre_embedded_functions.h"
```

If a generated embedded function requires additional libraries, those libraries must be available in the MMT execution environment.

The generator must not assume that arbitrary external C libraries are available.

### 21.1 Embedded Functions for Advanced Monitoring Logic

Embedded functions may be used when the canonical monitoring requirement requires computation or state that cannot be adequately represented using ordinary documented MMT property constructs.

The generator should prefer ordinary property constructs when they are sufficient to represent the complete monitoring requirement.

When additional computation or state is required:

- the generator may synthesize task-specific C logic inside `<embedded_functions>`;
- the generated algorithm must implement the canonical monitoring requirement rather than approximating or weakening it;
- protocol attributes passed to the function must exist in the supplied protocol knowledge;
- the generator may design appropriate C data structures, counters, state-management logic, temporal logic, or other task-specific algorithms as required;
- the generator must not invent MMT APIs, helper functions, runtime facilities, property-language constructs, or unavailable libraries;
- an available protocol attribute must not be used as a substitute for required computation or state merely because its name suggests counting, timing, aggregation, or similar behavior.

Embedded functions are a general extension mechanism and must not be restricted to a predefined set of monitoring scenarios or algorithms.

---

## 22. Reactive Functions

Reactive functions may be used to perform an action when a property is satisfied.

A custom reactive function should:

- be implemented inside `<embedded_functions>`;
- use the `em_` prefix;
- be referenced through the property's `if_satisfied` attribute when appropriate.

The generator must not create a reactive-function reference without ensuring that the referenced function exists.

The documented callback structure is:

```c
typedef void (*mmt_rule_satisfied_callback)(
    const rule_t *rule,
    int verdict,
    uint64_t timestamp,
    uint64_t counter,
    const mmt_array_t * const trace
);
```

---

## 23. Preserve Explicit Numerical Requirements

Explicit numerical values in the monitoring task must be preserved.

This includes:

- thresholds;
- counts;
- time windows;
- minimum values;
- maximum values;
- identifiers when they form part of the monitoring condition.

For example, if the requirement specifies:

```text
more than 10 events within 5 seconds
```

the generator must not silently produce:

```text
more than 20 events within 10 seconds
```

Such a change would alter the semantics of the requested property.

---

## 24. Preserve Event Ordering

When the monitoring requirement expresses an ordered behavior, the generated property must preserve that ordering.

The generator must distinguish between:

```text
A followed by B
```

and:

```text
B followed by A
```

when the ordering affects the meaning of the rule.

The generator must not reorder events solely because another order is easier to express.

---

## 25. Preserve the Monitoring Objective

The generated property must represent the actual security or monitoring objective expressed in the task.

The presence of related protocol attributes is not sufficient.

For example, using registration-related protocol fields does not necessarily mean that a generated property correctly detects a registration flood.

The combination of:

- events;
- conditions;
- temporal relationships;
- thresholds;
- correlations;

must together express the intended behavior.

---

## 26. Do Not Infer Semantic Correctness from XML Validity

A syntactically valid XML property is not necessarily semantically correct.

Therefore:

```text
XML validity ≠ semantic validity
```

The generator must not consider a property complete solely because it passes XML or schema validation.

Semantic validation must evaluate whether the property represents the original monitoring requirement.

---

## 27. Do Not Infer Executability from Schema Validity

A property that satisfies the XML schema may still use:

- unsupported protocol attributes;
- unsupported functions;
- incorrect event references;
- semantically incorrect constructs.

Schema validation therefore does not demonstrate that a property can be successfully executed by MMT.

When runtime or static validation tools are available, they should be used as additional evidence.

---

## 28. Use Deterministic Validation When Available

When a deterministic validator exists for a property characteristic, the generator must rely on that tool rather than on LLM judgment alone.

Examples include:

```text
XML parsing
schema validation
attribute availability
event-reference validation
MMT loading
runtime execution
```

The LLM should not claim that these properties are valid when an available deterministic tool reports otherwise.

---

## 29. Validation Feedback Must Be Preserved

When a validator identifies an error, the diagnostic information must be preserved during property refinement.

The generator should use feedback such as:

```text
error category
location
invalid element
unsupported attribute
invalid event reference
runtime error
```

to guide corrections.

The generator must not ignore a deterministic validation error and simply regenerate the same unsupported construct.

A construct explicitly identified as invalid by deterministic validation
must not appear unchanged in the next repaired candidate.

Compiler-confirmed structural restrictions must also be preserved during
repair.

In particular:

- `INVALID_PROPERTY_ARITY` must be resolved by producing a `<property>`
  with at most two direct child elements;

- a third direct `<event>` or `<operator>` must not survive repair;

- the two-child restriction must not be bypassed by inventing unsupported operators, undocumented nesting, unsupported aggregation mechanisms, unsupported counters, undocumented embedded-function syntax, or other unsupported property-language constructs;

- when the required monitoring behavior genuinely requires additional computation or state, a documented embedded function may be used as a supported implementation mechanism rather than adding invalid direct property children.

---

## 30. Corrections Should Be Local When Possible

When repairing a property, the generator should preserve parts of the property that already satisfy the monitoring requirement.

A validation error affecting one element does not automatically require redesigning unrelated parts of the property.

For example, if the only problem is an unsupported attribute, the repair should focus on finding a supported representation of that concept while preserving valid:

- thresholds;
- event ordering;
- timing constraints;
- correlations;
- property type.

This helps prevent repair attempts from introducing new semantic errors.

---

## 31. Restrictions on Invented Knowledge

The generator must not fabricate:

- protocol attributes;
- MMT functions;
- property-language elements;
- operator syntax;
- event-reference syntax;
- library availability;
- runtime behavior.

These restrictions do not prohibit the generator from synthesizing task-specific C algorithms using documented C language features and the documented MMT embedded-function interface.

The distinction is between generating an algorithm and inventing capabilities of the MMT execution environment.

When required information is unavailable, the system should identify the missing knowledge rather than generating an unsupported construct.

---

## 32. Verified Examples Are Guidance, Not Templates

Validated property examples may be used to understand common MMT structures.

However, an example must not be copied mechanically if its semantics differ from the current task.

The generator must adapt the property according to:

- the current monitoring objective;
- current protocols;
- current observable attributes;
- temporal requirements;
- correlation requirements.

Example similarity does not guarantee semantic equivalence.

---

## 33. Multi-Protocol Example Restrictions

Some verified example properties may contain attributes from several protocols.

For example, a property may combine:

```text
ngap
nas_5g
sctp_data
```

or:

```text
http2
ip
meta
```

The presence of these fields in a verified example does not imply that those protocol attributes are available in every monitoring scenario.

The generator must verify protocol availability for the current task before reusing constructs from a multi-protocol example.

---

## 34. Monitoring-Point Restrictions

When monitoring-point information is available, generated properties should use only information observable at that point.

A protocol field may exist within the system but still be unavailable at a particular observation point.

The generator must not assume universal visibility of all protocol information.

If monitoring-point observability is unknown, the property should not claim that such observability has been verified.

---

## 35. Output Format

The primary output of the property-generation task is the MMT XML property.

Unless the calling workflow explicitly requests otherwise, the generator should return the XML property without additional explanatory prose surrounding it.

For example, prefer:

```xml
<beginning>
    ...
</beginning>
```

rather than:

```text
Here is the generated property:

<beginning>
    ...
</beginning>

I hope this helps.
```

This restriction simplifies parsing and downstream validation.

---

## 36. No Silent Requirement Relaxation

If the monitoring requirement cannot be represented using ordinary MMT constructs or protocol attributes, the generator should consider whether the documented embedded-function mechanism can implement the required computation or state.

If no supported representation can be established, the generator must not silently weaken the requirement.

For example, it must not transform:

```text
Detect repeated registration attempts from the same UE
```

into:

```text
Detect any NGAP traffic
```

simply because the latter is easier to express.

When exact representation is not possible, the limitation should be reported to the workflow so that additional knowledge, tooling, or an alternative representation can be considered.

---

## 37. Separation of Syntax and Semantics

The generation workflow must treat the following as distinct concerns:

```text
Property-format correctness
Protocol/attribute support
Semantic correctness
Runtime executability
Behavioral correctness
```

Passing one validation level must not automatically imply that the others are satisfied.

For example:

```text
well-formed XML
```

does not imply:

```text
correct monitoring behavior
```

and:

```text
schema-valid XML
```

does not imply:

```text
successful MMT execution
```

---

## 38. Principle for Generated Properties

A generated property should be considered suitable for downstream use only when its representation is grounded in:

- the original monitoring task;
- the documented MMT property format;
- applicable property restrictions;
- available protocol knowledge;
- relevant validated examples when used;
- evidence produced by available validation tools.

The generator must avoid unsupported assumptions whenever objective information is available from the system.

---

## 39. Operator Structure

Verified MMT properties demonstrate that `<operator>` elements may occur
directly inside a `<property>` and may contain multiple `<event>` elements.

A `<property>` may contain multiple direct child elements only within the
compiler-confirmed limit of at most two direct children in total.

Therefore, a property may contain:

- up to two direct `<event>` and/or `<operator>` children in total;

- an `<operator>` containing multiple `<event>` elements, when supported by
  the documented operator structure.

The `value` of an XML `<operator>` must be one of the values explicitly
documented in `property_format.md`; logical boolean operators such as AND
and OR must not be used as XML operator values.

Event identifiers are scoped to the complete property. Therefore, an
event in one operator may reference an event defined in another operator
of the same property.

The available evidence does not establish that operators can be nested.

The generator must therefore not create nested `<operator>` structures
unless additional verified MMT documentation or examples establish that
such nesting is supported.

## 40. Property Identifier

The `property_id` is supplied by the monitoring task.

The generator must:

- use exactly the `property_id` supplied by the task;
- not invent a different property identifier;
- not reuse an identifier from an example;
- not modify or reinterpret the identifier.

The property identifier is administrative information and must not be
inferred from the scenario semantics.

---

## 41. Property Direct-Child Arity

The real MMT `compile_rule` parser permits at most two direct child
elements inside a `<property>` element.

Therefore:

- a `<property>` must contain no more than two direct child elements;
- those children may be valid `<event>` and/or `<operator>` elements,
  subject to the other structural restrictions;
- three or more direct `<event>` and/or `<operator>` children are invalid;
- do not add a third direct child to represent an additional condition;
- conditions that cannot be represented within the documented MMT
  structure must not be approximated by inventing unsupported XML
  constructs.

This restriction is based on compiler-confirmed behavior:

`HALT_SEC: Error 13f: Unexpected more than 2 children in property tag`