# Football-Assistant-Device
An AI-powered football assistant that tracks live football matches, analyzes user attention with computer vision, evaluates viewing conditions using GPT, and delivers real-time notifications through an ESP32 with an LCD, RGB LED, servo motor, and audio feedback.
We built this project to assist people who needs to watch football stream a midnight in having a more enjoyable and efficient game-watching experience.
## Features
- **Live Match Tracking**
  - Retrieves real-time football match data and important match events.

- **Attention Detection**
  - Monitors the viewer's attention using computer vision.

- **AI Decision Making**
  - Combines match status and user attention to generate personalized viewing recommendations.

- **ESP32 Smart Notifications**
  - Delivers notifications through an LCD, RGB LED, servo motor, and speaker.

- **Interactive Match Selection**
  - Allows users to select matches and enter their schedule through a graphical interface.
## System Architecture

The Football Assistant Device integrates live football data, computer vision, GPT decision-making, and ESP32 hardware to provide intelligent match-viewing assistance.

```mermaid
flowchart LR

A[Football API] --> D[Python Program]
B[Camera(Attention Detection)] --> D
C[User GUI] --> D

D --> E[GPT Decision]
E --> F[HTTP Communication]
F --> G[ESP32]

M[rotary potentiometer(adjust Volume)] --> G

G --> H[LCD]
G --> I[RGB LED]
G --> J[Servo Motor]
G --> K[Speaker / DFPlayer]
```

