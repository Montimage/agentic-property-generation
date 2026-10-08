# Semantic Validation Skill

## Purpose

Evaluate whether a generated MMT monitoring property correctly represents
the meaning and expected behavior of the original monitoring requirement.

Semantic validation is distinct from XML well-formedness, MMT syntax,
static-reference validation, and runtime validation.

A property may be syntactically valid and executable while still
representing the intended monitoring scenario incorrectly.

The objective of semantic validation is therefore to determine whether the
generated property expresses the monitoring logic required by the original
task.

---

## Inputs

Semantic validation should consider the following information when
available:

- the original natural-language monitoring task;
- the structured monitoring task derived from that input;
- explicit monitoring requirements;
- explicit restrictions;
- authorized task assumptions;
- unresolved task ambiguities;
- the generated MMT property;
- protocol attributes exposed by MMT;
- established protocol-domain knowledge available to the semantic reviewer;
- monitoring-point information;
- relevant property examples, only when explicitly supplied by the
  validation workflow.

The current monitoring task is the authoritative specification of the
monitoring objective.

Explicit requirements, restrictions, authorized assumptions, and unresolved
ambiguities must be interpreted as part of that task specification.

Protocol semantics that are not explicitly encoded in the task may be
evaluated using established protocol-domain knowledge available to the
semantic reviewer.

This includes the meaning of message identifiers, procedure values,
enumerated states, protocol states, and other protocol-specific constants.

The reviewer must not fabricate a semantic mapping when it cannot establish
that mapping with sufficient confidence.

Protocol attribute knowledge establishes which attributes are observable,
but does not by itself establish the semantic meaning of particular values
of those attributes.

Property examples, when supplied, are non-authoritative and should be used
only as structural references.

They must not be used to infer or introduce:

- task requirements;
- protocol semantics;
- concrete protocol values;
- correlation representations;
- thresholds;
- timing constraints;
- monitoring conditions.

The semantic reviewer should evaluate the generated property against the
current monitoring task and the supplied verified knowledge rather than
against the textual description contained inside the generated property
itself.

Descriptions, comments, event labels, and other natural-language text inside
the generated property are explanatory metadata and must not be treated as
evidence that the executable monitoring logic is semantically correct.

---

## Evaluation Dimensions

Semantic validation is organized into four dimensions:

1. Message and Protocol Semantics
2. Temporal and Ordering Semantics
3. Detection Semantics
4. Attribute Relevance for Scenario Detection

Each dimension evaluates a different aspect of the generated monitoring
property.

---

## A. Message and Protocol Semantics

Evaluate whether the property correctly represents the protocol behavior
described by the monitoring scenario.

This dimension focuses on whether the events represented in the property
correspond to the intended protocol interactions.

The validation should determine whether:

- the property uses the correct protocol or protocols;
- the selected protocol events correspond to the scenario;
- the intended message exchanges are represented correctly;
- the involved entities are represented consistently;
- protocol procedures or message identifiers correspond to the intended
  behavior;
- protocol identifiers are interpreted consistently with the current task
  and established protocol-domain knowledge.

For example, if the monitoring requirement refers to a particular
protocol operation or message, the generated property should identify
the corresponding observable protocol behavior rather than an unrelated
operation or message.

The reviewer may use established protocol-domain knowledge to determine which
concrete protocol value represents the requested behavior.

The reviewer must not invent such a mapping when it cannot establish the
mapping with sufficient confidence.

The semantic reviewer should not assume that an event is correct solely
because its textual `description` appears related to the scenario.

The executable condition represented by the event's `boolean_expression`
must also correspond to the intended protocol behavior.

---

## B. Temporal and Ordering Semantics

Evaluate whether the property correctly represents the temporal and ordering relationships required by the monitoring scenario.

This dimension includes:

- event ordering;
- temporal windows;
- delay constraints;
- thresholds associated with time;
- dependencies between events;
- transitions between events;
- correlations that depend on event order.

The semantic reviewer should determine whether the property preserves the temporal meaning of the original task.

For example, if the task specifies:

```text
Event A must be followed by Event B within 5 seconds
```

the generated property should preserve:

```text
A -> B
```

and should not reverse the order.

Similarly, a 5-second window should not be silently transformed into a different temporal interval.

