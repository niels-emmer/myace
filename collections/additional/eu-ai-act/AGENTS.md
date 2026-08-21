# EU AI Act Compliance

## Classify Risk Tier Before Anything Else

Before any compliance work, classify the AI system into the EU AI Act's risk
tier — unacceptable (prohibited), high, limited, or minimal — and identify the
actor role (provider, deployer, importer, distributor). Obligations depend
entirely on the tier and role; working without a classification is guessing.
Use the `eu-ai-act-risk-classification` skill's decision tree, and record the
tier + role + reasoning as the first line of any compliance output.

## Extraterritorial Reach — "Not in the EU" Is Not Out of Scope

The AI Act applies to any AI system whose output is used in the EU or whose
deployment affects EU residents, regardless of where the provider or deployer
is headquartered. Don't assume a non-EU org is exempt. When in doubt about
whether a system touches EU residents, treat it as in scope and say so.

## High-Risk Obligations Are Lifecycle, Not One-Time

For high-risk systems, risk management (Art 9), data governance (Art 10),
technical documentation (Art 11), record-keeping/logging (Art 12), transparency
(Art 13), human oversight (Art 14), and accuracy/robustness/cybersecurity
(Art 15) are ongoing obligations across the whole lifecycle — not a one-time
assessment. They sit alongside the quality management system (Art 17),
conformity assessment (Art 43), EU declaration of conformity, CE marking,
registration in the EU database (Art 49), post-market monitoring (Art 72), and
serious-incident reporting (Art 73). A review that only checks "did we do it
once" is incomplete.

## Transparency Is Live Now

Article 50 — chatbot AI-disclosure (50(1)), machine-readable marking of
synthetic content (50(2)), emotion-recognition/biometric-categorisation notice
(50(3)), and deepfake/public-interest-text labelling (50(4)) — is enforceable
from 2 August 2026. Treat it as in force, not future work. It applies to
limited-risk systems too, not just high-risk ones. See the
`eu-ai-act-transparency` skill.

## Human Oversight Is Designed In, Not Bolted On

Oversight must be designed into the system (Art 14), not added as an
afterthought. Assign a human who understands the system's capabilities and
limits, can interpret its output, and can override or abort it. A "human in
the loop" checkbox with no named, trained, empowered human is not oversight.

## Documentation Is a Deliverable, Not an Afterthought

Technical documentation (Annex IV), the EU declaration of conformity, the
risk-management file, data-governance records, and (for GPAI) the training-data
summary are compliance deliverables. Produce them as artifacts alongside the
code, kept in sync with the system's actual design — not reconstructed after
the fact. See the `eu-ai-act-documentation` skill.

## Compliance Output Is Evidence, Not Legal Advice

This collection produces classification, gap analysis, and documentation
drafts — never a legal assertion of compliance. Flag anything requiring binding
interpretation (whether a system is genuinely high-risk, whether an exemption
applies, fine exposure) for human/legal review. Never write "we are compliant"
as a conclusion; write "no gaps identified against the obligations checked,
subject to legal review."
