# MMT Property Repair Skill

## Purpose

Repair an existing generated MMT monitoring property using explicit
validation and semantic feedback.

The objective is to correct identified problems while preserving all
parts of the property that are already consistent with the monitoring
task.

Repair is different from initial property generation.

The repair agent starts from an existing candidate property and must
modify it only when supported by the supplied diagnosis, monitoring
task, and verified knowledge.

---

## Inputs

The repair process may receive:

- the original monitoring task;
- the current generated property;
- a deterministic repair diagnosis;
- deterministic validation issues;
- semantic validation issues;
- semantic-review recommendations;
- the MMT property format;
- property-generation restrictions;
- known generation errors;
- protocol attributes exposed by MMT.

The repair agent must treat the original monitoring task as the
authoritative source of monitoring requirements.

---

## Repair Objective

The repair agent should correct the issues identified by the supplied
diagnosis while changing as little of the current property as necessary.

The repair process should preserve:

- valid XML structures;
- correct event conditions;
- correct protocol references;
- correct temporal constraints;
- correct event correlations;
- correct embedded functions;
- all explicit task requirements.

Unrelated parts of the property should not be rewritten merely to produce
a different formulation.

---

## Property Identifier

The `property_id` supplied by the monitoring task is immutable.

The repair agent must:

- preserve exactly the same `property_id`;
- never copy an identifier from another property;
- never generate a replacement identifier;
- never alter the identifier as part of repair.

---

## Preserve Explicit Task Requirements

The repair agent must preserve explicit requirements including:

- monitoring objective;
- protocols;
- message or procedure requirements;
- event ordering;
- numerical thresholds;
- temporal windows;
- delay units;
- correlation requirements;
- monitored entities;
- monitoring point;
- restrictions explicitly supplied by the task.

The repair agent must repair the property rather than reinterpret the task.

---

## Minimal Repair Principle

Repairs should be local whenever possible.

For example, if the diagnosis identifies an incorrect temporal relation,
the repair agent should correct the relevant temporal structure without
rewriting unrelated event expressions.

If an event reference is incorrect, the repair agent should correct the
reference while preserving unrelated conditions.

The agent should avoid regenerating the entire property unless the
diagnosed issues make a local repair impossible.

---

## Use Diagnosis as the Repair Scope

The deterministic repair diagnosis defines the scope of the repair.

The repair agent should address issues marked as repairable.

Semantic recommendations may provide useful guidance, but they do not
override:

- the original task;
- deterministic validation evidence;
- verified protocol knowledge;
- the structured semantic issues.

The agent must not introduce additional changes merely because they appear
plausible.

---

## Missing Knowledge

The repair agent must not invent information that is absent from the supplied knowledge.

In particular, it must not invent:

- protocol procedure meanings;
- message identifiers;
- enumerated protocol values;
- unsupported protocol attributes;
- monitoring-point visibility;
- MMT language features.

If required knowledge is unavailable, automatic repair should have been blocked by the diagnosis workflow.

The repair agent must not bypass that restriction.

The prohibition on inventing MMT language features does not prevent the repair agent from synthesizing task-specific C algorithms using the documented embedded-function mechanism.

The repair agent may design normal C logic required by the task, but it must not invent capabilities of the MMT execution environment, such as undocumented APIs, helper functions, libraries, XML constructs, or runtime behavior.

---

## Underspecified Tasks

The repair agent must not invent missing monitoring requirements.

For example, if a task requests an "abnormal number of requests" but does
not define a threshold or another criterion for abnormality, the repair
agent must not invent a numerical threshold.

Such cases should be handled as `TASK_UNDERSPECIFIED` and blocked before
LLM-based repair.

---

## Protocol Attributes

Only protocol attributes supplied in the available MMT protocol knowledge may be introduced during repair.

A repair must not replace one unsupported attribute with another invented attribute.

When an existing attribute is valid and relevant, it should be preserved unless the diagnosis explicitly identifies it as problematic.

Protocol attribute knowledge may also provide `security_c_type` for attributes that can be passed to embedded functions.

When `security_c_type` is available, it is the grounding source for the compatible C parameter representation used by an embedded function.

A repair must not replace a known `security_c_type` with another guessed or generic C parameter type.

If `security_c_type` is null or unavailable, the repair agent must not invent the missing embedded-function C representation.

A null `security_c_type` does not mean that the protocol attribute itself is unavailable. It means only that its C representation as an embedded-function parameter is not established by the supplied knowledge.

---

## Protocol Semantic Knowledge

Available protocol knowledge is authoritative for determining which protocol attributes are exposed by MMT.

The monitoring task is authoritative for operational mappings explicitly defined by the user, such as which identifier represents the "same source" for the current task.