Explicit values such as:

```text
delay_min
delay_max
delay_units
```

should be compared against the original monitoring requirement.

The reviewer should also distinguish between:

```text
more than N events
```

and:

```text
at least N events
```

when the distinction affects the intended behavior.

Temporal validity should therefore consider both numerical values and their associated semantics.

Temporal behavior may also be implemented inside an embedded function.

When the generated C implementation participates in enforcing a task time window, timeout, expiration, reset condition, or other temporal requirement, the reviewer must include that executable logic in this dimension.

A correct XML `delay_max` does not compensate for incorrect temporal logic inside an embedded function, and embedded temporal logic must not be ignored merely because the surrounding property contains delay attributes.

Temporal issues should be reported only in this dimension when they concern the task's timing or ordering semantics.

---

## C. Detection Semantics

Evaluate whether the complete property logic actually characterizes the behavior, anomaly, attack, or violation described by the monitoring task.

This dimension focuses on the monitoring objective itself.

A property may contain protocol events related to a scenario while still failing to represent the condition that distinguishes the target behavior.

For example:

```text
detect messages of a given type
```

is not equivalent to:

```text
detect an excessive rate of those messages
```

The second scenario may additionally require:

- repeated events;
- a numerical threshold;
- a time window;
- correlation between events;
- identification of the same source or entity.

The reviewer must determine these requirements from the current monitoring task rather than from the example itself.

The semantic reviewer should therefore evaluate whether the combination of:

- events;
- boolean expressions;
- thresholds;
- timing constraints;
- correlations;
- embedded functions when present;

collectively implements the intended monitoring objective.

When required detection behavior is implemented inside an embedded function, the reviewer must inspect the function body rather than treating the function invocation itself as evidence that the behavior exists.

When the embedded function receives protocol attributes, Detection Semantics must also consider whether the invocation and C function interface are compatible with supplied `security_c_type` information.

A known mismatch between an attribute argument and its embedded-function parameter representation is a `PROPERTY_LOGIC_ERROR` because it affects the correct execution of the monitoring logic.

For stateful detection requirements, the reviewer should verify that the algorithm actually maintains the state required by the canonical task.

For example, when a task requires a threshold over repeated observations, the presence of a counter-like variable or attribute is not sufficient. The executable logic must implement the required counting semantics, correlation semantics, temporal constraints, and threshold boundary, as applicable to the task.

The reviewer should determine whether the property is:

- too general;
- too restrictive;
- missing an essential condition;
- introducing conditions unrelated to the task;
- implementing a different behavior from the requested one.

The property description alone must not be considered sufficient evidence of correct detection semantics.

The actual monitoring logic must support the behavior claimed by the description.

---

## D. Attribute Relevance for Scenario Detection

Evaluate whether the protocol and packet attributes used by the property are relevant and sufficient to characterize the monitoring scenario.

This dimension does not evaluate the structure or content of the generated alert.

In MMT, the attributes used by the property are exposed as part of the resulting alert information.

The objective is therefore to determine whether the property selects appropriate observable attributes for detecting and characterizing the scenario.

The validation should determine whether:

- the selected attributes are relevant to the monitoring objective;
- the attributes provide information necessary to characterize the monitored behavior;
- correlation attributes are used when the scenario requires events to be linked to the same entity, UE, stream, connection, or other identifier;
- attributes used in conditions contribute meaningfully to the detection logic;
- unnecessary attributes do not introduce unrelated constraints;
- the property does not omit attributes that are necessary to distinguish the target behavior from normal protocol activity.

Attribute availability and attribute relevance must be treated as separate questions.

For example:

```text
Is the attribute exposed by MMT?
```

is different from:

```text
Is the attribute useful for detecting this scenario?
```

An attribute may be available in MMT while being irrelevant to the current monitoring task.

Similarly, an attribute may appear semantically useful for a scenario but cannot be used if it is not exposed by the monitored MMT implementation.

Attribute availability should therefore be verified using protocol knowledge or deterministic tools when available.

This semantic dimension focuses on whether the attributes that were selected are meaningful and appropriate for implementing the intended detection logic.

When protocol, packet, or metadata attributes are supplied as parameters to an embedded function, their relevance must be evaluated according to how the generated C algorithm actually uses them.

