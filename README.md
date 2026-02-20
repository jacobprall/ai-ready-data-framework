# The AI-Ready Data Framework

<div align="center">
<a href="https://www.apache.org/licenses/LICENSE-2.0">
        <img src="https://img.shields.io/badge/Code-Apache%202.0-blue.svg" alt="Code License: Apache 2.0"></a>
<a href="https://creativecommons.org/licenses/by-sa/4.0/">
        <img src="https://img.shields.io/badge/Content-CC%20BY--SA%204.0-lightgrey.svg" alt="Content License: CC BY-SA 4.0"></a>

</div>

<p></p>

# Introduction

The **AI-Ready Data Framework** is an open standard that defines what "AI-ready" actually means. The five factors of AI-ready data provide criteria and requirements to help you evaluate your data, pipelines, and platforms against the demands of AI workloads. Use this framework to assess where you stand and prioritize what matters most for your specific AI ambitions.

## Background

The contributors to this framework include practicing data engineers, ML practitioners, and platform architects who have built and operated AI systems across industries.

This document synthesizes our collective experience building data infrastructure that can reliably power AI. Our goal is to help data practitioners design infrastructure that produces trustworthy AI decisions.

## Who should read this document?

* **Data engineers** building pipelines that power AI systems.  
* **Platform teams** designing infrastructure for ML and AI workloads.  
* **Architects** evaluating whether their stack can support RAG, agents, or real-time inference.  
* **Data leaders** who need to assess organizational AI readiness and communicate gaps to their teams.
* **Coding Agents** building the data infrastructure they will eventually consume

## The Five (+1) Factors of AI-Ready Data

0. [**Clean**](factors/0-clean.md) — Clean data is consistently accurate, complete, consistent, and valid.
1. [**Contextual**](factors/1-contextual.md) — Contextual data carries canonical semantics; meaning is explicit and co-located.
2. [**Consumable**](factors/2-consumable.md) — Consumable data is served in the right format and at the right latencies for AI workloads.
3. [**Current**](factors/3-current.md) — Current data reflects the present state with freshness enforced by systems, not assumed by AI consumers.
4. [**Correlated**](factors/4-correlated.md) — Correlated data is traceable from source to every decision it informs.
5. [**Compliant**](factors/5-compliant.md) — Compliant data meets regulatory requirements through enforced access controls, clear ownership, and auditable AI-specific safeguards.

These factors apply to any data system powering AI applications, regardless of tech stack.

## Requirements

Each factor is backed by a set of measurable **requirements** — specific criteria that can be evaluated against your data and platform. The full canonical list lives in [`factors/requirements.yaml`](factors/requirements.yaml).

The factor markdown files above describe the *why* and *what* of each factor in prose. The requirements file provides the machine-readable counterpart: every requirement has a unique key, a description, and a `workload` tag indicating whether it applies to `serving`, `training`, or both. All tests should be evaluated against a threshold and return a normalized score between 0 and 1, making it straightforward to build automated assessments or dashboards on top of the framework. 

## Related Resources

- [A Brief History of Data](factors/history-of-data.md)
- Contribute to this framework

## Contributors

[CONTRIBUTOR LIST]

## License

All content and images are licensed under a <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0 License</a>

Code is licensed under the <a href="https://www.apache.org/licenses/LICENSE-2.0">Apache 2.0 License</a>