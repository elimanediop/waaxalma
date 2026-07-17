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

**Prototype – v0.1**

The current release validates the architectural foundations of Waaxalma, including:

- AI Agent orchestration
- Speech-to-Text
- Translation
- Text-to-Speech
- Session management
- Streamlit user interface

---

## 📚 Documentation

Project documentation is available in the `docs/` directory.

- Architecture & Vision Book
- Roadmap
- Future design decisions (ADR)

---

## 🗺️ Roadmap

| Version | Goal |
|----------|------|
| v0.1 | Prototype |
| v0.2 | Voice Pipeline |
| v0.3 | Conversation Memory |
| v0.4 | Streaming |
| v0.5 | Multi-provider |
| v1.0 | First stable release |

---

## 📄 License

Apache 2.0