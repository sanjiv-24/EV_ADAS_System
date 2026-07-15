# EV ADAS Dashboard System 🚗⚡

## Overview

The **EV ADAS Dashboard System** is an embedded systems project that integrates an **STM32F103C8T6 microcontroller** with a **Python-based graphical dashboard** to simulate an Electric Vehicle (EV) Advanced Driver Assistance System (ADAS).

The system monitors vehicle parameters in real time, detects faults, communicates over UART, and displays live information through an intuitive desktop dashboard.

---

## Features

### Embedded System (STM32)
- Real-time vehicle monitoring
- Embedded C firmware developed using STM32CubeIDE
- UART communication with PC
- Fault detection and warning generation
- Vehicle control logic implementation
- Modular software architecture

### Python Dashboard
- Live vehicle parameter visualization
- Digital instrument cluster
- Real-time fault and warning indicators
- Serial communication using PySerial
- User-friendly graphical interface

---

## Technologies Used

### Hardware
- STM32F103C8T6 (Blue Pill)
- UART Communication

### Software
- Embedded C
- STM32CubeIDE
- Python 3
- Tkinter
- PySerial
- Matplotlib

---

## Project Structure

```
EV_ADAS/
│
├── STM32_Project/      # STM32CubeIDE Project
├── Dashboard/          # Python Dashboard
│   └── ev_dashboard.py
│
├── Images/             # Screenshots
│
├── requirements.txt
│
└── README.md
```

---

## How It Works

1. The STM32 continuously monitors vehicle parameters.
2. Sensor and system data are transmitted over UART.
3. The Python dashboard receives the serial data.
4. The dashboard updates the graphical interface in real time.
5. Any detected faults are displayed immediately to the user.

---

## Installation

### Clone Repository

```bash
git clone https://github.com/<your-username>/EV_ADAS.git
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Run Dashboard

```bash
python Dashboard/ev_dashboard.py
```

---


## Future Improvements

- CAN Bus communication
- Battery Management System (BMS) integration
- GPS support
- Wireless telemetry
- Mobile application
- AI-based driver assistance features

---

## Author

**Sanjiv Sekaran M**

Electronics and Communication Engineering

GitHub: https://github.com/<sanjiv-24>

LinkedIn: https://www.linkedin.com/in/<sanjiv-sekaran-m>

---

## License

This project is intended for educational and learning purposes.
