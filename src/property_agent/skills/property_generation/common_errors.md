# Common MMT Property Generation Errors

This document records recurrent errors observed when generating MMT
event-based monitoring properties with Large Language Models.

Its purpose is to help the property-generation agent recognize and avoid
previously observed failure patterns.

This document is not a substitute for the formal property specification.

The authoritative sources for generation remain:

- `property_format.md` for the MMT property representation;
- `restrictions.md` for generation constraints;
- protocol knowledge for the attributes actually exposed by MMT;
- deterministic validation tools for syntax and structural correctness.

The errors documented here should be interpreted as practical guidance
derived from previous property-generation experience.

---

## 1. Inventing Unsupported Protocol Attributes

### Error

The generated property uses an attribute that appears semantically
appropriate but is not actually exposed by the monitored MMT protocol
implementation.

Example of an unsupported generated concept:

```text
ngap.registration_request_count
```

The name may appear reasonable for detecting repeated registration
attempts, but this does not mean that such an NGAP attribute exists in
MMT.

### Why it is incorrect

Large Language Models may translate concepts appearing in a natural-language
requirement directly into plausible attribute names.

However:

```text
concept described by the requirement
        !=
attribute exposed by MMT
```

For NGAP, the current protocol knowledge exposes attributes such as:

```text
ngap.procedure_code
ngap.pdu_present
ngap.amf_ue_id
ngap.ran_ue_id
ngap.packet_count
ngap.data_count
ngap.payload_count
ngap.first_packet_time
ngap.last_packet_time
ngap.p_data_len
```

among the attributes reported by the MMT protocol iterator.

### Correct approach

Before using a protocol attribute:

1. identify the required monitoring concept;
2. consult the protocol knowledge;
3. determine whether an observable attribute represents the concept;
4. if the concept is not directly observable, determine whether it can be
   represented using available events, correlations, timing constraints,
   counters, or an embedded function.

Do not create a new field merely because its name would make the property
easier to express.

---

## 2. Confusing Protocol Semantics with Observable Attributes

### Error

The property uses information that exists conceptually in the protocol
or security scenario but is not directly available at the MMT monitoring
interface.

### Why it is incorrect

A protocol specification may contain considerably more information than
the MMT parser exposes as attributes.

Therefore:

```text
defined by protocol specification
        !=
observable through MMT
```

### Correct approach

Treat the MMT protocol attribute repository as the source of truth for
what can be directly referenced by a property.

If the required information cannot be observed directly, use an alternative
representation only when it can be constructed from supported information.

---

## 3. Replacing Behavioral Logic with an Invented Counter Attribute

### Error

A monitoring requirement describes behavior such as:

```text
Detect more than N events during a given time window.
```

The generated property converts this directly into an assumed field such as:

```text
protocol.request_count
```

even though no such field exists.

### Why it is incorrect

Counting repeated events is a stateful monitoring operation and may not correspond to a protocol attribute.

The counter represents monitoring logic rather than necessarily being a field carried by a protocol message.

### Correct approach

### Correct approach

First determine whether the required behavior can be represented using ordinary documented MMT property constructs.

A count-like protocol attribute must not be assumed to implement task-level counting merely because it exists.

Such an attribute may be used for the required behavior only when its semantics establish that it represents the count required by the monitoring task.

If the behavior requires additional computation or persistent state that cannot be adequately represented using ordinary property constructs, consider the documented embedded-function mechanism.

The generation agent may synthesize task-specific C logic for the required counting, temporal, or correlation behavior.

Do not model stateful monitoring behavior by inventing protocol fields or by assigning unsupported semantics to existing count-like attributes.

---

## 4. Incorrect Placement of `<embedded_functions>`

### Error

The generated property places:

```xml
<embedded_functions>
    ...
</embedded_functions>
```

inside a `<property>` element.

For example:

```xml
<beginning>

    <property ...>

        <embedded_functions>
            ...
        </embedded_functions>

        <event .../>

    </property>

</beginning>
```

