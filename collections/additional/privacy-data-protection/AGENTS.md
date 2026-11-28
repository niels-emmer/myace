# Privacy & Data Protection

Privacy-by-design conventions for software that handles personal data, written around the EU GDPR
(Regulation 2016/679) and applicable to most privacy regimes. This collection layers on a base
collection; it complements `eu-ai-act` (AI-specific obligations) and `auditor` (security review). It
produces engineering evidence and drafts, not legal advice: a qualified person decides legal questions.

## Privacy Output Is A Draft, Not Legal Advice

<!-- myace: priority=90 tags=privacy,governance -->

Everything this collection produces (data maps, DPIA drafts, retention proposals, response drafts) is input to a decision by the organisation's privacy lead or counsel. Say which questions need a qualified human (lawful basis, international transfers, regulator notification) and never state that something is compliant; state what was checked and what was not.

## Know What Personal Data You Hold

<!-- myace: priority=70 tags=privacy,data -->

Before adding a field, table, log line, analytics event or third-party call, say whether it is personal data (anything relating to an identifiable person, including identifiers, location and online identifiers) and why it is needed. Keep a record of the categories, purpose, source, location, recipients and retention for each store. See the `personal-data-inventory` skill.

## Collect Less, Keep It Shorter

<!-- myace: priority=70 tags=privacy,data -->

Collect only what a stated purpose needs, use it only for that purpose, and give every personal-data store a retention period with an automated deletion or anonymisation path. Prefer not collecting, then pseudonymising, then aggregating. A column with no purpose is a defect, not a convenience.

## Personal Data Stays Out Of Logs, Prompts And Test Fixtures

<!-- myace: priority=90 tags=privacy,security -->

Do not write personal data to application logs, error reports, analytics, URLs or prompts sent to third-party AI services unless it is necessary and the destination is approved for it. Use synthetic or irreversibly anonymised data in tests, fixtures and demos; never copy production data into a development environment.

## Plan For Subject Rights And Incidents

<!-- myace: priority=70 tags=privacy,operations -->

Design so a person's data can be found, exported, corrected and deleted across every store, backup policy and processor, and so a breach can be detected, scoped and reported inside the regulator deadline (GDPR Art. 33 gives 72 hours from awareness to notify the supervisory authority where required). See the `subject-request-handling` skill.

## Check Processors And Transfers Before Integrating

<!-- myace: priority=90 tags=privacy,vendor -->

Before sending personal data to a vendor or a region, check there is a processor agreement, the vendor's sub-processors and location are acceptable, and a transfer mechanism exists for data leaving the EEA. Flag the integration for the privacy lead; do not add it on the strength of a working API key.
