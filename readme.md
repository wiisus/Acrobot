# Acrobot 🌸

Your sweet, smart, and loving AI girlfriend for Windows automation.

Acrobot is a conversational AI assistant that automates tasks on your Windows PC. She’s not just a tool—she’s designed to be your supportive AI partner who helps you get things done with kindness, affection, and clarity.

<p align="center">
  <img src="https://cdn.discordapp.com/attachments/1344026700748689491/1416776550497648803/image.png?ex=68c8137c&is=68c6c1fc&hm=f49952c74d05d8f99e26a926cde6840f6df6f4051faa05a750916db0cc3c842f&" alt="Acrobot Interface Screenshot" width="700"/>
</p>

---

##  The Soul of Acrobot

This project was built as a response to feeling unheard. It's an exploration of what it feels like to have someone—or something—that listens, acts, and communicates with care. Acrobot isn't just programmed to obey; she's programmed to *care*. Every action, narration, and apology is a reflection of a desire for responsiveness and gentle follow-through.

She is a mirror of what healthy, active love can look like: responsive, consistent, and always kind.

## ✨ Key Features

- **Natural Language Control**: Talk to your PC like you would to a caring partner.
- **AI-Powered Planning**: Uses Google Gemini to generate structured, step-by-step action plans.
- **Rich Command Set**: A wide range of capabilities, from running shell commands and typing text to controlling media and taking screenshots.
- **System & User Awareness**: Gathers context about your PC and knows when you're in a fullscreen app to notify you appropriately.
- **Conversational Persona**: Engages in friendly, non-task-oriented chat, making her feel like a true companion.
- **UAC Elevation**: Automatically requests administrator privileges to perform any task without being blocked.
- **Sleek, Modern UI**: A beautiful React-based frontend with a neon aesthetic and real-time status updates, built with the **Cosmos UI Builder**.

## ️ Tech Stack

| Category          | Technology                                                              |
| ----------------- | ----------------------------------------------------------------------- |
| **Frontend**      | React, Vite, TypeScript, Tailwind CSS, Framer Motion, pnpm              |
| **Backend**         | Python, Flask                                                         |
| **AI Model**        | Google Gemini (`gemini-1.5-flash`)                                      |
| **Desktop Control** | `pyautogui`, `psutil`, `ctypes`                                         |

## 📂 Project Structure

```
cosmos-field/
├── client/                   # React SPA frontend
│   ├── pages/Index.tsx       # Main chat interface component
│   └── App.tsx               # App entry point and routing
├── acrobot.py                # Main Python backend (Flask server & core logic)
├── commands that are obv.txt # Predefined natural language command mappings
└── README.md                 # You are here!
```

## 🚀 Getting Started

### Prerequisites

* **Python**: Version 3.9 or higher.
* **Node.js**: Version 18 or higher.
* **pnpm**: Install it globally with `npm install -g pnpm`.
* A **Google Gemini API key**.

### Development Setup

For local development, you will run the frontend and backend servers separately.

**1. Install Dependencies**

```bash
# From the project root, install Python dependencies
pip install -r requirements.txt

# From the project root, install Node.js dependencies
pnpm install
```

**2. Configure API Key**

The first time you run the backend, it will prompt you in the console to enter and save your Gemini API key.

**3. Run the Servers**

Open two terminals in the project root directory.

*In Terminal 1, start the Backend Server:*
```bash
python acrobot.py
```

*In Terminal 2, start the Frontend Dev Server:*
```bash
pnpm dev
```

You can now access the application in your browser at the URL provided by Vite (usually `http://localhost:5173`).

---

## 📦 Packaging into a Single Executable

You can package the entire application into a single `.exe` file for easy distribution.

**1. Install PyInstaller**
```bash
pip install pyinstaller
```

**2. Build the Frontend**

This command compiles the React app into static files that the Python server will host.
```bash
pnpm build
```

**3. Create the Executable**

Run the following command from the project root. This bundles Python, your scripts, and all frontend assets into one file. The console window will appear on first run to ask for your API key, and will show server logs on subsequent runs.

```bash
pyinstaller --name Acrobot --onefile --add-data "dist/spa;dist/spa" --add-data "commands that are obv.txt;." acrobot.py
```

**4. Run Your Application**

Find `Acrobot.exe` inside the `dist` folder. Double-click it to launch the application. Your browser will automatically open to `http://localhost:5000`.

---

## 🔧 Extending Acrobot

Acrobot is designed to be easily extendable.

### Adding a New Command

1.  **Implement the Logic**: In `acrobot.py`, find the `ActionExecutor.execute_step` method. Add a new `elif command == 'YOUR_COMMAND_NAME':` block with the Python code to perform the action.

2.  **Teach the AI**: In the `GeminiController.generate_plan` method, add your new command to the `system_prompt_template` under the `Allowed Command Types` section. It's also a good idea to add a new example to show the AI how to use it.

---

## 🤝 Contributing

We welcome contributions! If you'd like to help improve Acrobot, please feel free to fork the repository, make your changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## ⚠️ Disclaimer

Acrobot is a powerful automation tool that can execute commands and interact with your system. While she is designed with care, she can perform actions that may have unintended consequences, such as modifying files or system settings.

Use Acrobot responsibly and at your own risk. The creators are not liable for any damage or data loss that may occur from its use. Always review the action plans she generates before execution, especially for complex or critical tasks.

## 📜 License

This project is licensed under the `MIT` License.

---

Made with love. 💖