### Why it is incorrect

Existing valid properties place `<embedded_functions>` within the
`<beginning>` container and outside individual `<property>` elements.

### Correct structure

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

### Correct approach

When custom logic is required:

1. define the embedded functions in the appropriate section of
   `<beginning>`;
2. invoke them from an event's `boolean_expression`.

Do not place the function-definition section inside an individual property.

---

## 5. Calling an Undefined Embedded Function

### Error

A boolean expression contains:

```text
#em_some_function(...)
```

but no corresponding function has been defined and no evidence exists
that the function is supplied by MMT.

### Why it is incorrect

A plausible function name does not imply that such a function exists.

This can produce a property that appears meaningful but cannot execute.

### Correct approach

Before invoking an embedded function, determine whether:

- it is already provided by the MMT environment; or
- it is explicitly implemented in the `<embedded_functions>` section.

For custom functions, use the `em_` naming convention.

---

## 6. Incorrect Embedded Function Invocation

### Error

The generated property defines an embedded function correctly but calls
it using unsupported or inconsistent arguments.

For example, the generated expression may supply:

- the wrong number of parameters;
- protocol attributes incompatible with the function;
- parameters in an incorrect order;
- values unavailable at the current event.

### Why it is incorrect

Function availability alone does not guarantee that a function call is
valid.

Its input parameters must correspond to the implementation.

### Correct approach

Compare the invocation directly against the function signature and the supplied
protocol attribute knowledge.

When a protocol attribute is passed to an embedded function and its
`security_c_type` is known, the corresponding C parameter must use a compatible
type.

For example, if the supplied protocol knowledge contains:

```text
qualified_name: ngap.amf_ue_id
security_c_type: double
```

and the property invokes: `#em_example(ngap.amf_ue_id)` then a compatible function signature is:
```c
static inline bool em_example(double amf_ue_id) {
    ...
}
```

The generator must not replace a known security_c_type with another guessed or generic C parameter representation.

If security_c_type is null or unavailable, do not guess the embedded-function parameter type.

Also verify:
- the number of arguments;
- their order;
- their availability at the current event;
- that the C implementation interprets each parameter consistently with the value supplied by the property.

Do not infer function signatures from function names.

---

## 7. Incorrect Event References

### Error

The property references a value such as:

```text
ngap.amf_ue_id.1
```

when:

- event `1` does not exist;
- event `1` does not provide the intended context;
- the wrong event identifier is referenced;
- the value should refer to the current event rather than a previous event.

### Why it is incorrect

The suffix:

```text
.event_id
```

has semantic meaning.

It refers to the value captured when another event occurred.

### Correct approach

Before generating a reference such as:

```text
protocol.field.1
```

verify that:

1. event `1` exists;
2. the event logically represents the point at which the referenced value
   should be captured;
3. the field is available;
4. comparison with the current event expresses the intended correlation.

---

## 8. Losing Correlation Between Events

### Error

The property correctly identifies two relevant protocol events but does not
ensure that they belong to the same communication context, UE, connection,
stream, or other entity required by the monitoring scenario.

For example, two authentication-related events may be detected without
ensuring that their identifiers correspond.

### Why it is incorrect

Temporal proximity alone does not necessarily mean that two network events
belong to the same interaction.

### Correct approach

When the task requires correlated events, determine which observable
identifier can link them.

Examples from verified properties include comparisons such as:

```text
ngap.amf_ue_id == ngap.amf_ue_id.1
```

and:

```text
sctp_data.data_stream == sctp_data.data_stream.1
```

Correlation requirements must come from the monitoring semantics rather
than being added or removed arbitrarily.

---

## 9. Correct Events but Incorrect Ordering

### Error

The generated property contains the required events but reverses their
logical order.

For example, a task requires:

```text
Authentication Request
        THEN
Authentication Response
```

but the generated property represents the response as the context and the
request as the trigger.