Passing an appropriate attribute to a function does not by itself establish that the function uses that attribute correctly.

Likewise, an attribute whose name suggests counting, timing, or aggregation must not be assumed to implement the corresponding task behavior unless its semantics actually support that interpretation.

---

## Protocol Knowledge and Semantic Validation

Semantic validation must distinguish between protocol attribute availability
and protocol semantic meaning.

### Protocol attribute knowledge

Protocol attribute knowledge describes what observable information is exposed by the monitored MMT implementation.

It can establish facts such as:

```text
<protocol>.<message_attribute> exists
<protocol>.<entity_identifier> exists
<protocol>.<transport_attribute> exists
```

This knowledge is authoritative for determining whether an attribute can be referenced by an executable MMT property.

Protocol attribute knowledge may also provide `security_c_type` for attributes that can be passed to embedded functions.

When `security_c_type` is available, it establishes the compatible C representation expected for that attribute when used as an embedded-function parameter.

For example:

```text
qualified_name: ngap.amf_ue_id
security_c_type: double
```

means that an embedded function receiving ngap.amf_ue_id must use a compatible C parameter representation.

A null or unavailable `security_c_type` does not mean that the protocol attribute itself is unavailable. It means only that its embedded-function C representation is not established by the supplied knowledge.

Attribute availability does not by itself establish the semantic meaning of a particular attribute value.

For example, knowing that: `<protocol>.<attribute>` is available does not by itself establish what: `<protocol>.<attribute> == <value>` represents.

### Protocol semantic knowledge
Protocol semantic meaning may be evaluated using:

1. the current canonical monitoring task;
2. authorized task assumptions;
3. established protocol-domain knowledge available to the semantic reviewer.

The system does not require a separate protocol-semantic database for every
supported protocol.

The reviewer may use established protocol-domain knowledge to interpret
protocol procedures, message identifiers, enumerated values, states, causes,
operations, and other protocol-specific concepts.

However, the reviewer must not fabricate a mapping merely because it appears
plausible or would make the monitoring task easier to express.

If a required protocol-semantic mapping cannot be established with sufficient
confidence, the reviewer should report: `KNOWLEDGE_MISSING` and explain which semantic fact could not be established.

### Task-defined operational mappings
A mapping explicitly defined by the canonical monitoring task is part of the
operative specification.

For example, if the task explicitly states that observations sharing a
particular identifier must be treated as originating from the same source,
that mapping is authoritative for task conformance.

The reviewer must not require independent protocol-semantic confirmation
merely to verify that the generated property follows such an explicit
task-defined operational mapping.

This does not authorize unrelated factual protocol-semantic claims.

### Grounding protocol-specific semantic claims
Whenever a generated property uses a concrete protocol-specific value to
represent a semantic concept, the reviewer must evaluate the evidence for
that mapping.

This applies generally to values such as:

- message identifiers;
- message types;
- procedure identifiers;
- operation codes;
- enumerated values;
- states;
- status codes;
- method identifiers;
- cause values;
- flag values;
- protocol-specific numerical or textual constants.

A semantic mapping may be considered supported when it can be established
from at least one of:

1. an explicit canonical task requirement;
2. an authorized task assumption;
3. established protocol-domain knowledge available to the reviewer.

Retrieved property examples are structural evidence only.

They must not be treated as the sole justification for a protocol-semantic
mapping.

The reviewer must not treat a mapping as correct merely because:

- the attribute exists;
- the value appears plausible;
- the XML is valid;
- the property compiles;
- the same value appears in a retrieved example.

If the required mapping cannot be established with sufficient confidence,
report: `KNOWLEDGE_MISSING`.

A score of `0.5` is normally appropriate when the property may be plausible
but semantic correctness cannot be established confidently.

---

## Event Correlation

When the monitoring scenario involves multiple events, semantic validation
should determine whether the property correctly establishes the required
relationship between them.

Possible relationships include:

- same entity;
- same source;
- same destination;
- same connection;
- same transaction;
- same session;
- same protocol identifier;
- another explicitly defined observable correlation key.

For example, when the monitoring task explicitly defines an observable
identifier as the correlation key, a property may compare:

```text
<protocol>.<entity_identifier> == <protocol>.<entity_identifier>.1
```

