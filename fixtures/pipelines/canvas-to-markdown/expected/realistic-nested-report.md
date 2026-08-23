# Canvas Relationship Report

## Top-Level Groups

- Company Principles (`group-company`)
  - Node: Ownership over handoff (`node-principle-ownership`)
  - Node: Short feedback loops (`node-principle-feedback`)
  - Child Group: Client Space (`group-client`)
    - Node: Large enterprise release process (`node-client-context`)
    - Nested Group: Risks (`group-risks`)
      - Node: Approval latency (`node-risk-approval`)
      - Node: Role ambiguity (`node-risk-ambiguity`)

## Ungrouped Nodes

- Independent note (`node-outside`)

## Edges

- node-principle-ownership -> node-client-context | from=group-company | to=group-client | shared=group-company
- node-client-context -> node-risk-approval | from=group-client | to=group-risks | shared=group-client
- node-risk-approval -> node-risk-ambiguity | from=group-risks | to=group-risks | shared=group-risks
- node-principle-feedback -> node-outside | from=group-company | to= | shared=
