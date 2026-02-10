# The AI-Ready Data Framework

The **AI-Ready Data Framework** is an open standard that defines what "AI-ready" actually means. The five factors of AI-ready data provide criteria to help you evaluate your data, pipelines, and platforms against the demands of AI workloads. Use this framework to assess where you stand and prioritize what matters most for your specific AI ambitions.

## Background

The contributors to this framework include practicing data engineers, ML practitioners, and platform architects who have built and operated AI systems across industries. This document synthesizes our collective experience building data systems that power reliable and trustworthy AI systems.

The format is inspired by Martin Fowler's work on defining technical patterns, the 12-Factor App methodology, and the 12 Factor Agent.

## Who Should Read This

* **Data engineers** deploying pipelines that power AI systems.
* **Platform teams** designing infrastructure for ML and AI workloads.
* **Architects** evaluating whether their stack can support RAG, agents, or real-time inference.
* **Data leaders** who need to assess organizational AI readiness and communicate gaps to their teams.
* **Coding agents** building the infrastructure they'll eventually consume.

## The Five Factors of AI-Ready Data

| Factor | Name | Definition |
|---|---|---|
| **0** | [**Clean**](factor-00-clean.md) | Accurate, complete, valid, and free of errors that would compromise downstream consumption |
| **1** | [**Contextual**](factor-01-contextual.md) | Meaning is explicit and co-located with canonical semantics |
| **2** | [**Consumable**](factor-02-consumable.md) | Served in the right format, at the right latencies, at the right scale |
| **3** | [**Current**](factor-03-current.md) | Reflects the present state, with freshness enforced by systems |
| **4** | [**Correlated**](factor-04-correlated.md) | Traceable from source to every decision it informs |
| **5** | [**Compliant**](factor-05-compliant.md) | Governed with enforced access controls, ownership, and AI-specific safeguards |

These factors apply to any data system powering AI applications, regardless of tech stack.

## What Is an "AI System"?

An AI system is one that performs **inference** -- it accepts inputs (data values, feature vectors, prompts, documents), applies a learned function shaped by prior inputs (training data), and produces outputs (predictions, classifications, generated content, actions). If there is no inference, it is not an AI system.

The boundary of the AI system is the model and its inference layer. Everything outside that boundary -- data ingestion, transformation, feature engineering, storage, serving -- belongs to the **data layer**, a separate system with its own responsibilities. The data layer's job is to ensure that what crosses the boundary is fit for consumption. This separation of concerns provides a few key benefits:

* When the data layer satisfies the factors of AI-readiness, new AI consumers can be added without re-engineering data infrastructure.
* Data readiness can be assessed and improved independently of any specific model or AI architecture.
* Each system is accountable to its own contract -- data teams own data quality, ML teams own model performance, and failures can be isolated to one side of the boundary.

Our definition is intentionally broad and architecture-agnostic. AI systems may differ in architecture, autonomy, and risk profile, but they share the same fundamental structure: data in, learned function applied, output produced.

## Three Workload Levels

Each factor defines requirements at three levels. Each level is additive -- higher levels include all requirements from lower levels.

| Level | Workload | Tolerance for Issues | Error Recovery |
|---|---|---|---|
| **L1** | Descriptive Analytics and BI | Moderate -- humans in the loop | Human catches it |
| **L2** | RAG and Retrieval Systems | Low -- any chunk can become a response | Fix source, re-embed |
| **L3** | ML Model Training and Fine-Tuning | Very low -- errors are learned, not retrieved | Retrain the model |

## License

All content and images are licensed under a [CC BY-SA 4.0 License](https://creativecommons.org/licenses/by-sa/4.0/).

Code is licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).
