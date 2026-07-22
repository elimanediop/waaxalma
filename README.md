# Waaxalma

> **Speak for me.**

Waaxalma is an open-source AI Voice Agent Framework that enables natural multilingual communication through intelligent voice agents.

Its mission is to help people communicate seamlessly across languages by combining speech recognition, translation, conversational AI, and speech synthesis into a modular and extensible framework.

---

## ✨ Features

- 🎙️ Speech-to-Text
- 🌍 Multilingual translation
- 🔊 Text-to-Speech
- 🤖 Multi-Agent architecture
- 🧩 Skills-based design
- 🔌 Provider abstraction
- 💬 Session management
- 🚀 FastAPI backend
- 🖥️ Streamlit client

---

## 🏗️ Architecture

```text
Client (Streamlit / API)

        │

        ▼

Agent Layer
(InterpreterAgent, TranslationAgent)

        │

        ▼

Skills Layer
(STT, Translation, TTS, Memory)

        │

        ▼

Provider Layer
(OpenAI today, more providers tomorrow)
```

---

## 🚀 Current Status

**Agent Orchestration – v0.2.**
---

## 📚 Documentation

Project documentation is available in the `docs/` directory.

- Architecture & Vision Book
- Roadmap
- Future design decisions (ADR)

---

## 🗺️ Roadmap

| Repository Version | Milestone           | Focus                                                            |
| ------------------ | ------------------- | ---------------------------------------------------------------- |
| **v0.1.0**         | Prototype           | Voice → Translation → Speech proof of concept                    |
| **v0.2.0**         | Agent Orchestration | Unified execution pipeline, AgentOrchestrator, SessionContext    |
| **v0.3.0**         | Reliability         | Validation, retries, timeouts, tracing, metrics, resilience      |
| **v0.4.0**         | Framework           | Specialized agents, provider abstraction, configurable pipelines |
| **v0.5.0**         | Product Readiness   | Persistent sessions, security, packaging, CI/CD, observability   |
| **v1.0.0**         | Stable Framework    | Production-ready voice agent framework                           |


v0.1 Prototype Streamlit Interface

![alt text](streamlit/image.png)

---

## 📄 License

Apache 2.0