to associate the current event with the identifier captured by an earlier
event.

The reviewer should determine whether correlation is required by the current
monitoring task and whether the selected attribute represents exactly the
relationship defined by that task.

The reviewer must not replace the task's explicitly defined correlation
representation with another representation obtained from an example, prior
knowledge, or a plausible alternative implementation.

---

## Threshold Semantics

When a monitoring task contains an explicit threshold, semantic validation
must verify that the generated property preserves it.

For example:

```text
more than 10 requests
```

must not silently become:

```text
more than 20 requests
```

The reviewer should also examine comparison boundaries.

For example:

```text
more than 10
```

corresponds conceptually to:

```text
> 10
```

whereas:

```text
at least 10
```

corresponds conceptually to:

```text
>= 10
```

when the corresponding operators are supported.

Changing the comparison boundary changes the behavior of the monitoring
property.

---

## Semantic Validation of Embedded Functions

When an embedded function is used, semantic validation must evaluate the actual executable C logic of that function in relation to the canonical monitoring task.

The existence of an embedded function, its name, comments, or event description is not sufficient evidence that the required monitoring behavior has been implemented.

The reviewer should determine whether:

- the embedded function is semantically necessary or appropriate for the required monitoring behavior;
- the function parameters correspond to observable information required by the task;
- the values passed from the MMT property correspond to the parameters actually used by the C implementation;
- when a protocol, packet, or metadata attribute has a known `security_c_type`, the corresponding embedded-function C parameter uses a compatible type;
- the C implementation does not reinterpret a parameter in a way that is incompatible with its supplied `security_c_type`;
- a known mismatch between an invocation argument's `security_c_type` and the embedded-function parameter representation is treated as an executable property defect rather than as missing knowledge;
- the C implementation preserves explicit thresholds and comparison boundaries;
- required temporal behavior is implemented correctly;
- required correlation or entity separation is preserved;
- persistent or reusable state is managed consistently with the monitoring requirement when state is necessary;
- reset, expiration, or state-transition behavior does not alter the intended detection semantics;
- the returned value represents the condition expected by the invoking event;
- the boolean expression invokes the embedded function in a way consistent with its return semantics;
- the function does not introduce additional detection conditions that are absent from the canonical task;
- the function does not omit conditions required by the canonical task.

When `security_c_type` is known, the reviewer should compare the attribute passed by the property with the corresponding C function parameter.

For example, if:
```text
ngap.amf_ue_id
security_c_type: double
```

is supplied, but the generated function declares:
```c
static inline bool em_check(const void *amf_ue_id) {
    ...
}
```

the interface is inconsistent with the supplied attribute representation.

This should be reported as `PROPERTY_LOGIC_ERROR` in Detection Semantics.

If `security_c_type` is null or unavailable and correct assessment genuinely depends on knowing that representation, the reviewer must not guess it. `KNOWLEDGE_MISSING` may be used only when that missing representation is necessary to determine correctness.

The reviewer may reason about ordinary C programming semantics in order to evaluate the generated algorithm.

For example, it may inspect comparisons, counters, data structures, branches, timestamps, state updates, and return conditions to determine whether the algorithm implements the task.

This does not authorize the reviewer to assume undocumented capabilities of the MMT environment.

The reviewer must not invent or assume undocumented:

- MMT APIs;
- helper functions;
- runtime facilities;
- library behavior;
- protocol attributes;
- lifecycle behavior.

If correctness depends on an MMT-specific runtime behavior that cannot be established from the supplied knowledge, report `KNOWLEDGE_MISSING`.

The semantic reviewer does not replace deterministic C or MMT compilation. Its responsibility is to determine whether the executable algorithm represented by the embedded function corresponds to the canonical monitoring requirement.

---

## Current Task Authority

The current MonitoringTask is the authoritative specification of what the
generated property is expected to implement.

The reviewer must not add, replace, or reinterpret task requirements.

In particular, it must not claim that the task requires:

- another correlation identifier;
- another protocol attribute;
- another message or procedure;
- another threshold;
- another time window;
- another monitoring condition;

unless that requirement is explicitly present in:

1. the current MonitoringTask;
2. an authorized task assumption; or
3. established protocol-domain knowledge where factual protocol semantics
   are required to evaluate the property.