### Why it is incorrect

In an ordered monitoring property, event order contributes directly to its
meaning.

A property can therefore reference all the correct protocol elements while
remaining semantically incorrect.

### Correct approach

Identify explicitly:

```text
context event
trigger event
```

before generating the XML.

Preserve the order expressed by the monitoring requirement.

---

## 10. Incorrect Temporal Window

### Error

The natural-language requirement specifies a particular time constraint,
but the generated property changes it.

Example:

```text
Requirement:
within 5 seconds

Generated property:
delay_max="10"
```

### Why it is incorrect

Changing the temporal window changes the monitored behavior.

The resulting XML may remain syntactically valid while implementing a
different security rule.

### Correct approach

Extract explicit temporal values from the task before property generation.

Verify that:

```text
delay_min
delay_max
delay_units
```

correspond to the intended temporal semantics.

Do not approximate or reinterpret explicit temporal values unless the task
allows it.

---

## 11. Incorrect Delay Units

### Error

The numerical delay is correct but the unit is changed.

For example:

```text
Requirement:
100 milliseconds
```

represented as:

```xml
delay_units="s"
delay_max="100"
```

### Why it is incorrect

The numerical value alone does not determine the temporal constraint.

### Correct approach

Treat:

```text
value + unit
```

as a single semantic requirement.

Both must agree with the original task.

---

## 12. Incorrect Threshold

### Error

The generated property changes a threshold explicitly stated by the user
or scenario.

Example:

```text
Requirement:
more than 10 requests
```

becomes:

```text
counter >= 20
```

### Why it is incorrect

This creates a different monitoring rule while potentially remaining
syntactically and structurally valid.

### Correct approach

Explicit thresholds must be extracted from the monitoring task and
preserved during:

- initial generation;
- syntax repair;
- semantic repair;
- runtime repair.

A correction to another part of the property must not unintentionally
modify the threshold.

---

## 13. Incorrect Threshold Boundary Semantics

### Error

The requirement says:

```text
more than 10
```

but the generated condition uses:

```text
>= 10
```

or the requirement says:

```text
at least 10
```

while the generated property uses:

```text
> 10
```

### Why it is incorrect

These expressions produce different behavior at the boundary value.

### Correct approach

Preserve the exact comparison semantics:

```text
more than N       -> > N
at least N        -> >= N
less than N       -> < N
at most N         -> <= N
equal to N        -> == N
```

only when the corresponding operator is supported by the property
environment.

Boundary conditions should later be tested through behavioral validation
when possible.

---

## 14. Using Related Events Without Implementing the Actual Detection Logic

### Error

A generated property includes events related to the attack or scenario but
does not implement the condition that distinguishes malicious or abnormal
behavior.

For example:

```text
registration-related event detected
```

is not necessarily equivalent to:

```text
registration flooding detected
```

### Why it is incorrect

A property may look semantically plausible because it contains domain
keywords while failing to encode:

- frequency;
- ordering;
- threshold;
- correlation;
- timing;
- mismatch;
- another condition defining the anomaly.

### Correct approach

Identify separately:

1. which events are relevant;
2. what combination of those events constitutes the monitored behavior.

The second part must be represented explicitly.

---

## 15. Generating a Property That Is Too General

### Error

The generated property detects a broad class of traffic rather than the
specific behavior described by the task.

Example:

```text
Task:
detect repeated registration attempts from the same entity

Property:
detect any NGAP message
```

### Why it is incorrect

The generated property technically observes related traffic but does not
represent the requested security objective.

This may cause excessive false positives.

### Correct approach

Preserve all conditions that distinguish the intended behavior from normal
traffic.

Do not simplify the monitoring requirement merely to produce a valid
property.

---

## 16. Generating a Property That Is Too Restrictive

### Error

The generated property adds conditions that were not required and that may
prevent legitimate instances of the target behavior from being detected.

### Why it is incorrect