For factual protocol semantics not explicitly defined by the task, the repair agent may use established domain knowledge when it can determine the meaning with sufficient confidence.

It must not guess protocol meanings.

If the required protocol semantics cannot be established reliably, the issue should remain unresolved as missing knowledge rather than being repaired using an invented mapping.

---

## Semantic Repair

When repairing a semantic issue, modify the executable monitoring logic rather than only changing human-readable descriptions.

Relevant executable elements include:

```text
boolean_expression
event relationships
operator structure
delay_min
delay_max
delay_units
event correlations
embedded-function logic
```

Changing only a description does not repair incorrect detection semantics.

When an embedded function participates in the diagnosed monitoring logic, semantic repair must consider the executable C implementation itself.

When the embedded function receives protocol attributes as parameters, semantic repair must also verify that the function signature and parameter handling are compatible with the supplied `security_c_type`, when that information is available.

A known mismatch between the attribute's `security_c_type` and the embedded-function parameter representation is an executable property defect and should be corrected as part of the repair.

The repair agent must not treat such a known mismatch as missing knowledge.

The repaired function must preserve all task requirements relevant to its behavior, including where applicable:

- thresholds;
- temporal windows;
- correlation keys;
- ordering;
- state transitions;
- reset or expiration conditions.

Replacing missing monitoring logic with a semantically unrelated protocol attribute does not constitute a valid semantic repair.

---

## Structural Repair

When deterministic validation identifies a structural or syntactic issue, the repair agent should correct the minimum structure necessary to satisfy the documented MMT property format.

The repair agent must not introduce undocumented tags, attributes, property types, operators, or delay units.

A repaired `<property>` must contain no more than two direct child elements.

When the diagnosis contains `INVALID_PROPERTY_ARITY`:

- reduce the property to at most two valid direct `<event>` and/or `<operator>` children;
- do not preserve a third direct child;
- do not invent unsupported operators or undocumented nesting to bypass the restriction.

If the underlying monitoring requirement requires additional computation or state, a documented embedded function may be introduced when semantically appropriate. It must not be added merely as a structural workaround for the arity error.

---

## Boolean-expression repair

When repairing an event that contains a compound boolean expression,
ensure that the complete logical expression is enclosed within an outer
pair of parentheses.

Correct:
```xml
boolean_expression="((condition_1) &amp;&amp; (condition_2))"
```

Incorrect:
```xml
boolean_expression="(condition_1) &amp;&amp; (condition_2)"
```

Preserve XML escaping for logical AND as `&amp;&amp;`.

---

## Embedded Functions

Existing embedded functions should be preserved unless they are involved in a diagnosed issue.

A new embedded function may be introduced when:

- the supplied diagnosis identifies missing or incorrect executable monitoring logic;
- the required behavior cannot be adequately represented using ordinary documented MMT property constructs; and
- the required behavior is sufficiently specified by the canonical monitoring task.

When introducing or repairing an embedded function:

- place the implementation inside `<embedded_functions>` according to the documented property format;
- use the documented `em_` prefix for newly defined custom functions;
- invoke the function through a supported event `boolean_expression`;
- pass only protocol, packet, or metadata attributes available in the supplied knowledge;
- when an input attribute has a known `security_c_type`, use a compatible C type for the corresponding embedded-function parameter;
- do not replace a known `security_c_type` with another guessed or generic C parameter type;
- if `security_c_type` is null or unavailable for an attribute, do not invent the embedded-function parameter type;
- ensure that each C function parameter and its use inside the function are consistent with the corresponding value passed from the property;
- normally use the documented `static inline` form for custom embedded functions;
- use `on_load()` or `on_unload()` only when initialization or cleanup is actually required;
- preserve all explicit task semantics.

The repair agent may synthesize task-specific C algorithms and data structures when necessary. This may include counters, persistent state, temporal state, correlation state, or other computation required by the monitoring task.

The repair agent must not invent undocumented MMT APIs, helper functions, runtime facilities, property-language features, or unavailable libraries.

Embedded functions must not be used to hide invented thresholds, unsupported protocol semantics, or other missing task information.

Likewise, count-like, time-like, or aggregate-like protocol attributes must not be substituted for required stateful logic unless their relevant semantics are established by available knowledge.

---

## One Repair Attempt

A single invocation of the repair agent produces one revised candidate.

The repair agent does not decide whether another repair attempt should be performed.

Revalidation and additional repair attempts are responsibilities of the orchestration workflow.

---

## Output

Return exactly one complete MMT XML document.

The output must:

- begin with `<beginning>`;
- end with `</beginning>`;
- preserve the task `property_id`;
- contain no Markdown code fences;
- contain no explanatory prose outside the XML.

Do not return a repair explanation.

The structured diagnosis already records why the repair was requested.