If the task explicitly defines a representation, that representation takes
precedence.

For example, if the task explicitly states that one observable identifier
represents the same source, the reviewer must evaluate the property using
that identifier. It must not replace it with another source representation.

Examples contained in this skill are illustrative only and must never be
treated as requirements of the current task.

---

## Semantic Validation Principles

### Do not infer semantic correctness from MMT syntax validity

A property may satisfy the known structural and syntactic rules of the MMT
property language while containing incorrect:

- events;
- temporal relationships;
- thresholds;
- correlations;
- monitoring logic.

Therefore:

```text
MMT syntax validity != semantic validity
```

---

### Do not infer semantic correctness from schema validity

A property may conform to the MMT XML schema while containing incorrect:

- events;
- temporal relationships;
- thresholds;
- correlations;
- monitoring logic.

Therefore:

```text
schema validity != semantic validity
```

---

### Do not infer semantic correctness from executability

A property that loads and executes successfully in MMT may still implement
the wrong monitoring requirement.

Therefore:

```text
executability != semantic correctness
```

Runtime execution should be treated as separate validation evidence.

---

### Preserve explicit requirements

The semantic reviewer should verify that the generated property preserves
explicit requirements contained in the original task.

These may include:

- message types;
- procedures;
- event ordering;
- numerical thresholds;
- temporal windows;
- correlation constraints;
- monitored entities;
- protocol restrictions.

The property must not silently relax or modify these requirements.

---


### Distinguish property errors from underspecified tasks

The semantic reviewer must distinguish between an incorrect generated
property and information that was never specified by the monitoring task.

For example, if the task requires:

```text
an abnormal number of requests
```

but does not define a numerical threshold or another explicit criterion for
what constitutes abnormal behavior, the reviewer must not invent one.

This should be reported as: TASK_UNDERSPECIFIED rather than automatically treating an arbitrary generated threshold as
correct.

Similarly, if a semantic fact cannot be established because required
protocol knowledge is unavailable, it should be reported as: KNOWLEDGE_MISSING.

---

### Evaluate executable logic, not descriptions

The semantic reviewer must focus primarily on:

```text
boolean_expression
event relationships
temporal constraints
attribute references
embedded-function behavior
```

rather than relying on:

```text
property description
event description
```

Human-readable descriptions may support interpretation but are not the
executable monitoring logic.

---

### Avoid introducing unsupported assumptions

If semantic validation requires information that cannot be established with
sufficient confidence, the reviewer should identify the uncertainty.

The reviewer may use established protocol-domain knowledge when evaluating
protocol semantics.

However, it must not fabricate:

- protocol-semantic mappings it does not know confidently;
- unavailable protocol attributes;
- monitoring-point visibility;
- MMT runtime behavior;
- property-language features;
- task requirements that were never specified.

Missing information should be reported explicitly when it prevents a
reliable semantic assessment.

---

## Scoring

Each semantic dimension is evaluated independently.

The supported scores are:

```text
1.0 = aligned
0.5 = partially aligned
0.0 = not aligned
```

### Score 1.0

Use `1.0` when the property adequately represents the aspect being
evaluated and no meaningful semantic inconsistency has been identified.

### Score 0.5

Use `0.5` when:

- the property partially represents the intended behavior but contains a
  meaningful semantic limitation; or
- the available task or protocol knowledge does not allow the reviewer to
  establish full semantic correctness.

A score of `0.5` therefore represents either partial alignment or unresolved
semantic uncertainty.

The associated issue category should indicate whether the cause is the
property itself, missing knowledge, or task underspecification.

### Score 0.0

Use `0.0` when the relevant behavior is:

- demonstrably incorrect;
- absent despite being required by the task;
- substantially inconsistent with the task;
- implementing a different detection behavior from the requested one.

A lack of sufficient knowledge to establish correctness should normally
produce a score of `0.5` together with a `KNOWLEDGE_MISSING` issue rather
than a score of `0.0`.

---

## Overall Semantic Assessment

The semantic reviewer should return results for all four dimensions:

```text
A. Message and Protocol Semantics

B. Temporal and Ordering Semantics

C. Detection Semantics

D. Attribute Relevance for Scenario Detection
```

