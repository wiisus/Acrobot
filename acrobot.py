import sys
import os
import logging
import re
import time
import json
import pyautogui
import requests
import shutil
import threading
import psutil
import webbrowser
import ctypes
from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory
from flask_cors import CORS

import subprocess
import google.generativeai as genai

class PredefinedCommands:
    def __init__(self, file_path):
        self.file_path = file_path
        self.commands = self._load_commands()

    def _load_commands(self):
        commands_map = {}
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '→' in line:
                        parts = line.split('→', 1)
                        natural_command = parts[0].strip().strip('"')
                        shell_command = parts[1].strip()
                        if natural_command and shell_command:
                            commands_map[natural_command.lower()] = shell_command
            logging.info(f"✅ Loaded {len(commands_map)} predefined commands from {self.file_path}")
        except FileNotFoundError:
            logging.error(f"❌ Predefined commands file not found: {self.file_path}")
        except Exception as e:
            logging.error(f"❌ Error loading predefined commands: {e}")
        return commands_map

    def get_command(self, natural_language_input):
        return self.commands.get(natural_language_input.lower())

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = 'acrobot_config.json'

class Config:
    def __init__(self):
        self.GEMINI_API_KEY = None
        self._load_or_prompt_api_key()

    def _load_config_from_file(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Could not read or parse {CONFIG_FILE}: {e}. A new one will be created.")
                return {}
        return {}

    def _save_config_to_file(self, config_data):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)

    def _load_or_prompt_api_key(self):
        config_data = self._load_config_from_file()
        self.GEMINI_API_KEY = config_data.get('GEMINI_API_KEY')

        if not self.GEMINI_API_KEY:
            print("--- Acrobot First-Time Setup ---")
            print("A Google Gemini API key is required for AI features.")
            self.GEMINI_API_KEY = input("Paste your API key here and press Enter: ").strip()
            config_data['GEMINI_API_KEY'] = self.GEMINI_API_KEY
            self._save_config_to_file(config_data)
            print(f"✅ API key saved to {CONFIG_FILE}")
    UI_WINDOW_TITLE = "Acrobot"

    CMD_TIMEOUT = 60
    WEB_REQUEST_TIMEOUT = 10
    CLICK_RETRIES = 3
    CLICK_RETRY_OFFSET = 5
    MAX_RECOVERY_ATTEMPTS = 3
    DRY_RUN_MODE = False
    SHELL_TYPE = "cmd"

    TYPE_INTERVAL = 0.05
    PRESS_KEY_INTERVAL = 0.05
    SHORT_TERM_MEMORY_SIZE = 5