Additional conditions can change the detection semantics and introduce
false negatives.

### Correct approach

Do not add identifiers, message types, thresholds, timing conditions, or
other restrictions unless they are:

- explicitly required;
- necessary to represent the intended behavior; or
- justified by verified protocol/property knowledge.

---

## 17. Repairing Syntax While Breaking Semantics

### Error

The agent receives a syntax error and modifies the property so that the
XML becomes valid, but the modification changes:

- the threshold;
- the monitored event;
- the event ordering;
- correlation;
- the temporal constraint.

### Why it is incorrect

A successful syntax repair does not justify changing the original
monitoring requirement.

### Correct approach

Repairs should be local whenever possible.

When repairing a structural problem:

1. preserve the original task;
2. preserve already-correct semantic decisions;
3. modify only the elements related to the reported error;
4. submit the repaired property to semantic validation again.

---

## 18. Repairing One Error by Introducing Another

### Error

The agent responds to a validator error by replacing the problematic
construct with another unsupported construct.

Example:

```text
unsupported attribute A
        ↓
repair
        ↓
invented attribute B
```

### Why it is incorrect

The repair is based on language-model plausibility rather than available
knowledge.

### Correct approach

When a validator identifies unsupported information, use a knowledge lookup
before selecting an alternative.

Do not repeatedly guess attribute names.

---

## 19. Ignoring Deterministic Validation Feedback

### Error

A deterministic validator reports an invalid XML structure or unsupported
construct, but the generator retains the same structure because it believes
the property is correct.

### Why it is incorrect

For deterministic properties such as XML/schema validity, validator output
is stronger evidence than LLM judgment.

### Correct approach

Treat deterministic validator feedback as authoritative for the
characteristic being checked.

For example:

```text
XSD validator
    -> authority for schema compliance

protocol registry
    -> authority for known MMT attributes

MMT runtime
    -> authority for whether the property can be loaded/executed
```

The LLM should interpret and act on this evidence rather than override it.

---

## 20. Confusing Schema Validity with Executability

### Error

A generated property passes XML/XSD validation and is therefore considered
complete.

### Why it is incorrect

A schema-valid property may still contain:

- unavailable protocol attributes;
- incorrect embedded-function logic;
- unsupported runtime constructs;
- semantic errors.

### Correct approach

Treat validation levels separately.

A property may require:

```text
XML validation
schema validation
static validation
semantic validation
runtime validation
behavioral validation
```

depending on the capabilities available to the workflow.

---

## 21. Confusing Executability with Semantic Correctness

### Error

The property successfully loads and executes in MMT and is therefore
assumed to implement the original requirement.

### Why it is incorrect

An executable property may still detect the wrong behavior.

For example, it may:

- trigger too early;
- use the wrong threshold;
- correlate unrelated entities;
- trigger on benign traffic;
- fail to trigger on the intended attack.

### Correct approach

Runtime acceptance and semantic correctness must be evaluated separately.

Where test traces are available, compare actual alert behavior against the
expected behavior defined by the monitoring task.

---

## 22. Inappropriate Reuse of a Valid Example

### Error

The agent retrieves a valid example and copies its structure, protocol
attributes, thresholds, or events without adapting them to the current task.

### Why it is incorrect

A verified property demonstrates valid use of the property language but
does not necessarily have the same semantics as the current requirement.

### Correct approach

Use examples to learn patterns such as:

- event correlation;
- timing representation;
- embedded-function placement;
- property structure.

Do not copy task-specific semantics unless they are applicable to the new
requirement.

---

## 23. Copying Attributes from a Multi-Protocol Example

### Error

A retrieved example contains:

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

and the generator assumes all those protocols and fields are available in
the current monitoring task.

### Why it is incorrect

The validity of an example applies to the environment in which that example
was verified.

It does not establish availability for another scenario or monitoring
point.

### Correct approach

Validate protocol availability independently for the current task.

The example repository provides generation guidance, not universal
protocol availability.