The semantic reviewer must not determine the final acceptance policy.

Its responsibility is to provide:

- the score for each semantic dimension;
- the justification for each score;
- the semantic issues identified;
- an overall summary;
- repair-oriented recommendations.

The semantic-validation workflow calculates the following values
deterministically after receiving the review: `overall_score` and `valid`.

The default overall score is the arithmetic mean of the four semantic
dimension scores:

```text
overall_score =
    (
        message_exchange_semantics
        + temporal_ordering_semantics
        + detection_semantics
        + attribute_relevance
    ) / 4
```

The default strict acceptance policy considers a generated property
semantically valid only when all four semantic dimensions receive a score
of: `1.0`.

Therefore, a high average score must not compensate for a failed or
uncertain semantic dimension.

For example:
```text
A = 1.0
B = 1.0
C = 0.0
D = 1.0
```
produces `overall_score = 0.75` but the property is still semantically invalid because the detection
semantics are not aligned with the monitoring requirement.

The acceptance policy belongs to the deterministic evaluation workflow
rather than the LLM reviewer.

This separation allows alternative acceptance policies to be evaluated
experimentally without changing the semantic-review instructions.

---

## Issue Reporting

When a semantic problem is identified, the reviewer should describe the
issue precisely enough that a property-generation agent can use it for
repair.

Prefer precise feedback grounded in the current monitoring task.

```text
The task requires correlation using <required_identifier>, but the property
uses <different_identifier>.
```

instead of:

```text
The correlation is incorrect.
```

The identifiers named in semantic feedback must come from the current
MonitoringTask, authorized assumptions, or verified knowledge.

Do not introduce an alternative correlation representation that does not
appear in the current task.

Semantic feedback should identify:

- what is incorrect;
- where the inconsistency occurs;
- how it differs from the original requirement.

When appropriate, it may also indicate which requirement should be
reconsidered during repair.

---

## Interaction with Deterministic Validators

Semantic validation complements deterministic validation tools.

The semantic reviewer should not duplicate checks that can be performed
objectively by deterministic tools.

For example:

```text
XML validator
    -> XML well-formedness

MMT syntax validator
    -> known MMT property-language structure and syntax

MMT static validator
    -> protocol attribute availability, event references,
       and embedded-function references

MMT runtime validation
    -> runtime compatibility and behavior when available
```

The semantic reviewer should instead concentrate on questions such as:

```text
Does the selected protocol behavior correspond to the scenario?

Does a protocol value have verified semantic support?

Is this attribute appropriate for representing the intended entity?

Does this correlation express the required relationship?

Does the property preserve the required event order and time window?

Does the complete property implement the requested detection condition?
```

---

## Expected Output

The semantic validation result produced by the semantic reviewer should be
compatible with the `SemanticAssessment` data model.

Conceptually, the output should contain:

```json
{
  "message_exchange_semantics": {
    "score": 0.5,
    "justification": "...",
    "issues": [
      {
        "type": "knowledge_missing",
        "message": "...",
        "evidence": "..."
      }
    ]
  },

  "temporal_ordering_semantics": {
    "score": 1.0,
    "justification": "...",
    "issues": []
  },

  "detection_semantics": {
    "score": 0.0,
    "justification": "...",
    "issues": [
      {
        "type": "property_logic_error",
        "message": "...",
        "evidence": "..."
      }
    ]
  },

  "attribute_relevance": {
    "score": 0.5,
    "justification": "...",
    "issues": [
      {
        "type": "semantic_mismatch",
        "message": "...",
        "evidence": "..."
      }
    ]
  },

  "summary": "...",

  "recommendations": [
    "..."
  ]
}
```

The semantic reviewer should not return:
- the overall score;
- the final acceptance decision;

These values are calculated deterministically by the semantic-validation workflow after the LLM assessment has been parsed.

The final workflow converts the reviewer output into a SemanticReport containing:

```text
message_exchange_semantics
temporal_ordering_semantics
detection_semantics
attribute_relevance
overall_score
valid
summary
recommendations
```

The semantic assessment should be structured so that it can be used both for:
- experimental evaluation;
- deterministic semantic acceptance;
- automatic property refinement in later stages.

---

## General Semantic Validation Principle

Semantic validation should answer the following question:

