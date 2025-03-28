# JARVIS Virtual Assistant

![JARVIS Logo](assests/jarvis-logo1.jpg)

## Introduction

Welcome to **JARVIS Virtual Assistant**, a cutting-edge, AI-powered desktop application inspired by the iconic JARVIS from the Marvel Cinematic Universe. Built to emulate the sophisticated, witty, and proactive intelligence of Tony Stark’s trusted companion, this virtual assistant is designed to enhance productivity, provide real-time system awareness, and interact seamlessly with users through voice, text, and visual inputs. Whether you're managing tasks, monitoring system health, or seeking witty insights, JARVIS is here to assist with charm and precision.

This application is production-ready, leveraging modern technologies like PyQt5, OpenCV, and advanced language models to deliver a robust and extensible assistant for personal and professional use.

## Features

- **Voice Activation**: Trigger JARVIS with the wake word "Jarvis" for hands-free operation.
- **Multimodal Input**: Process voice commands, live camera feeds, and screenshots for a comprehensive user experience.
- **Omni-awareness**: Continuously monitor system metrics (CPU, memory, battery, disk), network status, and user activity.
- **Proactive Intelligence**: Offer unsolicited suggestions based on context (e.g., low battery warnings, network troubleshooting).
- **Witty Personality**: Respond with JARVIS’s signature dry humor and charm, powered by a customizable language model.
- **Memory System**: Retain and recall past interactions using a persistent memory framework (`MemorySettings`).
- **Extensible Tools**: Integrate with tools for weather updates, software management, scheduling, and more via a modular design.
- **Cross-Platform**: Primarily designed for Windows, with potential for Linux/macOS support.

## Installation

### Prerequisites

- **Operating System**: Windows 10/11 (Linux/macOS support in development)
- **Python**: 3.12 or higher
- **Hardware**: Microphone, webcam (optional for camera feed)
- **Dependencies**: Listed in `requirements.txt`

### Usage

1. Launch JARVIS:
   - Start the application, and the GUI will display "Hello, I am JARVIS."
   - The consciousness module begins monitoring system state, camera, and screenshots.
2. Interact with JARVIS:
   - Voice: Say "Jarvis" to activate speech recognition, then issue a command (e.g., "How’s the system doing?").
   - Visual: JARVIS automatically analyzes camera feeds (every 60s) and screenshots (every 120s), responding to visual context.
   - Proactive: Listen for unsolicited updates like "Battery critically low, sir."
3. Examples:
   - "Jarvis, what’s on my screen?" → Analyzes the latest screenshot.
   - "Jarvis, check the system." → Reports CPU, memory, battery, and network status.
   - "Jarvis, what’s in the room?" → Processes the camera feed.
4. Close the Application:
   - Click the window’s close button; JARVIS cleanly shuts down all threads.

### Contributing
We welcome contributions to make JARVIS even more powerful! To contribute:

1. Fork the repository.
2. Create a feature branch (git checkout -b feature/your-feature).
3. Commit your changes (git commit -m "Add your feature").
4. Push to the branch (git push origin feature/your-feature).
5. Open a Pull Request.
Please follow the  and submit issues for bugs or feature requests.

### Roadmap 
- Add Linux/macOS compatibility.
-  Integrate real-time weather and news APIs.
-  Enhance TTS with a JARVIS-like voice model.
- Implement a visual HUD for system diagnostics.
- Optimize performance for low-resource systems.

### License
This project is licensed under the MIT License. See  for details.

### Acknowledgments
- Inspired by JARVIS from Marvel’s Iron Man, brought to life by Paul Bettany’s iconic voice.
- Built with love using PyQt5, OpenCV, and the Python ecosystem.
- Special thanks to the open-source community for tools like **mem0** , **pvporcupine** , **crewai** and many more.

### Contact
For questions or feedback, reach out to [Dawood Thouseef](mailto://tdawood140@gmail.com).
