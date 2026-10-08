# Monitoring Task Assumption Resolution

## Purpose

Resolve remaining task-level ambiguities only after the user has
explicitly authorized the system to make assumptions.

This skill must never be used without explicit user authorization.

## Core Principle

Make the minimum assumptions necessary to obtain an executable
monitoring task.

Every assumption must be recorded explicitly.

An assumption must never be presented as information originally supplied
by the user.

## Allowed Assumptions

Task-level design choices may be assumed when needed, including:

- a numerical monitoring threshold;
- a monitoring time-window duration;
- an operational correlation criterion;
- another missing task parameter required to make the monitoring
  objective executable.

Use only protocol attributes present in the supplied protocol attribute
knowledge when an assumption requires selecting an attribute.

## Forbidden Assumptions

Do not invent factual protocol semantics.

Do not invent:

- unknown procedure-code meanings;
- unknown message-code meanings;
- unsupported protocol attributes;
- undocumented protocol state values;
- factual mappings that require external protocol knowledge.

For example, if verified knowledge does not establish which procedure
code represents a Registration Request, do not invent a procedure code.

That is missing protocol knowledge, not a task-level assumption.

## Minimality

Resolve only ambiguities that remain in the supplied MonitoringTask.

Do not modify explicit user requirements.

Do not replace or reinterpret existing requirements unnecessarily.

Prefer the minimum number of assumptions required to make the task
sufficiently specified.

## Assumption Provenance

Every inferred choice must appear in the `assumptions` output.

If an assumption also creates an executable requirement, include that
requirement in `requirements_to_add`.

Example:

Assumption:
"Treat 10 requests as the abnormal-request threshold."

Requirement:
"Detect more than 10 relevant requests."

## Remaining Ambiguities

If an ambiguity cannot safely be resolved without inventing unsupported
protocol facts, preserve it in `remaining_ambiguities`.

## Output

Return only the JSON object required by the supplied schema.

Do not generate XML.

Do not generate an MMT property.