---

## 24. Adding an Embedded Function When It Is Not Needed

### Error

The LLM generates custom C code for behavior that can already be represented
using normal property attributes and expressions.

### Why it is problematic

Embedded functions increase:

- implementation complexity;
- execution dependencies;
- validation difficulty;
- opportunities for generation errors.

### Correct approach

Prefer the simplest supported property representation.

Use an embedded function only when the required monitoring behavior cannot
be adequately expressed using the available property constructs.

---

## 25. Avoiding an Embedded Function When Stateful Logic Is Required

### Error

The monitoring task requires stateful behavior such as counting events over time, but the generated property attempts to express the entire behavior as a direct comparison against protocol fields.

### Why it is problematic

Some monitoring concepts are derived from sequences or aggregates rather than directly observable packet attributes.

### Correct approach

Determine whether ordinary documented MMT property constructs can represent the complete monitoring behavior.

If they cannot and the task requires additional computation or persistent state, use the documented embedded-function mechanism when appropriate.

The generation agent may synthesize the task-specific C algorithm required to implement the monitoring behavior.

The generated algorithm may use normal C programming constructs such as counters, data structures, temporal state, or correlation state, provided that it remains within the documented MMT embedded-function environment.

Do not fabricate packet fields or unsupported MMT constructs to represent derived state.

---

## 26. Mixing Property Description and Property Logic

### Error

The generated `description` correctly describes the desired attack, but the
boolean expressions implement different behavior.

### Why it is incorrect

Natural-language descriptions are metadata and do not determine what
MMT actually evaluates.

For example:

```xml
description="Detect registration flooding"
```

does not make the property a registration-flood detector unless its events
and conditions implement that behavior.

### Correct approach

Semantic validation must inspect the executable property logic, not only
its textual descriptions.

---

## 27. Treating Human-Readable Event Descriptions as Evidence

### Error

An event is considered correct because its `description` says:

```text
Authentication Response
```

while its actual `boolean_expression` identifies another message.

### Why it is incorrect

The event description is not the executable condition.

### Correct approach

Always compare:

```text
event description
        ↔
boolean_expression
        ↔
protocol knowledge
        ↔
original task
```

The executable expression must support the meaning claimed by the
description.

---

## 28. Omitting Required Alert Context

### Error

The generated property detects the intended behavior but does not preserve
enough contextual information to make the resulting alert useful.

### Why it is problematic

A detection may require information about the involved entity, protocol
event, or correlated identifiers to support interpretation or downstream
processing.

### Correct approach

When the monitoring task specifies required reporting information, ensure
that the property preserves the relevant context.

Alert/reporting requirements should be evaluated separately from detection
semantics.

---

## 29. Hallucinating Missing Property-Language Syntax

### Error

The generator encounters a monitoring requirement that appears to need an
MMT construct not described in the available property-format knowledge and
creates a plausible XML element or operator.

### Why it is incorrect

Plausible XML is not necessarily valid MMT property syntax.

### Correct approach

When the required construct is not documented:

1. consult available verified examples;
2. consult additional property knowledge when available;
3. use deterministic validation;
4. report the missing capability if it cannot be established.

Do not invent MMT syntax.

---

## 30. Hallucinating `<operator>` Structures

### Error

The property format indicates that `<operator>` nodes may exist, but the
available documentation does not define their complete grammar.

The generator creates a new operator structure based on assumptions.

### Why it is incorrect

Knowing that an element exists is not sufficient to know its valid
attributes, nesting rules, or semantics.

### Correct approach

Use `<operator>` constructs only when supported by:

- verified documentation;
- the schema;
- validated property examples.

Otherwise, do not invent their representation.

---

## 31. Generating Explanatory Text Around XML

### Error

The LLM returns:

```text
Here is your property:

<beginning>
...
</beginning>

This property detects the attack...
```

when downstream code expects XML only.

### Why it is problematic

Additional prose can cause parsing or validation failures.

