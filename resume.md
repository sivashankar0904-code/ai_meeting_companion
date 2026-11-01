# Sivashankar S

**AI Engineer | Gen AI Developer**

Email: sivashankar0904@gmail.com | Phone: +91 9597497765 | LinkedIn: [linkedin.com/in/sivashankar-shanmugam](https://linkedin.com/in/sivashankar-shanmugam) | GitHub: [github.com/sivashankar0904-code](https://github.com/sivashankar0904-code)

---

## Professional Summary

AI Engineer and Gen AI Developer with 8+ years of experience delivering production AI systems, architecting agentic, event-driven platforms — from multi-agent orchestration, generative UI, and RAG pipelines. Skilled at translating ambiguous business and domain workflows into resilient, production-grade platforms, and at leading engineering teams through that build. Comfortable owning technical decisions end-to-end: architecture, tooling tradeoffs, and delivery.

---

## Technical Skills
  - **RAG & Semantic Search:** RAG (LangChain + pgvector, Amazon Bedrock Knowledge Bases), Semantic Search (SentenceTransformer, Amazon Aurora, Amazon OpenSearch), RAG Evaluation (RAGAS)
  - **LLMs & Agents:** LLM Integration (AWS Bedrock, LangChain OpenAI, Anthropic SDK, LiteLLM adapter — Claude), LangGraph (agentic critique loops), Amazon Bedrock AgentCore
  - **Document Intelligence:** OCR (Tesseract, AWS Textract), Document Intelligence
  - **Machine Learning:** Classification & Model Bake-off (scikit-learn, XGBoost, LightGBM, CatBoost, Random Forest), MLflow (experiment tracking, model versioning), AWS SageMaker (training, tuning, Experiments), SageMaker Model Registry (champion-challenger promotion)
  - **Monitoring:** Drift Detection (PSI, KS tests)
- **Observability & CI/CD:** Prometheus, Grafana, Loki, Tempo, OpenTelemetry (OTel), Langfuse, Jenkins CI/CD, GitLab CI/CD
- **Languages / Frameworks:** Python (FastAPI, Django, Flask) — primary | Go (Gin), JavaScript
- **Databases:** PostgreSQL (pgvector), Amazon Aurora, Amazon OpenSearch, MongoDB, MySQL, Redis, Neo4j, Elasticsearch, Apache Iceberg (data lakehouse)
- **Messaging / Streaming:** Kafka (Amazon MSK), gRPC, RabbitMQ, Celery (Workers, Beat), WebSocket, Redis Streams
- **Orchestration:** n8n (workflow-driven execution planning)
- **Cloud & Infrastructure:** AWS (ECS, EKS, S3, RDS, MSK, EventBridge, Lambda, IAM, Bedrock), Docker
- **Architecture:** Microservices, Event-Driven Architecture, CDC (Kafka Connect), Append-Only Audit Logging, Multi-Tenant SaaS, REST APIs, IAM/RBAC, GeoJSON/Shapefile

---

## Professional Experience

### Lead Engineer (leading a team of 8)
**Spartan Technologies** | *June 2026 – Present*

- **Owned** end-to-end technical architecture and system design across the company's Document Processing and Audit Automation platforms — directing an 8-engineer team on service boundaries, event topology, and technology selection.

#### Intelligent Document Processing Platform

- **Architected** a cloud-agnostic, agentic AI, event-driven document intelligence platform with Kafka as the control bus across 16+ microservices and LLM-backed agents.

##### AI Agents & MLOps
- **Designed** a multi-agent workflow coordinating autonomously via an LLM-agnostic adapter for provider-independent model swapping.
- **Built** an automated critique loop for generation-critique-revise review of escalated decisions.
- **Established** the ML lifecycle: model bake-off across multiple algorithms with champion/challenger promotion and drift detection triggering automated retraining.
- **Architected** the RAG pipeline — chunking, embedding, and retrieval combined with graph entity context for grounded LLM responses.
- **Built** an event-driven text/OCR extraction pipeline — S3 upload triggers via EventBridge invoking Lambda functions for serverless document parsing.

##### Analytics & Anomaly Detection
- **Built** the analytics ETL pipeline curating raw document/audit data into an **Apache Iceberg** lakehouse for ad-hoc querying.
- **Trained** anomaly detection models (Isolation Forest, Z-score) on **Amazon SageMaker**, with experiment tracking via MLflow, over the curated Iceberg dataset.
- **Delivered** a RAG-powered analytics chatbot — an Agent layer over the LLM-agnostic adapter (LiteLLM) retrieving grounded context from pgvector to answer document/KPI queries in natural language, with generative UI dynamically rendering charts and drill-down detail views for analytics and anomaly-detection results.

##### Orchestration & Data
- **Built** the orchestration layer on n8n workflows, encoding the execution plan — agent sequencing, model selection, and rules-pack routing — without an external manifest.
- **Designed** the persistence architecture enforcing a sole-writer pattern via Kafka relay, with append-only audit logging and schema for job/file/event tracking.
- **Engineered** a multi-provider storage abstraction (S3, Azure Blob, MinIO) with a user-selectable storage/bucket registry and gRPC-based streaming file ingestion.
- **Implemented** distributed task processing using Celery Workers with RabbitMQ queueing, and Celery Beat for periodic/scheduled runs, backed by circuit-breaker retry/resume.

##### Observability & Evaluation
- **Instrumented** system and AI pipeline observability with **OpenTelemetry** — metrics in Prometheus, logs in Loki, and distributed traces in Tempo — unified in Grafana dashboards across microservices and agent workflows.
- **Monitored** agentic workflows with **Langfuse** — tracing agent runs, tool calls, latency, token usage, and cost across LLM providers for debugging and quality review.
- **Established** continuous RAG evaluation with **RAGAS** — tracking faithfulness, answer relevancy, and context precision/recall over time to catch regressions in the retrieval and generation pipeline.

#### Audit Process Automation Platform

- **Architected** an agentic AI-driven automation platform on AWS serverless services (Lambda, SQS, EventBridge).
- **Engineered** a cascading, resilient automation strategy — API automation as primary, with web automation and OCR-based RPA as successive fallbacks.

##### AI Agents & Task Processing
- **Orchestrated** a multi-agent workflow (Notice-Summarizing Agent, Reply Agent, Critic Agent) built on **Amazon Bedrock Agents**, using multi-agent collaboration for supervisor-led task routing.
- **Monitored** agentic workflows with **Amazon Bedrock AgentCore Observability** — tracing agent runs, tool calls, latency, and token usage via CloudWatch for debugging and quality review.
- **Implemented** distributed task processing using Amazon SQS queueing with AWS Lambda workers and Amazon EventBridge Scheduler for periodic/scheduled automation runs, backed by circuit-breaker retry/resume, plus real-time push notifications via Firebase.
- **Decoupled** persistence of external-source API responses through an **Amazon SQS** async queue, with Lambda consumers writing results to the database independently of the automation runs.
- **Built** the core automation service (KPI tracking, job tracker, configurable rules/template engine for automated decisions) backed by Redis caching, and an OCR-based Extraction Service for parsing scanned/PDF documents into structured data.

##### Platform Services
- **Designed** shared platform services — multi-tenant IAM, persistence, and storage gateways — orchestrated via n8n within the company's microservices ecosystem.

---

### Lead Developer
**Dibiz Global Pvt Ltd** | *Nov 2024 – Nov 2025*

#### Secure Document-Centric Collaboration Platform

- **Led** the development of a secure business communication platform with seamless omnichannel Flutter applications deployed across mobile, web, desktop, and Microsoft Teams.
- **Architected** the core backend microservices utilizing Golang (Gin framework) and Python (Django) to deliver high-performance RESTful APIs tailored for real-time secure document exchange and threaded messaging.

##### Collaboration & Messaging
- **Engineered** real-time, document-centric team chat functionality implementing WebSocket and Redis Streams for high-throughput, low-latency collaboration workflows.
- **Implemented** a scalable messaging and caching layer utilizing RabbitMQ and Redis to optimize data access performance and guarantee reliable event-driven updates.

##### AI & Document Intelligence
- **Integrated** advanced AI-driven document processing algorithms for automated data extraction, intelligent categorization, and seamless workflow automation, securely storing assets in **AWS S3**.
- **Built** a **RAG system** using **pgvector** (PostgreSQL) and **LangChain** — document ingestion, chunking, embedding, vector retrieval, and LLM response generation — enabling intelligent document-centric chat within the platform.
- **Tracked** RAG pipeline experiments using MLflow — logging embedding model versions, chunk sizes, and retrieval metrics across iterations.
- **Monitored** system and AI pipeline performance using Prometheus and Grafana.

##### Data, Integrations & DevOps
- **Designed** advanced database schemas across PostgreSQL and MongoDB optimized for strict granular access and secure multi-tenant data isolation, hosted on **AWS ECS/RDS** infrastructure.
- **Devised** robust integrations to synchronize critical transaction data and automate cross-platform approval workflows with external enterprise systems.
- **Onboarded** third-party services critical for enterprise compliance, including Twilio for SMS notifications, SendGrid for email delivery, and Zoho eSign API for legally binding document workflows.
- **Automated** continuous integration and deployment pipelines utilizing Jenkins CI/CD, streamlining release processes for backend microservices.

---

### Senior Backend Developer
**Dibiz Global Pvt Ltd – Palm Oil SaaS Platform** | *Aug 2022 – Nov 2024*

#### Supply Chain Traceability & Geospatial System

- **Implemented** an advanced supply chain traceability system leveraging Neo4j GraphDB, enabling end-to-end visibility and origin mapping across complex supply networks.
- **Engineered** advanced geospatial features to process GeoJSON and Shapefile data, enabling precise mapping and management for palm oil plantations.
- **Developed** an EXIF data filtering system for comprehensive image metadata handling, validation, and geolocation extraction.

#### Microservices Architecture & Integration

- **Designed and delivered** scalable microservices-based backend systems deployed on **AWS EKS** within a collaborative 10-member engineering team, improving deployment efficiency and system reliability.
- **Developed** high-performance RESTful APIs across backend microservices utilizing Golang (Gin) and Python (Django/FastAPI), significantly reducing processing latency.
- **Implemented** robust messaging and notification features leveraging RabbitMQ for event-driven workflows and Redis for an optimized caching layer.
- **Integrated** third-party communication APIs (Twilio for SMS, SendGrid for email) and built an automated weighbridge processing system using SendGrid Inbound Parse webhooks, utilizing **AWS S3** for secure attachment storage.

#### Custom Identity & Access Management (IAM)

- **Engineered** custom Identity and Access Management (IAM) components using Golang and the Gin framework, successfully implementing multi-tenant Role-Based Access Control (RBAC).
- **Created** a seamless authentication integration across microservices by implementing custom Django middleware to interface with the Golang IAM service.
- **Designed** optimized PostgreSQL database schemas tailored for a multi-tenant SaaS architecture, incorporating row-level security to guarantee data privacy.

---

### Senior Python Developer
**C-Square Info Solutions Pvt Ltd** | *Feb 2021 – Aug 2022*

#### Automated Document Processing & Machine Learning Engine

- **Designed and developed** an automated pharmaceutical invoice and order management system capable of processing email attachments from multiple distributors.
- **Implemented** a dynamic template parsing engine integrating Tesseract OCR for precise text extraction from PDF and image formats.
- **Built** machine learning models to enable automated template recognition and document classification, significantly reducing manual data entry.
- **Tracked** model experiments and versions using MLflow — logging parameters, metrics, and artifacts across training runs.
- **Monitored** pipeline health and model performance using Prometheus and Grafana dashboards.
- **Collaborated** effectively with cross-functional teams to ensure the successful delivery of complex automation projects.

#### Data Integration & Real-Time Analytics Platform

- **Architected** a data migration platform utilizing fuzzy mapping algorithms to accurately identify and synchronize pharmaceutical items across different systems.
- **Created** scalable RESTful APIs integrated with Kafka for reliable event streaming and message queuing.
- **Developed** a comprehensive sales analytics dashboard with role-based access control, tailored for both sales and support teams.
- **Implemented** real-time notification and alert systems utilizing email and Telegram bots for active progress tracking.

---

### Python Developer
**Sietec Solutionz Pvt Ltd** | *Oct 2018 – Feb 2021*

#### Automated Reporting & Data Acquisition System

- **Developed** a robust energy monitoring and quality control system utilizing Python to acquire real-time data from industrial SCADA systems and PLCs.
- **Built** an interactive, web-based visualization dashboard using the Flask framework to display live metrics and analytics.
- **Engineered** automated data-pipeline solutions integrating edge device data with SQL Server databases for reliable long-term storage and automated report generation.

---

### Instrumentation Engineer
**Sri Andal Paper Mills** | *Feb 2017 – Nov 2017*

- Built operational efficiency system integrating multi-plant DCS/ERP data with automated reporting.

---

## Education

### M.Sc in Electronics
**University of Tours (Polytech Tours), France** | *Sep 2015 – July 2016*