> Does the generated property use the appropriate observable information,
> relationships, conditions, and temporal behavior to represent the
> monitoring scenario described by the original task?

The validation should therefore evaluate the property as executable
monitoring logic rather than merely as valid XML or plausible
natural-language output.

---
## Semantic Issue Categories

Semantic issues should be assigned one of the following categories:

### `PROPERTY_LOGIC_ERROR`
The executable property logic is incomplete or internally unsuitable for the
required detection behavior.

Example:

```text
The task requires repeated requests above a threshold, but the property
contains only two correlated events and no counting logic.
```

Embedded-function examples include:

- the task requires a threshold but the generated C never maintains or evaluates the required count;
- the task requires correlation by an identifier but the generated state is shared across all identifiers;
- the task requires a time window but the generated algorithm never expires or resets state according to that window;
- a protocol attribute is passed to an embedded function using a C parameter representation incompatible with its known `security_c_type`;
- the generated function returns true under conditions different from those required by the task.

These are property-logic errors when the task is sufficiently specified and the generated executable algorithm is demonstrably incorrect.

### `SEMANTIC_MISMATCH`
The property implements behavior different from the monitoring requirement.

### `TEMPORAL_MISMATCH`
The ordering, time window, delay, or temporal boundary differs from the monitoring requirement.

### `ATTRIBUTE_IRRELEVANT`
An available attribute is used in a way that does not appropriately represent the required entity, relationship, or monitoring behavior.

### `KNOWLEDGE_MISSING`
The available knowledge is insufficient to verify a semantic claim made by the generated property.

Do not use `KNOWLEDGE_MISSING` merely because the property contains task-specific C logic.

Ordinary C programming semantics may be evaluated by the reviewer.

Use `KNOWLEDGE_MISSING` when semantic assessment depends on an external fact that cannot be established, such as undocumented MMT runtime behavior, an unknown MMT helper function, or an uncertain protocol-semantic mapping.

### `TASK_UNDERSPECIFIED`
The original monitoring task lacks information required to construct or verify a fully specified executable monitoring rule.

---

## Distinguishing Task Underspecification from Missing Knowledge

Use `TASK_UNDERSPECIFIED` when information required to define the intended
monitoring behavior is absent from the canonical monitoring task itself.

Examples include:

- a task requests an "abnormal number" of events but provides no threshold;

- a task requests detection within a "short" or "limited" period but provides
  no duration;

- a task requires correlation by "the same source" but does not define what
  constitutes the source and the unresolved representation materially affects
  the monitoring requirement;

- a task refers to a required condition without providing the value or
  criterion needed to define that condition.

Do not infer or invent a missing task requirement.

Use `KNOWLEDGE_MISSING` when:

- the canonical monitoring task is sufficiently specified;
- evaluating the generated property requires a factual protocol-semantic
  mapping; and
- that mapping cannot be established with sufficient confidence from the
  canonical task, authorized assumptions, or the reviewer's established
  protocol-domain knowledge.

Examples include:

- the property uses a concrete procedure identifier to represent a named
  protocol procedure, but the reviewer cannot confidently establish that
  mapping;

- the property uses a concrete state value to represent a requested protocol
  state, but the reviewer cannot confidently establish the meaning of that
  value;

- verification depends on protocol semantics that the reviewer does not know
  with sufficient confidence.

A missing task requirement must not be reclassified as missing protocol
knowledge.

The absence of a separate external protocol-semantic database is not, by
itself, a `KNOWLEDGE_MISSING` condition.

---

## Do Not Introduce Unsupported Task Interpretations

Evaluate the generated property against the monitoring task as written.

Do not introduce a more specific technical interpretation of an abstract
task concept unless that interpretation is supported by the canonical task, an authorized
assumption, or established protocol-domain knowledge.

For example, if a task requires events from the "same source", do not
assume that "source" corresponds to a particular connection identifier,
endpoint identifier, entity identifier, session identifier, or other
observable attribute unless that mapping is explicitly supported.

When the task explicitly defines which observable attribute represents the
abstract concept, that definition is authoritative.

When such a mapping is necessary but it cannot be established from the
canonical task, authorized assumptions, or established protocol-domain
knowledge provided, report `TASK_UNDERSPECIFIED` rather than inventing the mapping.