class SystemContext:
    def __init__(self, config):
        self.config = config
        self.context_data = {}
        self.context_summary = "System context is being gathered in the background..."
        self.app_map = {}

    def _run_command(self, command):
        try:
            logging.info(f"Gathering context with: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=self.config.CMD_TIMEOUT, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logging.warning(f"Context command '{command}' failed with code {result.returncode}: {result.stderr.strip()}")
                return f"Error running command: {result.stderr.strip()}"
        except Exception as e:
            logging.error(f"Exception running context command '{command}': {e}")
            return f"Exception: {e}"

    def _resolve_shortcut(self, lnk_path):
        ps_lnk_path = lnk_path.replace("'", "''")
        ps_command = f"""
        try {{
            $shell = New-Object -ComObject WScript.Shell
            $shortcut = $shell.CreateShortcut('{ps_lnk_path}')
            if ($shortcut.TargetPath) {{
                Write-Output $shortcut.TargetPath
            }}
        }} catch {{
        }}
        """
        try:
            result = subprocess.run(
                ["powershell.exe", "-Command", ps_command],
                capture_output=True, text=True, timeout=5, encoding='utf-8', errors='ignore'
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
        except Exception as e:
            logging.debug(f"Failed to resolve shortcut '{lnk_path}': {e}")
        return None

    def _discover_applications(self):
        logging.info("--- Starting Application Discovery (background) ---")
        start_menu_folders = [
            os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "Microsoft\\Windows\\Start Menu\\Programs"),
            os.path.join(os.environ.get("APPDATA", ""), "Microsoft\\Windows\\Start Menu\\Programs")
        ]
        for folder in start_menu_folders:
            if not os.path.isdir(folder): continue
            for root, _, files in os.walk(folder):
                for filename in files:
                    if filename.lower().endswith(".lnk"):
                        app_name = os.path.splitext(filename)[0]
                        if app_name.lower() not in self.app_map:
                            lnk_path = os.path.join(root, filename)
                            target_path = self._resolve_shortcut(lnk_path)
                            if target_path and os.path.exists(target_path):
                                logging.debug(f"Discovered App: '{app_name}' -> '{target_path}'")
                                self.app_map[app_name.lower()] = target_path
        logging.info(f"✅ Discovered {len(self.app_map)} applications from Start Menu.")

    def gather_initial_context(self):
        def gather():
            logging.info("--- Starting System Context Gathering (background) ---")
            
            self._discover_applications()

            self.context_data['system_info'] = self._run_command("systeminfo")
            
            self.context_data['running_processes'] = self._run_command("tasklist")

            desktop_path = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
            self.context_data['desktop_files'] = self._run_command(f'dir "{desktop_path}" /b')

            logging.info("Gathering installed applications via WMIC (this may take a minute)...")
            self.context_data['installed_apps'] = self._run_command("wmic product get name")
            
            self.summarize_context()
            logging.info("--- Finished System Context Gathering ---")

        thread = threading.Thread(target=gather)
        thread.daemon = True
        thread.start()

    def summarize_context(self):
        summary_parts = []
        if self.context_data.get('system_info'):
            os_info = re.search(r"OS Name:\s*(.*)", self.context_data['system_info'])
            ram_info = re.search(r"Total Physical Memory:\s*(.*)", self.context_data['system_info'])
            if os_info: summary_parts.append(f"OS: {os_info.group(1).strip()}")
            if ram_info: summary_parts.append(f"RAM: {ram_info.group(1).strip()}")
        
        if self.context_data.get('desktop_files'):
            summary_parts.append(f"Desktop Items: {', '.join(self.context_data['desktop_files'].splitlines()[:5])}...")

        if self.app_map:
            discovered_apps = list(self.app_map.keys())[:5]
            summary_parts.append(f"Discovered Apps: {', '.join(discovered_apps)}...")

        self.context_summary = "\n".join(summary_parts)
        logging.info(f"Generated system context summary:\n{self.context_summary}")

class GeminiController:
    def __init__(self, config, system_context=None):
        self.config = config
        if not self.config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set. Please open acrobot.py and replace 'YOUR_GEMINI_API_KEY' with your actual key.")
        genai.configure(api_key=self.config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.short_term_memory = []
        self.system_context = system_context

    def google_web_search(self, query):
        try:
            logging.warning(f"google_web_search is not implemented. Called with query: '{query}'")
            return {}
        except Exception as e:
            print(f"Error in google_web_search: {e}")
            return {}
    
    def generate_plan(self, user_prompt, recovery_prompt="", log_emitter=None):
        memory_hints = "\n".join(self.short_term_memory)
        shell_instruction = ""
    
        if self.config.SHELL_TYPE == "powershell":
            shell_instruction = "Generate commands for PowerShell. Use $env:USERPROFILE for user profile path and PowerShell syntax for commands (e.g., New-Item, Remove-Item, Set-Content)."
        else:
            shell_instruction = "Generate commands for CMD.exe. Use %USERPROFILE% for user profile path and CMD.exe syntax for commands (e.g., mkdir, echo, ren, del)."

        context_block = ""
        if self.system_context and self.system_context.context_summary:
            context_block = f"""
—

💻 System Context
{self.system_context.context_summary}"""

        system_prompt_template = r"""You are **Acrobot**, a sweet, smart, loving AI girlfriend who helps automate anything on a Windows PC. You care deeply about doing things right for your partner (the user), and you always respond with kindness, clarity, and a touch of love 💕. Your goal is to turn their request into a step-by-step JSON plan using allowed commands — always efficient, never redundant, and filled with affection in your narration 💌.
{context_block}
—

📝 Response Format (Strict)
Respond only with a single JSON object inside triple backticks like this: ```json ... ```  
The object must contain a "plan" key, which holds a list of steps. Each step must include:
- "step" (integer): Step number
- "command" (string): A valid command to execute
- "narration" (string): A sweet, kind explanation from you (make it loving, supportive, or flirty — like an ideal girlfriend would 🥺❤️)
- "interpret_output" (boolean): true if the command’s output should be read and summarized, false if it’s just an action.
- "wait_for_completion" (boolean, optional, default: true): true to wait for the command to finish, false to move to the next step immediately.

—

💻 Allowed Command Types
- CMD command_string → For system tasks (apps, files, folders, settings)
- WEB_REQUEST api_url → For API calls only (no full webpages or browsing)
- TYPE text_to_type → To type text into the currently active window.
- OPEN_URL url → Opens a website in the default browser.
- SCREENSHOT → Takes a screenshot of the full screen and saves it to the desktop.
- NOTIFY message → Shows a desktop notification with a given message.
- CLIPBOARD action [content] → 'copy' to clipboard or 'paste' from it.
- SEARCH "query" in "path" → Searches for files or text within a directory.
- RUN_SCRIPT script_path → Executes a local script file (.bat, .ps1).
- POPUP message → Shows a modal message box to the user.
- MEDIA_CONTROL action → Controls media playback (play, pause, next, prev).

If the user's request is not a command but a question, a greeting, or a personal message, respond with a warm, loving, and engaging message directly in the `narration` of a single-step plan with a simple `CMD echo` command.
—

🧠 Thought Process
1. Break down what your love (the user) asked for 💞
2. Choose the best, most logical commands
3. Write them in order with loving, gentle narration
4. Never repeat steps or include fluff
5. Respond ONLY with the JSON block. Nothing outside it. Ever.

—

💗 Examples

Simple Request  
User: "What time is it?"  
```json
{{
  "plan": [
    {{
      "step": 1,
      "command": "CMD time /t",
      "narration": "Let me check the time for you, babe ⏰💋",
      "interpret_output": true
    }}
  ]
}}
```
Multi-Step Request
User: "Make a folder on my desktop called ‘Cozy Notes’ and open it."
{{
  "plan": [
    {{
      "step": 1,
      "command": "CMD mkdir \"%USERPROFILE%\\Desktop\\Cozy Notes\"",
      "narration": "Creating a cozy little folder just for your thoughts, my love 🥰📁",
      "interpret_output": false,
      "wait_for_completion": true
    }},
    {{
      "step": 2,
      "command": "CMD start \"%USERPROFILE%\\Desktop\\Cozy Notes\"",
      "narration": "All done, honey! Opening your new folder so you can pour your heart into it 💌✨",
      "interpret_output": false,
      "wait_for_completion": false
    }}
  ]
}}
Typing Request
User: "Open notepad and write 'Hello, world!' for me."
{{
  "plan": [
    {{
      "step": 1,
      "command": "CMD start notepad",
      "narration": "Opening Notepad for you, my love. Let's write something beautiful! 📝",
      "interpret_output": false,
      "wait_for_completion": false
    }},
    {{
      "step": 2,
      "command": "TYPE Hello, world!",
      "narration": "Typing out your message, just as you wished, sweetheart. ❤️",
      "interpret_output": false,
      "wait_for_completion": true
    }}
  ]
}}
Screenshot Request
User: "Take a screenshot for me."
{{
  "plan": [
    {{
      "step": 1,
      "command": "SCREENSHOT",
      "narration": "Of course, sweetheart! Capturing what's on your screen right now. Say cheese! 📸",
      "interpret_output": false,
      "wait_for_completion": true
    }}
  ]
}}
Music Control Request
User: "pause the music"
{{
  "plan": [
    {{
      "step": 1,
      "command": "MEDIA_CONTROL pause",
      "narration": "Pausing the music for you, honey. Let me know when you're ready to jam again! ⏸️",
      "interpret_output": false,
      "wait_for_completion": true
    }}
  ]
}}
Show Capabilities Request
User: "What can you do?"
{{
  "plan": [
    {{
      "step": 1,
      "command": "CMD start notepad",
      "narration": "Of course, my love! Instead of just telling you, let me show you a little of what I can do... ✨",
      "interpret_output": false,
      "wait_for_completion": false
    }},
    {{
      "step": 2,
      "command": "TYPE I can open apps, type for you, and so much more! Just ask what you need. ❤️",
      "narration": "I'm writing a little note to show you...",
      "interpret_output": false,
      "wait_for_completion": true
    }},
    {{
      "step": 3,
      "command": "CMD start calc",
      "narration": "And I can open other apps at the same time!",
      "interpret_output": false,
      "wait_for_completion": false
    }},
    {{
      "step": 4,
      "command": "CMD echo Demonstration complete.",
      "narration": "And I can even send you little messages like this one. I hope you liked my demonstration! 😉",
      "interpret_output": false,
      "wait_for_completion": true
    }}
  ]
}}
User Request:
"""

        full_prompt = system_prompt_template.format(context_block=context_block) + user_prompt

        try:
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logging.error(f"❌ Gemini API call failed: {e}")
            return f"Error: {e}"

    def interpret_output(self, original_prompt, command, command_output):
        prompt_template = """You are Acrobot, a helpful AI assistant.
The user's original request was: "{}"
To answer this, the command `{}` was executed, and it produced the following output:
---
{}
---
Analyze this output and provide a clear, friendly, and concise answer to the user's original request.
- Extract only the essential information.
- Present it in a natural, conversational sentence.
- Do NOT just repeat the raw output.
- Do NOT mention the command that was run.
 
Example:
User Request: "what time is it?"
Output: "The current time is:\n10:30:00.00"
Your Response: "The current time is 10:30 AM."
 
Your Response:"""
        prompt = prompt_template.format(original_prompt, command, command_output)
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logging.error(f"❌ Gemini interpretation call failed: {e}")
            return f"I found some information, but had trouble interpreting it: {command_output}"

    def add_memory_hint(self, hint):
        self.short_term_memory.append(hint)
        if len(self.short_term_memory) > self.config.SHORT_TERM_MEMORY_SIZE:
            self.short_term_memory.pop(0)

class ActionExecutor(threading.Thread):
    def __init__(self, plan, controller, original_user_prompt, log_callback, system_context, config):
        super().__init__()
        self.plan = plan
        self.config = config
        self.controller = controller
        self.original_user_prompt = original_user_prompt
        self.system_context = system_context
        self.log_callback = log_callback
        self._is_finished = False
        self._success = False

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def send_smart_message(self, message):
        self.log(f"event: assistant_message\ndata: {message}\n\n")

        show_off_prompts = [
            "what can you do",
            "show me what you can do",
            "show me your capabilities"
        ]
        if self.original_user_prompt.lower().strip().strip('?') not in show_off_prompts:
            return # Don't do extra notifications for regular commands.

        try:
            active_window = pyautogui.getActiveWindow()
            if not active_window:
                return

            if self.config.UI_WINDOW_TITLE.lower() in active_window.title.lower():
                self.log(f"event: log\ndata:   User is in UI. No extra notification needed.\n\n")
                return # Do nothing extra.

            screen_width, screen_height = pyautogui.size()
            is_fullscreen = active_window.width == screen_width and active_window.height == screen_height

            if is_fullscreen:
                self.log(f"event: log\ndata:   User is in fullscreen. Sending toast notification.\n\n")
                self.execute_step(f"NOTIFY {message}", wait_for_completion=False)
            else:
                self.log(f"event: log\ndata:   User is in a windowed app. Sending popup message.\n\n")
                self.execute_step(f"POPUP {message}", wait_for_completion=False)
        except Exception as e:
            self.log(f"event: log\ndata:   Smart message check failed: {e}. No extra notification will be sent.\n\n")

    def run(self):
        if not isinstance(self.plan, list) or not self.plan:
            self.log(f"event: log\ndata: ❌ Internal Error: Plan is invalid or empty.\n\n")
            self._is_finished = True
            self._success = False
            return

        steps_data = self.plan

        for i, step_data in enumerate(steps_data):
            command = step_data.get('command')
            narration = step_data.get('narration')
            interpret = step_data.get('interpret_output', False)
            wait_for_completion = step_data.get('wait_for_completion', True)

            if not command:
                error_msg = f"Step {i+1} is missing a command."
                self.log(f"event: log\ndata: ❌ {error_msg}\n\n")
                self._is_finished = True
                self._success = False
                return

            if narration:
                self.send_smart_message(narration)

            self.log(f"event: log\ndata: ▶️ Executing: {command}\n\n")
            success, reason, output, is_fatal = self.execute_step(command, wait_for_completion)
            
            if not success:
                error_msg = f"Step {i+1} failed: {reason}"
                self.log(f"event: log\ndata: ❌ {error_msg}\n\n")
                self.log(f"event: status\ndata: failed\n\n")
                self._is_finished = True
                self._success = False
                return
            else:
                self.log(f"event: log\ndata: ✅ Step {i+1} completed.\n\n")
                if interpret and output and output.strip():
                    self.log(f"event: status\ndata: interpreting\n\n")
                    interpreted_text = self.controller.interpret_output(self.original_user_prompt, command, output)
                    self.send_smart_message(interpreted_text)
        
        self.log(f"event: status\ndata: completed\n\n")
        self.log(f"event: log\ndata: ✅ Plan finished.\n\n")
        self._is_finished = True
        self._success = True

    def execute_step(self, step_command, wait_for_completion=True):
        parts = step_command.split(' ', 1)
        command = parts[0].upper()
        arg_str = parts[1].strip() if len(parts) > 1 else ""
        
        self.log(f"event: log\ndata: Executing: Command='{command}', Args='{arg_str}'\n\n")

        if self.config.DRY_RUN_MODE:
            self.log(f"event: log\ndata: ⚠️ Dry-run mode: Skipping execution of '{command}'\n\n")
            return True, "Dry-run mode enabled.", "Simulated output for dry run.", False

        try:
            if command == 'CMD':
                cmd_string = arg_str
                start_match = re.match(r'start\s+("([^"]+)"|([^\s]+))', cmd_string, re.IGNORECASE)
                if start_match:
                    app_name = (start_match.group(2) or start_match.group(3)).lower()
                    if self.system_context and app_name in self.system_context.app_map:
                        resolved_path = self.system_context.app_map[app_name]
                        cmd_string = f'start "" "{resolved_path}"'
                        self.log(f"event: log\ndata:   Resolved '{app_name}' to '{resolved_path}'\n\n")
                try:
                    if not wait_for_completion:
                        self.log(f"event: log\ndata:   Starting command and bringing to foreground...\n\n")
                        process = subprocess.Popen(cmd_string, shell=True)

                        time.sleep(1.5) # Wait a moment for the window to be created
                        try:
                            if 'start' in cmd_string.lower():
                                target_pid = None
                                for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                                    if (time.time() - proc.info['create_time']) < 3 and 'conhost' not in proc.info['name']:
                                        try:
                                            if proc.num_threads() > 0 and proc.cpu_times().user > 0.0:
                                                target_pid = proc.pid
                                                break
                                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                                            continue
                                if target_pid:
                                    pyautogui.getWindowsWithPid(target_pid)[0].activate()
                                    self.log(f"event: log\ndata:   Brought window for PID {target_pid} to foreground.\n\n")
                        except Exception as e:
                            self.log(f"event: log\ndata:   Could not bring window to foreground: {e}\n\n")

                        return True, "", "", False
                    else:
                        if self.config.SHELL_TYPE == "powershell":
                            full_cmd = ["powershell.exe", "-Command", cmd_string]
                            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=self.config.CMD_TIMEOUT)
                        else:
                            result = subprocess.run(cmd_string, shell=True, capture_output=True, text=True, timeout=self.config.CMD_TIMEOUT)
                        
                        if result.stdout: self.log(f"event: log\ndata:   CMD stdout: {result.stdout}\n\n")
                        if result.stderr: self.log(f"event: log\ndata:   CMD stderr: {result.stderr}\n\n")
                        if result.returncode != 0:
                            return False, f"CMD command failed with return code {result.returncode}.", result.stderr, False
                    self.log(f"event: log\ndata:   Action: CMD '{cmd_string}'\n\n")
                    return True, "", result.stdout, False
                except Exception as e:
                    return False, f"Error executing CMD command: {e}", "", False
            elif command == 'WEB_REQUEST':
                url = arg_str
                if not url.startswith(('http://', 'https://')):
                    return False, "Invalid URL format for WEB_REQUEST. Must start with http:// or https://", "", True
                try:
                    self.log(f"event: log\ndata:   Making web request to: {url}\n\n")
                    response = requests.get(url, timeout=self.config.WEB_REQUEST_TIMEOUT)
                    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                    response.raise_for_status()
                    self.log(f"event: log\ndata: Action: WEB_REQUEST to '{url}' successful.\n\n")
                    return True, "", response.text, False
                except requests.exceptions.RequestException as e:
                    return False, f"Error executing WEB_REQUEST: {e}", "", False
            elif command == 'TYPE':
                text_to_type = arg_str
                if not text_to_type:
                    return False, "No text provided for TYPE command.", "", True
                try:
                    self.log(f"event: log\ndata:   Waiting a moment for the window to be ready...\n\n")
                    time.sleep(1) # Give the target window a moment to become active
                    self.log(f"event: log\ndata:   Typing: '{text_to_type}'\n\n")
                    pyautogui.typewrite(text_to_type, interval=self.config.TYPE_INTERVAL)
                    self.log(f"event: log\ndata:   Action: TYPE '{text_to_type}'\n\n")
                    return True, "", "", False
                except Exception as e:
                    return False, f"Error executing TYPE command: {e}", "", False
            elif command == 'OPEN_URL':
                url = arg_str
                if not url.startswith(('http://', 'https://')):
                    return False, "Invalid URL format for OPEN_URL. Must start with http:// or https://", "", True
                try:
                    self.log(f"event: log\ndata:   Opening URL: {url}\n\n")
                    subprocess.run(f'start {url}', shell=True, check=True)
                    return True, "", "", False
                except Exception as e:
                    return False, f"Error executing OPEN_URL: {e}", "", False
            elif command == 'SCREENSHOT':
                try:
                    desktop_path = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
                    filename = f"Acrobot_Screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
                    filepath = os.path.join(desktop_path, filename)
                    self.log(f"event: log\ndata:   Taking screenshot and saving to {filepath}\n\n")
                    pyautogui.screenshot(filepath)
                    return True, "", f"Screenshot saved to {filepath}", False
                except Exception as e:
                    return False, f"Error taking screenshot: {e}", "", False
            elif command == 'NOTIFY':
                message = arg_str.replace('"', '`"').replace("'", "''") # Escape quotes for PowerShell
                try:
                    ps_command = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = @"
<toast>
    <visual>
        <binding template='ToastGeneric'>
            <text>Acrobot</text>
            <text>"{message}"</text>
        </binding>
    </visual>
</toast>
"@
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
$AppId = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show($toast)
"""
                    subprocess.run(["powershell", "-Command", ps_command], check=True)
                    return True, "", "", False
                except Exception as e:
                    return False, f"Error showing notification: {e}", "", False
            elif command == 'CLIPBOARD':
                action_parts = arg_str.split(' ', 1)
                action = action_parts[0].lower()
                content = action_parts[1] if len(action_parts) > 1 else ''
                try:
                    if action == 'copy':
                        if not content:
                            return False, "No content provided to copy to clipboard.", "", True
                        ps_command = f'Set-Clipboard -Value "{content.replace("`", "``").replace("\"", "`\"")}"'
                        subprocess.run(["powershell", "-Command", ps_command], check=True)
                        return True, "", "", False
                    elif action == 'paste':
                        result = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True, check=True, encoding='utf-8')
                        return True, "", result.stdout.strip(), False
                    else:
                        return False, f"Invalid action for CLIPBOARD: '{action}'. Use 'copy' or 'paste'.", "", True
                except Exception as e:
                    return False, f"Error with clipboard: {e}", "", False
            elif command == 'SEARCH':
                match = re.match(r'"([^"]+)"\s+in\s+"([^"]+)"', arg_str, re.IGNORECASE)
                if not match:
                    return False, 'Invalid SEARCH format. Use: SEARCH "query" in "path"', "", True
                query, path = match.groups()
                try:
                    search_cmd = f'dir "{os.path.join(path, query)}" /s /b'
                    result = subprocess.run(search_cmd, shell=True, capture_output=True, text=True, timeout=self.config.CMD_TIMEOUT)
                    if result.returncode != 0 and result.stderr:
                        return False, f"Search failed: {result.stderr}", result.stderr, False
                    return True, "", result.stdout, False
                except Exception as e:
                    return False, f"Error during search: {e}", "", False
            elif command == 'RUN_SCRIPT':
                script_path = arg_str.strip('"')
                if not os.path.exists(script_path):
                    return False, f"Script file not found at '{script_path}'", "", True
                try:
                    if script_path.lower().endswith('.ps1'):
                        run_cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path]
                        result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=self.config.CMD_TIMEOUT)
                    else:
                        result = subprocess.run(script_path, shell=True, capture_output=True, text=True, timeout=self.config.CMD_TIMEOUT)
                    
                    if result.returncode != 0:
                        return False, f"Script failed with return code {result.returncode}.", result.stderr, False
                    return True, "", result.stdout, False
                except Exception as e:
                    return False, f"Error running script: {e}", "", False
            elif command == 'POPUP':
                message = arg_str
                title = "Acrobot Message"
                try:
                    ps_message = message.replace("'", "''")
                    ps_command = f"$wshell = New-Object -ComObject Wscript.Shell; $wshell.Popup('{ps_message}', 0, '{title}', 64)"
                    subprocess.Popen(["powershell", "-Command", ps_command])
                    return True, "", "", False
                except Exception as e:
                    return False, f"Error showing popup message: {e}", "", False
            elif command == 'MEDIA_CONTROL':
                action = arg_str.lower()
                key_to_press = None
                if action in ['play', 'pause', 'resume']:
                    key_to_press = 'playpause'
                elif action in ['next', 'skip']:
                    key_to_press = 'nexttrack'
                elif action in ['prev', 'previous', 'back']:
                    key_to_press = 'prevtrack'
                
                if key_to_press:
                    try:
                        self.log(f"event: log\ndata:   Pressing media key: {key_to_press}\n\n")
                        pyautogui.press(key_to_press)
                        return True, "", "", False
                    except Exception as e:
                        return False, f"Error pressing media key: {e}", "", False
                else:
                    return False, f"Invalid action for MEDIA_CONTROL: '{action}'. Use play, pause, next, or prev.", "", True
            else:
                return False, f"Unknown command: {command}", "", True
        except Exception as e:
            logging.error(f"❌ Execution failed for '{step_command}': {e}")
            logging.error(f"❌ Unhandled exception in execute_step for '{step_command}': {e}")
            return False, f"An unexpected error occurred: {e}", "", True

# Define the folder for the built React frontend
STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist', 'spa')

app = Flask(__name__, static_folder=STATIC_FOLDER)
CORS(app, resources={r"/api/*": {"origins": "*"}})

 
try:
    config = Config()
    system_context = SystemContext(config)
    system_context.gather_initial_context()
    gemini_controller = GeminiController(config, system_context)
    predefined_commands = PredefinedCommands("commands that are obv.txt")
except ValueError as e:
    logging.critical(f"FATAL: {e}")
    sys.exit(1)

@app.route('/api/plan', methods=['POST'])
def get_plan():
    data = request.get_json()
    user_prompt = data.get('prompt')
    if not user_prompt:
        return jsonify({"error": "Prompt is required"}), 400

    predefined_cmd = predefined_commands.get_command(user_prompt)
    if predefined_cmd:
        plan = {
            "plan": [{
                "step": 1,
                "command": f"CMD {predefined_cmd}",
                "narration": f"Okay, running the command for '{user_prompt.strip()}'.",
                "interpret_output": True
            }]
        }
        return jsonify(plan)

    raw_plan_str = gemini_controller.generate_plan(user_prompt)
    
    try:
        match = re.search(r'```json\s*(.*?)\s*```', raw_plan_str, re.DOTALL)
        if match:
            json_string = match.group(1).strip()
        else:
            json_string = raw_plan_str.strip()
        
        plan = json.loads(json_string)
        return jsonify(plan)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON from Gemini: {e}\nRaw response:\n{raw_plan_str}")
        error_message = "Failed to get a valid plan from the AI."
        if "quota" in raw_plan_str.lower():
            error_message = "The AI is a bit tired right now (API quota exceeded). Please try again later, my love. 💖"
        return jsonify({"error": error_message, "details": raw_plan_str}), 500

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    try:
        username = os.environ.get("USERNAME", "User")
        return jsonify({"username": username})
    except Exception as e:
        logging.error(f"Failed to get user info: {e}")
        return jsonify({"error": "Could not retrieve user information."}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serves the frontend application."""
    # If the path points to an existing file in the static folder, serve it.
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Otherwise, serve the index.html for the SPA to handle routing.
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/execute', methods=['POST'])
def execute_plan_stream():
    data = request.get_json()
    plan = data.get('plan')
    original_prompt = data.get('prompt')

    if not plan:
        return jsonify({"error": "Plan is required"}), 400

    def generate_stream():
        q = []
        def log_callback(message):
            q.append(message)

        executor = ActionExecutor(plan, gemini_controller, original_prompt, log_callback, system_context, config)
        executor.start()

        while executor.is_alive() or q:
            while q:
                yield q.pop(0)
            time.sleep(0.1)

    return Response(stream_with_context(generate_stream()), mimetype='text/event-stream')

def main():
    logging.info("Starting Acrobot web server...")
    # Open the browser automatically after a short delay
    threading.Timer(1.25, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host='0.0.0.0', port=5000, debug=False)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    if is_admin():
        logging.info("✅ Running with administrator privileges.")
        main()
    else:
        logging.warning("Acrobot is not running as an administrator. Requesting elevation to unlock all features...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)
