# The AI-Ready Data Framework

<div align="center">
<a href="https://www.apache.org/licenses/LICENSE-2.0">
        <img src="https://img.shields.io/badge/Code-Apache%202.0-blue.svg" alt="Code License: Apache 2.0"></a>
<a href="https://creativecommons.org/licenses/by-sa/4.0/">
        <img src="https://img.shields.io/badge/Content-CC%20BY--SA%204.0-lightgrey.svg" alt="Content License: CC BY-SA 4.0"></a>

</div>

<p></p>

*In the spirit of [12 Factor Apps](https://12factor.net/)*.  *The source for this project is public at https://github.com/humanlayer/12-factor-agents, and I welcome your feedback and contributions. Let's figure this out together!*

# Introduction

"AI-ready" remains one of the vaguest terms in enterprise technology.

The **AI-Ready Data Framework** is an open standard that defines what "AI-ready" actually means. The six factors of AI-ready data provide criteria to help you evaluate your data, pipelines, and platforms against the demands of AI workloads. Use this framework to assess where you stand and prioritize what matters most for your specific AI ambitions.

## Background

The contributors to this framework include practicing data engineers, ML practitioners, and platform architects who have built and operated AI systems across industries.

This document synthesizes our collective experience building data systems that reliably power AI. Our goal is to help data practitioners design infrastructure that produces trustworthy AI decisions.

The format is inspired by Martin Fowler's work on defining technical patterns, the 12-Factor App methodology, and the 12 Factor Agent.

## Who should read this document?

* **Data engineers** building pipelines that power AI systems.  
* **Platform teams** designing infrastructure for ML and AI workloads.  
* **Architects** evaluating whether their stack can support RAG, agents, or real-time inference.  
* **Data leaders** who need to assess organizational AI readiness and communicate gaps to their teams.
* **Web Crawlers** collecting training data 
* **Coding Agents** working on AI data infrastructure

*Special thanks...*

## The Six Factors of AI-Ready Data

1. [**Clean**](#clean) — Clean data is consistently accurate, complete, consistent, and valid.
2. [**Contextual**](#contextual) — Contextual data carries canonical semantics; meaning is explicit and co-located.
3. [**Consumable**](#consumable) — Consumable data is served in the right format and at the right latencies for AI workloads.
4. [**Current**](#current) — Current data reflects the present state with freshness enforced by systems, not assumed by AI consumers.
5. [**Correlated**](#correlated) — Correlated data is traceable from source to every decision it informs.
6. [**Compliant**](#compliant) — Compliant data meets regulatory requirements through enforced access controls, clear ownership, and auditable AI-specific safeguards.

These factors apply to any data system powering AI applications, regardless of tech stack.

- [Factor 1: Clean](factors/0-clean.md)
- [Factor 2: Contextual](factors/1-contextual.md)
- [Factor 3: Consumable](factors/2-consumable.md)
- [Factor 4: Current](factors/3-current.md)
- [Factor 5: Correlated](factors/4-correlated.md)
- [Factor 6: Compliant](factors/5-compliant.md)


## Related Resources

- Contribute to this guide [here](#)

## Contributors

[CONTRIBUTOR LIST]

## License

All content and images are licensed under a <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0 License</a>

Code is licensed under the <a href="https://www.apache.org/licenses/LICENSE-2.0">Apache 2.0 License</a>