### Correct approach

When XML output is requested, return only the XML document:

```xml
<beginning>
    ...
</beginning>
```

Reasoning, diagnostics, and validation reports should be returned through
separate structured fields rather than being mixed into the XML.

---

## 32. Error-Handling Principle

When an error is identified, the correction strategy should depend on the
type of error.

### Syntax or XML error

Use deterministic parser or schema feedback.

### Unsupported attribute

Consult protocol knowledge.

### Invalid event reference

Inspect event identifiers and correlation logic.

### Incorrect threshold or timing

Return to the original monitoring task.

### Incorrect protocol semantics

Consult protocol knowledge and the semantic-validation result.

### Incorrect behavioral result

Use expected trace behavior and execution evidence.

### Missing capability

First determine whether the behavior can be implemented using:

1. ordinary documented MMT property constructs; or
2. the documented embedded-function mechanism with task-specific C logic.

Do not invent new MMT property syntax merely because ordinary constructs are insufficient.

If neither a supported ordinary representation nor a grounded embedded-function representation can be established, report the unresolved requirement to the orchestrating workflow.

---

## 33. General Repair Principle

A repair should preserve all verified aspects of the current property.

Conceptually:

```text
Current property
       +
Specific validation evidence
       +
Original monitoring requirement
       +
Relevant knowledge
       ↓
Targeted correction
```

rather than:

```text
Validation error
       ↓
Generate an unrelated property from scratch
```

unless the existing property is fundamentally incompatible with the task.

---

## 34. General Generation Principle

Before considering an MMT property satisfactory, distinguish between the
following questions:

```text
Is the XML well formed?

Is the property structurally valid?

Are the referenced protocols and attributes actually available?

Does the property represent the requested semantics?

Can MMT execute the property?

Does the property behave as expected on representative traffic?
```

These questions are related but not equivalent.

The agent should avoid using success at one level as evidence of success at
all other levels.

---

## 35. Compound boolean expression missing outer grouping

### Incorrect

```xml
<event
    value="COMPUTE"
    event_id="2"
    description="Correlated NGAP event"
    boolean_expression="(ngap.procedure_code == 4) &amp;&amp; (ngap.amf_ue_id == ngap.amf_ue_id.1)"/>
```
Although each individual comparison is parenthesized, the complete
logical expression is not.

The real MMT compiler rejects this form because the logical operator is
encountered outside the grouped expression.

### Correct
```xml
<event
    value="COMPUTE"
    event_id="2"
    description="Correlated NGAP event"
    boolean_expression="((ngap.procedure_code == 4) &amp;&amp; (ngap.amf_ue_id == ngap.amf_ue_id.1))"/>
```
Always enclose the complete compound boolean expression in an additional
outer pair of parentheses.

## 36. Confusing XML `<operator>` Values with Boolean Logical Operators

### Error

The generated property attempts to represent logical conjunction using an
XML operator:

```xml
<operator value="AND">
    ...
</operator>
```

A similar mistake may occur with:
```xml
<operator value="OR">
```

### Why it is incorrect
The XML `<operator>` element and logical operators inside
`boolean_expression` are different language constructs.

The MMT property format defines the supported values of the XML
`<operator>` element.

Logical `AND` and `OR` are expressed inside `boolean_expression`, using the
supported boolean-expression syntax.

Therefore:
```text
XML tree operator
    !=
boolean logical operator
```

### Correct approach
Before creating an `<operator>` element:

1. verify that its value is explicitly supported by `property_format.md`;
2. do not translate the words `AND` or `OR` into XML `<operator>` values;
3. when conditions belong to the same event, combine them inside
`boolean_expression`.

For example: `boolean_expression="((condition_1) &amp;&amp; (condition_2))"`

If deterministic validation reports `INVALID_OPERATOR_VALUE`, the invalid
operator value must not be preserved in the repaired candidate.

## 37. Treating an Embedded Function as Evidence of Correct Monitoring Logic

