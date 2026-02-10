# The AI-Ready Data Framework

<div align="center">
<a href="https://www.apache.org/licenses/LICENSE-2.0">
        <img src="https://img.shields.io/badge/Code-Apache%202.0-blue.svg" alt="Code License: Apache 2.0"></a>
<a href="https://creativecommons.org/licenses/by-sa/4.0/">
        <img src="https://img.shields.io/badge/Content-CC%20BY--SA%204.0-lightgrey.svg" alt="Content License: CC BY-SA 4.0"></a>

</div>

<p></p>

# Introduction

The **AI-Ready Data Framework** is an open standard that defines what "AI-ready" actually means. The five factors of AI-ready data provide criteria to help you evaluate your data, pipelines, and platforms against the demands of AI workloads. Use this framework to assess where you stand and prioritize what matters most for your specific AI ambitions.

## Background

The contributors to this framework include practicing data engineers, ML practitioners, and platform architects who have built and operated AI systems across industries. This document synthesizes our collective experience building data systems that power reliable and trustworthy AI systems.

The format is inspired by Martin Fowler's work on defining technical patterns, the 12-Factor App methodology, and the 12 Factor Agent.

## Who should read this document?

* **Data engineers** deploying pipelines that power AI systems.  
* **Platform teams** designing infrastructure for ML and AI workloads.  
* **Architects** evaluating whether their stack can support RAG, agents, or real-time inference.  
* **Data leaders** who need to assess organizational AI readiness and communicate gaps to their teams.
* **Web Crawlers** collecting training data 
* **Coding Agents** building the infrastructure they'll eventually consume

*Special thanks...*

## The Five Factors of AI-Ready Data

1. [**Contextual**](#contextual) — Contextual data carries canonical semantics; meaning is explicit and co-located.
2. [**Consumable**](#consumable) — Consumable data is served in the right format and at the right latencies for AI workloads.
3. [**Current**](#current) — Current data reflects the present state with freshness enforced by systems.
4. [**Correlated**](#correlated) — Correlated data is traceable from source to every decision it informs.
5. [**Compliant**](#compliant) — Compliant data meets regulatory requirements through enforced access controls, clear ownership, and auditable AI-specific safeguards.

These factors apply to any data system powering AI applications, regardless of tech stack.

- [A Brief History of Data](content/history-of-data.md)
- [Factor 0: Clean](content/factor-00-clean.md)
- [Factor 1: Contextual](content/factor-01-contextual.md)
- [Factor 2: Consumable](content/factor-02-consumable.md)
- [Factor 3: Current](content/factor-03-current.md)
- [Factor 4: Correlated](content/factor-04-correlated.md)
- [Factor 5: Compliant](content/factor-05-compliant.md)

## Reference guide
### What exactly do you mean by "AI system"?

An AI system is one that performs **inference** -- it accepts inputs (data values, feature vectors, prompts, documents), applies a learned function shaped by prior inputs (training data), and produces outputs (predictions, classifications, generated content, actions). If there is no inference, it is not an AI system.

The boundary of the AI system is the model and its inference layer. Everything outside that boundary -- data ingestion, transformation, feature engineering, storage, serving -- belongs to the **data layer**, a separate system with its own responsibilities. The data layer's job is to ensure that what crosses the boundary is fit for consumption. This separation of concerns provides a few key benefits:
* When the data layer satisfies the factors of AI-readiness, new AI consumers can be added without re-engineering data infrastructure.
* Data readiness can be assessed and improved independently of any specific model or AI architecture.
* Each system is accountable to its own contract -- data teams own data quality, ML teams own model performance, and failures can be isolated to one side of the boundary.

Our definition is intentionally broad and architecture-agnostic. AI systems may differ in architecture, autonomy, and risk profile, but they share the same fundamental structure: data in, learned function applied, output produced. 

## Related Resources

- Contribute to this guide [here](#)

## Contributors

[CONTRIBUTOR LIST]

## License

All content and images are licensed under a <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0 License</a>

Code is licensed under the <a href="https://www.apache.org/licenses/LICENSE-2.0">Apache 2.0 License</a>


