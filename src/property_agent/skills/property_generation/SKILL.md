# MMT Property Generation Skill

## Purpose

Generate an MMT event-based monitoring property from a natural-language
monitoring requirement.

The generated property must represent the intended monitoring behavior
using constructs and protocol information supported by the available
MMT environment.

## Inputs

The generation process may receive:

- a natural-language monitoring task;
- one or more monitored protocols;
- monitoring requirements;
- explicit restrictions;
- monitoring-point information;
- protocol knowledge;
- relevant validated property examples;
- feedback produced by validation tools.

## Procedure

When generating an MMT monitoring property:

1. Analyze the monitoring task and identify the behavior to be detected.

2. Identify the protocol events required to represent that behavior.

3. Determine which protocol attributes are required to characterize
   those events.

4. Verify that required attributes are available in the provided
   protocol knowledge.

5. Identify relationships between events, including ordering,
   correlation, and temporal constraints.

6. Determine the executable condition associated with each event, including any ordinary boolean logic or embedded-function invocation required to represent that event.

7. Determine whether the complete monitoring requirement can be represented using ordinary documented MMT property constructs.

   - Prefer ordinary events, boolean expressions, event references, temporal constraints, and operators when they are sufficient.

   - If the requirement needs additional computation or state that cannot be adequately represented using those constructs, use the documented embedded-function mechanism.

   - When an embedded function is required, synthesize the task-specific C logic needed to implement the canonical monitoring requirement.

   - When protocol attributes are passed to an embedded function, use their supplied `security_c_type` to determine compatible C parameter types when that information is available.

8. Construct the property according to the MMT event-based property
   format.

9. Respect all property-generation restrictions.

10. Use available validation tools to verify the generated property.

11. When validation feedback identifies an error, use the reported
    evidence to revise the property rather than ignoring the error.

## Embedded-function generation

Embedded functions are a general MMT extension mechanism for monitoring logic requiring computation or state beyond ordinary property expressions.

When generating an embedded function:

- place the C implementation inside `<embedded_functions>` according to `property_format.md`;

- use the documented `em_` prefix for newly defined custom functions;

- invoke the function from an event `boolean_expression` using the documented `#function(parameters)` syntax;

- use only protocol, packet, or metadata attributes available in the supplied knowledge as function inputs;

- when an input attribute has a known `security_c_type`, use a compatible C type for the corresponding embedded-function parameter;

- do not replace a known `security_c_type` with another guessed or generic C parameter type;

- if `security_c_type` is null or unavailable for an attribute, do not invent the embedded-function parameter type;

- a null `security_c_type` means only that the embedded-function C representation is not established by the supplied knowledge; it does not mean that the attribute itself is unavailable;

- ensure that each function parameter and its use inside the C implementation are consistent with the corresponding attribute passed from the property;

- normally use the documented `static inline` form for custom embedded functions;

- use `on_load()` or `on_unload()` only when initialization or cleanup is actually required;

- preserve all explicit task semantics, including thresholds, timing, ordering, and correlation requirements.

The generator may design scenario-specific C algorithms and data structures when required by the monitoring task. This may include, for example, counters, persistent state, temporal state, or correlation state.

The generator must distinguish between:

- synthesizing a C algorithm using documented language and MMT integration mechanisms; and
- inventing capabilities of the MMT environment.

The first is allowed. The second is not.

The generator must not invent undocumented MMT APIs, helper functions, runtime facilities, property-language constructs, or unavailable libraries.

An existing protocol attribute must not be used as a substitute for required computation or state merely because its name appears related to counting, timing, aggregation, or another required behavior.

## Knowledge use

Protocol attributes must be obtained from available protocol knowledge.

Do not assume that an attribute exists simply because its name would be semantically convenient for the monitoring requirement.

Protocol knowledge may also provide `security_c_type` for attributes that can be passed to embedded functions. When this information is available, it is the grounding source for the compatible C parameter representation used by the generated embedded function.

The generator must not guess another parameter representation when a known `security_c_type` is supplied. If the required `security_c_type` is unavailable, the generator must not invent the missing C representation.

Attribute availability does not by itself establish that an attribute implements the behavior required by the task. In particular, count-like, time-like, or aggregate-like attributes must not be treated as equivalent to task-specific stateful logic unless that meaning is supported by available knowledge.

MMT property-format and embedded-function behavior must be grounded in `property_format.md` and `restrictions.md`.

Task-specific algorithms implemented inside embedded functions may be synthesized by the model as normal C programming logic, provided they use the documented MMT integration environment.

Validated property examples may be consulted when they are relevant to the current task. Examples provide guidance but must not override the canonical monitoring requirements.

## Supporting resources

The detailed MMT property representation is defined in:

- `property_format.md`

Generation constraints are defined in:

- `restrictions.md`

Previously observed generation problems are documented in:

- `common_errors.md`

## Output

The primary output is an MMT XML monitoring property.

Unless explicitly requested otherwise, the generated XML should not be
surrounded by explanatory prose.