### Error

The generated property contains an embedded function and the function name or description appears related to the monitoring task, so the property is assumed to implement the required behavior.

For example:

```text
#em_check_request_rate(...)
```

does not by itself establish that the function correctly implements the required rate, threshold, correlation, or time window.

### Why it is incorrect
An embedded function is executable monitoring logic.

Its name, comments, invocation, or existence do not establish its semantic correctness.

The C implementation may:
- use the wrong threshold;
- omit correlation between entities;
- use an incorrect time window;
- share state that should be separated by an identifier;
- fail to reset or expire state correctly;
- return true under conditions different from those required by the task.

### Correct approach
Semantic validation must inspect the executable C implementation and compare its behavior with the canonical monitoring task.

Evaluate, as applicable:
- threshold boundaries;
- counters and state updates;
- correlation keys;
- temporal state;
- reset or expiration behavior;
- return conditions;
- parameters passed from the MMT property, including compatibility with known `security_c_type` information;

Do not treat the presence of an embedded function as proof that advanced monitoring behavior has been implemented correctly.

## 38. Inventing MMT Runtime Capabilities Inside Embedded C

### Error

The generated C algorithm is plausible as normal C code but relies on an
MMT-specific API, helper function, runtime object, library, or lifecycle
behavior that is not documented or otherwise verified.

### Why it is incorrect

The generation agent is allowed to synthesize task-specific C algorithms.

This does not mean that it may invent capabilities of the MMT execution
environment.

For example:

```text
valid C algorithm
    !=
valid use of undocumented MMT runtime functionality
```
A generated algorithm may therefore be logically reasonable while relying on facilities that do not exist in the target environment.

### Correct approach
Distinguish between:
1. task-specific algorithm design; and
2. MMT-environment knowledge.

The generator may synthesize ordinary C logic such as:
- counters;
- arrays or structures;
- state transitions;
- comparisons;
- temporal calculations;
- correlation logic.

It must not invent:
- MMT APIs;
- helper functions;
- protocol attributes;
- runtime callbacks;
- libraries;
- XML integration syntax;
- undocumented lifecycle behavior.

When required MMT-specific functionality cannot be established, report the missing knowledge rather than fabricating it.

## 39. Using an Incorrect C Type for an Embedded-Function Attribute Parameter

### Error

A protocol attribute is passed to a custom embedded function, but the function
declares the corresponding C parameter using a representation incompatible
with the supplied `security_c_type`.

For example, the supplied protocol knowledge states:

```text
qualified_name: ngap.amf_ue_id
security_c_type: double
```

but the generated property defines:

```c
static inline bool em_check_ngap_count(
    const void *amf_ue_id
) {
    ...
}
```

and invokes it using: `#em_check_ngap_count(ngap.amf_ue_id)`

### Why it is incorrect

The embedded-function signature must be compatible with the representation supplied to the function by the MMT-Security property environment.

A protocol attribute may be valid and relevant to the monitoring task while still being handled incorrectly by the embedded C function.

Therefore:
```text
correct attribute
    !=
correct embedded-function interface
```

A mismatch can produce generated C code that fails compilation or interprets the supplied value incorrectly.

### Correct approach

When protocol knowledge provides `security_c_type`, use it as the grounding source for the corresponding embedded-function C parameter.

For the example above, a compatible signature is:
```c
static inline bool em_check_ngap_count(
    double amf_ue_id
) {
    ...
}
```

Do not replace a known `security_c_type` with another guessed or generic C parameter type.

If `security_c_type` is null or unavailable, do not invent the missing C representation.

A null `security_c_type` does not mean that the protocol attribute is unavailable. It means only that its embedded-function parameter representation has not been established by the supplied knowledge.

During semantic review, a mismatch with a known security_c_type should be treated as an executable property-logic defect.

During repair, correct the function signature and any incompatible parameter handling while preserving unrelated valid monitoring logic.
