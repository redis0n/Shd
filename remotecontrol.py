# remote_control_ultimate.py - Полный контроль над ПК
from flask import Flask, request, render_template_string, Response, jsonify
from pynput.keyboard import Controller as KeyboardController, Key, Listener as KeyboardListener
from pynput.mouse import Controller as MouseController, Button, Listener as MouseListener
import platform
import threading
import subprocess
import os
import sys
import mss
import mss.tools
import io
from PIL import Image, ImageDraw, ImageFont
import base64
import psutil
import time
import json
import datetime
import shutil
import ctypes
import winreg
import winshell
from cryptography.fernet import Fernet
import socket
import traceback

app = Flask(__name__)
keyboard = KeyboardController()
mouse = MouseController()

# Глобальные переменные
mouse_blocked = False
keyboard_blocked = False
blocked_keys = set()
drawing_mode = False
drawing_lines = []
current_drawing_color = "#FF0000"
screen_width = 1920
screen_height = 1080
log_entries = []
key_logs = []
app_logs = []

# Получение размеров экрана
try:
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
except:
    pass

# HTML интерфейс (огромный)
HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Ultimate Remote Control</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: #00ff41;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(0,0,0,0.5);
            border-radius: 15px;
            border: 1px solid #00ff41;
            box-shadow: 0 0 20px rgba(0,255,65,0.3);
        }
        
        .tabs {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 20px;
        }
        
        .tab {
            padding: 12px 24px;
            background: rgba(26,26,26,0.9);
            cursor: pointer;
            border-radius: 8px 8px 0 0;
            transition: all 0.3s;
            border: 1px solid #00ff41;
            border-bottom: none;
            font-weight: bold;
        }
        
        .tab:hover {
            background: #00ff41;
            color: #0a0a0a;
            transform: translateY(-2px);
        }
        
        .tab.active {
            background: #00ff41;
            color: #0a0a0a;
            box-shadow: 0 0 15px rgba(0,255,65,0.5);
        }
        
        .content {
            background: rgba(17,17,17,0.95);
            padding: 25px;
            border-radius: 0 10px 10px 10px;
            display: none;
            border: 1px solid #00ff41;
            backdrop-filter: blur(5px);
        }
        
        .content.active {
            display: block;
            animation: fadeIn 0.5s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .card {
            background: rgba(30,30,40,0.8);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #00ff41;
            transition: transform 0.3s;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,255,65,0.2);
        }
        
        .card h3 {
            margin-bottom: 15px;
            color: #00ff41;
            border-bottom: 2px solid #00ff41;
            display: inline-block;
        }
        
        button {
            background: linear-gradient(135deg, #00ff41 0%, #00cc33 100%);
            color: #0a0a0a;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            cursor: pointer;
            font-weight: bold;
            border-radius: 6px;
            transition: all 0.2s;
            font-family: monospace;
            font-size: 14px;
        }
        
        button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 10px rgba(0,255,65,0.5);
        }
        
        button.danger {
            background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
            color: white;
        }
        
        button.warning {
            background: linear-gradient(135deg, #ffaa00 0%, #cc8800 100%);
        }
        
        input, textarea, select {
            background: #1a1a1a;
            color: #00ff41;
            border: 1px solid #00ff41;
            padding: 10px;
            margin: 5px;
            border-radius: 6px;
            font-family: monospace;
            width: calc(100% - 20px);
        }
        
        .log {
            background: #0a0a0a;
            padding: 12px;
            height: 300px;
            overflow-y: auto;
            font-size: 11px;
            border: 1px solid #00ff41;
            border-radius: 8px;
            margin-top: 20px;
            font-family: monospace;
        }
        
        .log-entry {
            padding: 3px;
            border-bottom: 1px solid #1a1a1a;
            font-size: 11px;
        }
        
        .log-entry.info { color: #00ff41; }
        .log-entry.warning { color: #ffaa00; }
        .log-entry.error { color: #ff4444; }
        .log-entry.key { color: #8888ff; }
        
        .screen-container {
            text-align: center;
            position: relative;
        }
        
        #screenCanvas {
            max-width: 100%;
            border: 2px solid #00ff41;
            border-radius: 8px;
            cursor: crosshair;
            background: #000;
        }
        
        .drawing-tools {
            margin-top: 10px;
            padding: 10px;
            background: rgba(0,0,0,0.5);
            border-radius: 8px;
        }
        
        .color-preview {
            width: 30px;
            height: 30px;
            border-radius: 5px;
            display: inline-block;
            margin: 5px;
            cursor: pointer;
            border: 2px solid white;
        }
        
        .file-browser {
            max-height: 400px;
            overflow-y: auto;
            background: #0a0a0a;
            padding: 10px;
            border-radius: 8px;
        }
        
        .file-item {
            padding: 5px;
            margin: 2px;
            cursor: pointer;
            border-radius: 4px;
        }
        
        .file-item:hover {
            background: #00ff41;
            color: #0a0a0a;
        }
        
        .process-item {
            padding: 8px;
            margin: 5px;
            background: #0a0a0a;
            cursor: pointer;
            border-radius: 5px;
            border-left: 3px solid #00ff41;
        }
        
        .process-item:hover {
            background: #1a1a1a;
            transform: translateX(5px);
        }
        
        .shortcut-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 10px;
        }
        
        .shortcut-btn {
            background: #2a2a2a;
            padding: 10px;
            text-align: center;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        }
        
        .shortcut-btn:hover {
            background: #00ff41;
            color: black;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .recording {
            animation: pulse 1s infinite;
            color: #ff4444;
        }
        
        .status-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-left: 10px;
        }
        
        .status-badge.active {
            background: #00ff41;
            color: black;
        }
        
        .status-badge.blocked {
            background: #ff4444;
            color: white;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            .tab {
                padding: 8px 12px;
                font-size: 12px;
            }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎮 ULTIMATE REMOTE CONTROL 🎮</h1>
        <p>Полный контроль над компьютером | <span id="status">🟢 Подключен</span></p>
    </div>
    
    <div class="tabs">
        <div class="tab active" onclick="showTab('keyboard')">⌨️ Клавиатура</div>
        <div class="tab" onclick="showTab('mouse')">🖱️ Тачпад</div>
        <div class="tab" onclick="showTab('screen')">📺 Экран</div>
        <div class="tab" onclick="showTab('drawing')">🎨 Рисование</div>
        <div class="tab" onclick="showTab('system')">⚙️ Система</div>
        <div class="tab" onclick="showTab('files')">📁 Файлы</div>
        <div class="tab" onclick="showTab('monitoring')">👁️ Мониторинг</div>
        <div class="tab" onclick="showTab('advanced')">🔧 Продвинутый</div>
    </div>

    <!-- Клавиатура -->
    <div id="keyboard" class="content active">
        <div class="grid">
            <div class="card">
                <h3>⌨️ Управление клавиатурой</h3>
                <div id="keyboardStatus">
                    <button onclick="toggleKeyboardBlock()" id="kbToggleBtn" class="warning">
                        🚫 Заблокировать клавиатуру
                    </button>
                    <button onclick="clearBlockedKeys()">🗑️ Снять блокировку всех клавиш</button>
                </div>
                <div style="margin-top: 15px;">
                    <h4>Заблокировать конкретные клавиши:</h4>
                    <input type="text" id="blockKeyInput" placeholder="Клавиша (a, b, enter, space...)">
                    <button onclick="blockSpecificKey()">🚫 Заблокировать</button>
                </div>
                <div style="margin-top: 15px;">
                    <h4>Отправить текст:</h4>
                    <textarea id="textToSend" rows="3" placeholder="Введите текст..."></textarea>
                    <button onclick="sendText()">📝 Отправить</button>
                </div>
            </div>
            
            <div class="card">
                <h3>🎹 Виртуальная клавиатура</h3>
                <div style="display: grid; grid-template-columns: repeat(10, 1fr); gap: 5px;">
                    <div class="shortcut-btn" onclick="sendKey('1')">1</div>
                    <div class="shortcut-btn" onclick="sendKey('2')">2</div>
                    <div class="shortcut-btn" onclick="sendKey('3')">3</div>
                    <div class="shortcut-btn" onclick="sendKey('4')">4</div>
                    <div class="shortcut-btn" onclick="sendKey('5')">5</div>
                    <div class="shortcut-btn" onclick="sendKey('6')">6</div>
                    <div class="shortcut-btn" onclick="sendKey('7')">7</div>
                    <div class="shortcut-btn" onclick="sendKey('8')">8</div>
                    <div class="shortcut-btn" onclick="sendKey('9')">9</div>
                    <div class="shortcut-btn" onclick="sendKey('0')">0</div>
                    <div class="shortcut-btn" onclick="sendKey('q')">q</div>
                    <div class="shortcut-btn" onclick="sendKey('w')">w</div>
                    <div class="shortcut-btn" onclick="sendKey('e')">e</div>
                    <div class="shortcut-btn" onclick="sendKey('r')">r</div>
                    <div class="shortcut-btn" onclick="sendKey('t')">t</div>
                    <div class="shortcut-btn" onclick="sendKey('y')">y</div>
                    <div class="shortcut-btn" onclick="sendKey('u')">u</div>
                    <div class="shortcut-btn" onclick="sendKey('i')">i</div>
                    <div class="shortcut-btn" onclick="sendKey('o')">o</div>
                    <div class="shortcut-btn" onclick="sendKey('p')">p</div>
                    <div class="shortcut-btn" onclick="sendKey('a')">a</div>
                    <div class="shortcut-btn" onclick="sendKey('s')">s</div>
                    <div class="shortcut-btn" onclick="sendKey('d')">d</div>
                    <div class="shortcut-btn" onclick="sendKey('f')">f</div>
                    <div class="shortcut-btn" onclick="sendKey('g')">g</div>
                    <div class="shortcut-btn" onclick="sendKey('h')">h</div>
                    <div class="shortcut-btn" onclick="sendKey('j')">j</div>
                    <div class="shortcut-btn" onclick="sendKey('k')">k</div>
                    <div class="shortcut-btn" onclick="sendKey('l')">l</div>
                    <div class="shortcut-btn" onclick="sendKey('z')">z</div>
                    <div class="shortcut-btn" onclick="sendKey('x')">x</div>
                    <div class="shortcut-btn" onclick="sendKey('c')">c</div>
                    <div class="shortcut-btn" onclick="sendKey('v')">v</div>
                    <div class="shortcut-btn" onclick="sendKey('b')">b</div>
                    <div class="shortcut-btn" onclick="sendKey('n')">n</div>
                    <div class="shortcut-btn" onclick="sendKey('m')">m</div>
                    <div class="shortcut-btn" onclick="sendKey('space')">Space</div>
                    <div class="shortcut-btn" onclick="sendKey('enter')">Enter</div>
                    <div class="shortcut-btn" onclick="sendKey('backspace')">Backspace</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Тачпад -->
    <div id="mouse" class="content">
        <div class="grid">
            <div class="card">
                <h3>🖱️ Управление мышью</h3>
                <button onclick="toggleMouseBlock()" id="mouseToggleBtn" class="warning">
                    🚫 Заблокировать мышь
                </button>
                <div class="touchpad" id="touchpad"
                     style="width: 100%; height: 400px; background: #1a1a1a; border: 3px solid #00ff41; border-radius: 12px; margin-top: 15px; cursor: crosshair;"
                     onmousemove="mouseMove(event)"
                     onclick="mouseClick('left')"
                     oncontextmenu="mouseClick('right'); return false">
                </div>
                <div style="margin-top: 10px;">
                    <button onclick="mouseClick('left')">🖱️ Левый</button>
                    <button onclick="mouseClick('right')">🖱️ Правый</button>
                    <button onclick="mouseClick('middle')">🖱️ Средний</button>
                    <button onclick="mouseClick('double')">🖱️ Двойной</button>
                </div>
                <div>
                    <button onclick="sendScroll('up')">⬆️ Вверх</button>
                    <button onclick="sendScroll('down')">⬇️ Вниз</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Экран -->
    <div id="screen" class="content">
        <div class="card">
            <h3>📺 Просмотр экрана</h3>
            <div class="screen-container">
                <canvas id="screenCanvas" width="800" height="600"></canvas>
                <div style="margin-top: 10px;">
                    <button onclick="startScreenCapture()">▶️ Запустить захват</button>
                    <button onclick="stopScreenCapture()">⏹️ Остановить</button>
                    <button onclick="captureScreenOnce()">📸 Скриншот</button>
                    <select id="quality">
                        <option value="30">Низкое (30%)</option>
                        <option value="60">Среднее (60%)</option>
                        <option value="90" selected>Высокое (90%)</option>
                    </select>
                    <select id="interval">
                        <option value="200">Быстро (0.2с)</option>
                        <option value="500" selected>Нормально (0.5с)</option>
                        <option value="1000">Медленно (1с)</option>
                    </select>
                </div>
            </div>
        </div>
    </div>

    <!-- Рисование -->
    <div id="drawing" class="content">
        <div class="card">
            <h3>🎨 Рисование на экране</h3>
            <button onclick="toggleDrawing()" id="drawingToggleBtn">✏️ Включить рисование</button>
            <button onclick="clearDrawing()">🗑️ Очистить рисунок</button>
            <div class="drawing-tools">
                <h4>Цвет:</h4>
                <div class="color-preview" style="background: #FF0000;" onclick="setDrawingColor('#FF0000')"></div>
                <div class="color-preview" style="background: #00FF00;" onclick="setDrawingColor('#00FF00')"></div>
                <div class="color-preview" style="background: #0000FF;" onclick="setDrawingColor('#0000FF')"></div>
                <div class="color-preview" style="background: #FFFF00;" onclick="setDrawingColor('#FFFF00')"></div>
                <div class="color-preview" style="background: #FF00FF;" onclick="setDrawingColor('#FF00FF')"></div>
                <div class="color-preview" style="background: #00FFFF;" onclick="setDrawingColor('#00FFFF')"></div>
                <div class="color-preview" style="background: #FFFFFF;" onclick="setDrawingColor('#FFFFFF')"></div>
                <input type="color" id="customColor" onchange="setDrawingColor(this.value)">
            </div>
            <canvas id="drawingCanvas" style="display: none;"></canvas>
        </div>
    </div>

    <!-- Система -->
    <div id="system" class="content">
        <div class="grid">
            <div class="card">
                <h3>🔋 Управление питанием</h3>
                <button onclick="systemAction('shutdown')" class="danger">⛔ Выключить</button>
                <button onclick="systemAction('restart')" class="danger">🔄 Перезагрузить</button>
                <button onclick="systemAction('sleep')">😴 Сон</button>
                <button onclick="systemAction('lock')">🔒 Заблокировать</button>
                <button onclick="systemAction('logout')">🚪 Выйти</button>
            </div>
            
            <div class="card">
                <h3>📦 Управление программами</h3>
                <input type="text" id="programPath" placeholder="Путь или имя программы">
                <button onclick="openProgram()">🚀 Открыть</button>
                <input type="text" id="processName" placeholder="Имя процесса (notepad.exe)">
                <button onclick="closeProgram()">❌ Закрыть</button>
            </div>
            
            <div class="card">
                <h3>🎯 Горячие клавиши</h3>
                <div class="shortcut-grid">
                    <div class="shortcut-btn" onclick="sendHotkey('win')">Win</div>
                    <div class="shortcut-btn" onclick="sendHotkey('alt+f4')">Alt+F4</div>
                    <div class="shortcut-btn" onclick="sendHotkey('ctrl+shift+esc')">Ctrl+Shift+Esc</div>
                    <div class="shortcut-btn" onclick="sendHotkey('alt+tab')">Alt+Tab</div>
                    <div class="shortcut-btn" onclick="sendHotkey('win+r')">Win+R</div>
                    <div class="shortcut-btn" onclick="sendHotkey('win+d')">Win+D</div>
                    <div class="shortcut-btn" onclick="sendHotkey('ctrl+c')">Ctrl+C</div>
                    <div class="shortcut-btn" onclick="sendHotkey('ctrl+v')">Ctrl+V</div>
                    <div class="shortcut-btn" onclick="sendHotkey('ctrl+x')">Ctrl+X</div>
                    <div class="shortcut-btn" onclick="sendHotkey('ctrl+z')">Ctrl+Z</div>
                    <div class="shortcut-btn" onclick="sendHotkey('ctrl+y')">Ctrl+Y</div>
                    <div class="shortcut-btn" onclick="sendHotkey('ctrl+a')">Ctrl+A</div>
                </div>
                <input type="text" id="customHotkey" placeholder="Своя комбинация (ctrl+shift+esc)">
                <button onclick="sendCustomHotkey()">🔧 Отправить</button>
            </div>
            
            <div class="card">
                <h3>📊 Системная информация</h3>
                <button onclick="getSystemInfo()">🖥️ Обновить</button>
                <div id="sysInfo" style="margin-top: 10px; font-size: 12px;"></div>
            </div>
            
            <div class="card">
                <h3>📋 Список процессов</h3>
                <button onclick="listProcesses()">🔄 Обновить</button>
                <div id="processList" style="max-height: 300px; overflow-y: auto;"></div>
            </div>
            
            <div class="card">
                <h3>💬 Уведомления на экран</h3>
                <textarea id="notificationText" rows="3" placeholder="Текст уведомления..."></textarea>
                <button onclick="sendNotification()">🔔 Показать уведомление</button>
                <button onclick="sendFullscreenNotification()">📢 На весь экран (5 сек)</button>
            </div>
        </div>
    </div>

    <!-- Файлы -->
    <div id="files" class="content">
        <div class="grid">
            <div class="card">
                <h3>📁 Файловый менеджер</h3>
                <input type="text" id="filePath" placeholder="Путь (C:\\ или C:\\Windows)">
                <button onclick="browseFiles()">🔍 Обзор</button>
                <div id="fileBrowser" class="file-browser"></div>
            </div>
            
            <div class="card">
                <h3>📄 Создать/Удалить файл</h3>
                <input type="text" id="newFilePath" placeholder="Путь к новому файлу">
                <textarea id="fileContent" rows="5" placeholder="Содержимое файла..."></textarea>
                <button onclick="createFile()">📝 Создать файл</button>
                <button onclick="deleteFile()" class="danger">🗑️ Удалить файл</button>
                <button onclick="renameFile()">✏️ Переименовать</button>
            </div>
        </div>
    </div>

    <!-- Мониторинг -->
    <div id="monitoring" class="content">
        <div class="grid">
            <div class="card">
                <h3>👁️ Лог клавиатуры (нажатия пользователя)</h3>
                <button onclick="clearKeyLogs()">🗑️ Очистить лог</button>
                <button onclick="exportKeyLogs()">💾 Экспорт</button>
                <div id="keyLogs" class="log" style="height: 300px;"></div>
            </div>
            
            <div class="card">
                <h3>📱 Лог приложений (открытые программы)</h3>
                <button onclick="clearAppLogs()">🗑️ Очистить лог</button>
                <button onclick="exportAppLogs()">💾 Экспорт</button>
                <div id="appLogs" class="log" style="height: 300px;"></div>
            </div>
            
            <div class="card">
                <h3>📊 Активные процессы в реальном времени</h3>
                <button onclick="startProcessMonitoring()">▶️ Старт</button>
                <button onclick="stopProcessMonitoring()">⏹️ Стоп</button>
                <div id="activeProcesses" class="log" style="height: 200px;"></div>
            </div>
        </div>
    </div>

    <!-- Продвинутый -->
    <div id="advanced" class="content">
        <div class="grid">
            <div class="card">
                <h3>🔧 Выполнить команду</h3>
                <input type="text" id="cmdCommand" placeholder="Команда CMD">
                <button onclick="executeCommand()">⚡ Выполнить</button>
                <div id="cmdOutput" style="margin-top: 10px; background: #0a0a0a; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;"></div>
            </div>
            
            <div class="card">
                <h3>🎮 Управление Windows</h3>
                <button onclick="toggleStartup()">🔄 Добавить в автозагрузку</button>
                <button onclick="volumeControl('up')">🔊 Громкость +</button>
                <button onclick="volumeControl('down')">🔉 Громкость -</button>
                <button onclick="volumeControl('mute')">🔇 Выкл. звук</button>
                <button onclick="brightnessControl('up')">☀️ Яркость +</button>
                <button onclick="brightnessControl('down')">🌙 Яркость -</button>
            </div>
            
            <div class="card">
                <h3>🛡️ Безопасность</h3>
                <button onclick="blockUSB()">🔌 Заблокировать USB</button>
                <button onclick="unblockUSB()">🔓 Разблокировать USB</button>
                <button onclick="disableTaskManager()">🚫 Отключить диспетчер задач</button>
                <button onclick="enableTaskManager()">✅ Включить диспетчер задач</button>
            </div>
            
            <div class="card">
                <h3>📊 Системные логи</h3>
                <div id="systemLogs" class="log" style="height: 200px;"></div>
            </div>
        </div>
    </div>

    <div class="log" id="log">
        🟢 Система готова к работе
    </div>
</div>

<script>
let captureInterval = null;
let processMonitorInterval = null;
let drawingEnabled = false;
let lastX = 0, lastY = 0;

function showTab(name) {
    document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(name).classList.add('active');
    event.target.classList.add('active');
}

// Клавиатура
async function sendKey(key) {
    addLog('⌨️ Отправлена клавиша: ' + key);
    await fetch('/key', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key: key})});
}

async function sendText() {
    let text = document.getElementById('textToSend').value;
    if (text) {
        addLog('📝 Отправлен текст: ' + text.substring(0, 50));
        await fetch('/text', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text: text})});
    }
}

async function toggleKeyboardBlock() {
    let response = await fetch('/toggle_keyboard_block', {method:'POST'});
    let data = await response.json();
    let btn = document.getElementById('kbToggleBtn');
    if (data.blocked) {
        btn.innerHTML = '🔓 Разблокировать клавиатуру';
        btn.classList.add('danger');
        addLog('🚫 Клавиатура заблокирована');
    } else {
        btn.innerHTML = '🚫 Заблокировать клавиатуру';
        btn.classList.remove('danger');
        addLog('✅ Клавиатура разблокирована');
    }
}

async function blockSpecificKey() {
    let key = document.getElementById('blockKeyInput').value;
    if (key) {
        await fetch('/block_key', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key: key})});
        addLog(`🚫 Клавиша "${key}" заблокирована`);
    }
}

async function clearBlockedKeys() {
    await fetch('/clear_blocked_keys', {method:'POST'});
    addLog('✅ Блокировка всех клавиш снята');
}

// Мышь
let mouseX = 0, mouseY = 0;

function mouseMove(e) {
    let rect = document.getElementById('touchpad').getBoundingClientRect();
    let x = e.clientX - rect.left;
    let y = e.clientY - rect.top;
    if (lastX !== 0 && lastY !== 0) {
        let dx = x - lastX;
        let dy = y - lastY;
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
            fetch('/mouse', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({dx: dx, dy: dy})});
        }
    }
    lastX = x;
    lastY = y;
}

async function mouseClick(button) {
    addLog('🖱️ ' + button + ' клик');
    await fetch('/click', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({button: button})});
}

async function sendScroll(dir) {
    addLog('📜 Скролл ' + dir);
    await fetch('/scroll', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({dir: dir})});
}

async function toggleMouseBlock() {
    let response = await fetch('/toggle_mouse_block', {method:'POST'});
    let data = await response.json();
    let btn = document.getElementById('mouseToggleBtn');
    if (data.blocked) {
        btn.innerHTML = '🔓 Разблокировать мышь';
        btn.classList.add('danger');
        addLog('🚫 Мышь заблокирована');
    } else {
        btn.innerHTML = '🚫 Заблокировать мышь';
        btn.classList.remove('danger');
        addLog('✅ Мышь разблокирована');
    }
}

// Экран
let screenCanvas = document.getElementById('screenCanvas');
let ctx = screenCanvas.getContext('2d');

async function captureScreenOnce() {
    let quality = document.getElementById('quality').value;
    let response = await fetch(`/screen_capture?quality=${quality}`);
    let data = await response.json();
    if (data.image) {
        let img = new Image();
        img.onload = function() {
            screenCanvas.width = img.width;
            screenCanvas.height = img.height;
            ctx.drawImage(img, 0, 0, screenCanvas.width, screenCanvas.height);
        };
        img.src = 'data:image/jpeg;base64,' + data.image;
        addLog('📸 Скриншот получен');
    }
}

function startScreenCapture() {
    if (captureInterval) clearInterval(captureInterval);
    let interval = parseInt(document.getElementById('interval').value);
    captureInterval = setInterval(async () => {
        let quality = document.getElementById('quality').value;
        let response = await fetch(`/screen_capture?quality=${quality}`);
        let data = await response.json();
        if (data.image) {
            let img = new Image();
            img.onload = function() {
                screenCanvas.width = img.width;
                screenCanvas.height = img.height;
                ctx.drawImage(img, 0, 0, screenCanvas.width, screenCanvas.height);
            };
            img.src = 'data:image/jpeg;base64,' + data.image;
        }
    }, interval);
    addLog('▶️ Захват экрана запущен');
}

function stopScreenCapture() {
    if (captureInterval) {
        clearInterval(captureInterval);
        captureInterval = null;
        addLog('⏹️ Захват экрана остановлен');
    }
}

// Рисование
let drawingCanvas = document.getElementById('drawingCanvas');
let drawingCtx = drawingCanvas.getContext('2d');

async function toggleDrawing() {
    drawingEnabled = !drawingEnabled;
    let btn = document.getElementById('drawingToggleBtn');
    if (drawingEnabled) {
        btn.innerHTML = '✏️ Выключить рисование';
        btn.classList.add('active');
        addLog('🎨 Рисование включено');
        await fetch('/drawing/start', {method:'POST'});
    } else {
        btn.innerHTML = '✏️ Включить рисование';
        btn.classList.remove('active');
        addLog('🎨 Рисование выключено');
        await fetch('/drawing/stop', {method:'POST'});
    }
}

async function clearDrawing() {
    await fetch('/drawing/clear', {method:'POST'});
    addLog('🗑️ Рисунок очищен');
}

async function setDrawingColor(color) {
    await fetch('/drawing/color', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({color: color})});
    addLog(`🎨 Цвет изменён на ${color}`);
}

// Системные действия
async function systemAction(action) {
    if (confirm(`Вы уверены, что хотите ${action} компьютер?`)) {
        addLog(`⚠️ Выполнение: ${action}`);
        await fetch('/system_action', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action: action})});
    }
}

async function openProgram() {
    let path = document.getElementById('programPath').value;
    if (path) {
        addLog(`🚀 Открытие: ${path}`);
        await fetch('/open_program', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path: path})});
    }
}

async function closeProgram() {
    let name = document.getElementById('processName').value;
    if (name) {
        addLog(`❌ Закрытие: ${name}`);
        await fetch('/close_program', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name: name})});
    }
}

async function sendHotkey(hotkey) {
    addLog(`🔧 Комбинация: ${hotkey}`);
    await fetch('/hotkey', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({hotkey: hotkey})});
}

async function sendCustomHotkey() {
    let hotkey = document.getElementById('customHotkey').value;
    if (hotkey) {
        await sendHotkey(hotkey);
        document.getElementById('customHotkey').value = '';
    }
}

async function getSystemInfo() {
    let response = await fetch('/system_info');
    let data = await response.json();
    let info = `
        💻 ОС: ${data.os}<br>
        🖥️ Процессор: ${data.cpu}%<br>
        💾 RAM: ${data.ram}% (${data.ram_used}GB / ${data.ram_total}GB)<br>
        📀 Диск C:: ${data.disk}%<br>
        🕐 Время работы: ${data.uptime}<br>
        🌐 IP: ${data.ip}
    `;
    document.getElementById('sysInfo').innerHTML = info;
}

async function listProcesses() {
    let response = await fetch('/process_list');
    let data = await response.json();
    let html = '';
    data.processes.forEach(p => {
        html += `<div class="process-item" onclick="killProcess(${p.pid})">
                    📌 ${p.name} (PID: ${p.pid}) - CPU: ${p.cpu}% - RAM: ${p.memory}MB
                 </div>`;
    });
    document.getElementById('processList').innerHTML = html;
}

async function killProcess(pid) {
    if (confirm(`Завершить процесс ${pid}?`)) {
        addLog(`🔫 Завершение процесса PID: ${pid}`);
        await fetch('/kill_process', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({pid: pid})});
        setTimeout(() => listProcesses(), 500);
    }
}

async function sendNotification() {
    let text = document.getElementById('notificationText').value;
    if (text) {
        await fetch('/notification', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text: text, fullscreen: false})});
        addLog(`🔔 Уведомление: ${text}`);
    }
}

async function sendFullscreenNotification() {
    let text = document.getElementById('notificationText').value;
    if (text) {
        await fetch('/notification', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text: text, fullscreen: true})});
        addLog(`📢 Полноэкранное уведомление: ${text}`);
    }
}

// Файлы
async function browseFiles() {
    let path = document.getElementById('filePath').value || 'C:\\';
    let response = await fetch('/browse_files', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path: path})});
    let data = await response.json();
    let html = '';
    data.files.forEach(file => {
        let icon = file.is_dir ? '📁' : '📄';
        html += `<div class="file-item" onclick="selectFile('${file.path}')">${icon} ${file.name}</div>`;
    });
    document.getElementById('fileBrowser').innerHTML = html;
}

function selectFile(path) {
    document.getElementById('filePath').value = path;
    browseFiles();
}

async function createFile() {
    let path = document.getElementById('newFilePath').value;
    let content = document.getElementById('fileContent').value;
    if (path) {
        await fetch('/create_file', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path: path, content: content})});
        addLog(`📝 Файл создан: ${path}`);
    }
}

async function deleteFile() {
    let path = document.getElementById('newFilePath').value;
    if (path && confirm(`Удалить ${path}?`)) {
        await fetch('/delete_file', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path: path})});
        addLog(`🗑️ Файл удалён: ${path}`);
    }
}

async function renameFile() {
    let path = document.getElementById('newFilePath').value;
    let newName = prompt('Новое имя:');
    if (path && newName) {
        await fetch('/rename_file', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path: path, new_name: newName})});
        addLog(`✏️ Файл переименован: ${path} -> ${newName}`);
    }
}

// Мониторинг
async function updateKeyLogs() {
    let response = await fetch('/key_logs');
    let data = await response.json();
    let html = '';
    data.logs.forEach(log => {
        html += `<div class="log-entry key">${log.time} - [${log.key}]</div>`;
    });
    document.getElementById('keyLogs').innerHTML = html;
}

async function updateAppLogs() {
    let response = await fetch('/app_logs');
    let data = await response.json();
    let html = '';
    data.logs.forEach(log => {
        html += `<div class="log-entry info">${log.time} - 📱 ${log.app}</div>`;
    });
    document.getElementById('appLogs').innerHTML = html;
}

function clearKeyLogs() {
    fetch('/clear_key_logs', {method:'POST'});
    addLog('🗑️ Лог клавиатуры очищен');
}

function clearAppLogs() {
    fetch('/clear_app_logs', {method:'POST'});
    addLog('🗑️ Лог приложений очищен');
}

function exportKeyLogs() {
    window.open('/export_key_logs');
}

function exportAppLogs() {
    window.open('/export_app_logs');
}

function startProcessMonitoring() {
    if (processMonitorInterval) clearInterval(processMonitorInterval);
    processMonitorInterval = setInterval(async () => {
        let response = await fetch('/active_processes');
        let data = await response.json();
        let html = '';
        data.processes.slice(0, 20).forEach(p => {
            html += `<div>📌 ${p.name} - CPU: ${p.cpu}% - RAM: ${p.memory}MB</div>`;
        });
        document.getElementById('activeProcesses').innerHTML = html;
    }, 2000);
    addLog('▶️ Мониторинг процессов запущен');
}

function stopProcessMonitoring() {
    if (processMonitorInterval) {
        clearInterval(processMonitorInterval);
        processMonitorInterval = null;
        addLog('⏹️ Мониторинг процессов остановлен');
    }
}

// Продвинутые функции
async function executeCommand() {
    let cmd = document.getElementById('cmdCommand').value;
    if (cmd) {
        let response = await fetch('/execute_command', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({command: cmd})});
        let data = await response.json();
        document.getElementById('cmdOutput').innerHTML = `<pre>${data.output}</pre>`;
        addLog(`⚡ Выполнена команда: ${cmd}`);
    }
}

async function toggleStartup() {
    let response = await fetch('/toggle_startup', {method:'POST'});
    let data = await response.json();
    addLog(data.message);
}

async function volumeControl(action) {
    await fetch('/volume', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action: action})});
    addLog(`🔊 Громкость: ${action}`);
}

async function brightnessControl(action) {
    await fetch('/brightness', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action: action})});
    addLog(`☀️ Яркость: ${action}`);
}

async function blockUSB() {
    await fetch('/block_usb', {method:'POST'});
    addLog('🔌 USB устройства заблокированы');
}

async function unblockUSB() {
    await fetch('/unblock_usb', {method:'POST'});
    addLog('🔓 USB устройства разблокированы');
}

async function disableTaskManager() {
    await fetch('/disable_taskmanager', {method:'POST'});
    addLog('🚫 Диспетчер задач отключён');
}

async function enableTaskManager() {
    await fetch('/enable_taskmanager', {method:'POST'});
    addLog('✅ Диспетчер задач включён');
}

function addLog(msg) {
    let logDiv = document.getElementById('log');
    let time = new Date().toLocaleTimeString();
    logDiv.innerHTML += `<div class="log-entry info">${time} - ${msg}</div>`;
    logDiv.scrollTop = logDiv.scrollHeight;
}

// Обновление логов каждые 2 секунды
setInterval(() => {
    updateKeyLogs();
    updateAppLogs();
}, 2000);

// Инициализация
getSystemInfo();
listProcesses();
</script>
</body>
</html>
"""

# Глобальные переменные для бэкенда
mouse_blocked = False
keyboard_blocked = False
blocked_keys = set()
drawing_mode = False
drawing_lines = []
drawing_color = "#FF0000"
key_logs = []
app_logs = []
system_logs = []
process_monitor = None

# Функции для мониторинга клавиатуры
def on_press(key):
    global key_logs, keyboard_blocked, blocked_keys
    
    try:
        key_str = key.char if hasattr(key, 'char') else str(key)
        
        # Логирование
        log_entry = {
            'time': datetime.datetime.now().strftime("%H:%M:%S"),
            'key': key_str
        }
        key_logs.append(log_entry)
        if len(key_logs) > 1000:
            key_logs = key_logs[-1000:]
        
        # Блокировка клавиатуры
        if keyboard_blocked:
            return False
        
        # Блокировка конкретных клавиш
        if key_str in blocked_keys:
            return False
            
    except Exception as e:
        pass

def on_release(key):
    pass

# Функции для мониторинга приложений
def monitor_applications():
    global app_logs
    previous_processes = set()
    while True:
        try:
            current_processes = set()
            for proc in psutil.process_iter(['name']):
                try:
                    current_processes.add(proc.info['name'])
                except:
                    pass
            
            new_processes = current_processes - previous_processes
            for proc in new_processes:
                if proc and not proc.startswith('System') and not proc.startswith('svchost'):
                    log_entry = {
                        'time': datetime.datetime.now().strftime("%H:%M:%S"),
                        'app': proc
                    }
                    app_logs.append(log_entry)
                    if len(app_logs) > 500:
                        app_logs = app_logs[-500:]
            
            previous_processes = current_processes
            time.sleep(2)
        except:
            time.sleep(2)

# Запуск мониторинга
monitoring_thread = threading.Thread(target=monitor_applications, daemon=True)
monitoring_thread.start()

# Запуск слушателя клавиатуры
keyboard_listener = KeyboardListener(on_press=on_press, on_release=on_release)
keyboard_listener.daemon = True
keyboard_listener.start()

# Маршруты
@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/key', methods=['POST'])
def key_press():
    global keyboard_blocked
    if keyboard_blocked:
        return '', 403
    key = request.json.get('key')
    if key:
        try:
            send_key_to_system(key)
        except:
            pass
    return '', 204

@app.route('/text', methods=['POST'])
def type_text():
    global keyboard_blocked
    if keyboard_blocked:
        return '', 403
    text = request.json.get('text', '')
    if text:
        try:
            keyboard.type(text)
        except:
            pass
    return '', 204

@app.route('/hotkey', methods=['POST'])
def hotkey():
    global keyboard_blocked
    if keyboard_blocked:
        return '', 403
    hotkey = request.json.get('hotkey', '')
    if hotkey:
        send_hotkey(hotkey)
    return '', 204

@app.route('/mouse', methods=['POST'])
def mouse_move():
    global mouse_blocked
    if mouse_blocked:
        return '', 403
    dx = request.json.get('dx', 0)
    dy = request.json.get('dy', 0)
    try:
        x, y = mouse.position
        mouse.position = (x + dx, y + dy)
    except:
        pass
    return '', 204

@app.route('/click', methods=['POST'])
def mouse_click():
    global mouse_blocked
    if mouse_blocked:
        return '', 403
    button = request.json.get('button', 'left')
    try:
        if button == 'double':
            mouse.click(Button.left, 2)
        else:
            btn_map = {'left': Button.left, 'right': Button.right, 'middle': Button.middle}
            mouse.click(btn_map.get(button, Button.left))
    except:
        pass
    return '', 204

@app.route('/scroll', methods=['POST'])
def mouse_scroll():
    global mouse_blocked
    if mouse_blocked:
        return '', 403
    direction = request.json.get('dir', 'down')
    scroll_amount = 120 if direction == 'up' else -120
    try:
        mouse.scroll(0, scroll_amount)
    except:
        pass
    return '', 204

@app.route('/toggle_mouse_block', methods=['POST'])
def toggle_mouse_block():
    global mouse_blocked
    mouse_blocked = not mouse_blocked
    return jsonify({'blocked': mouse_blocked})

@app.route('/toggle_keyboard_block', methods=['POST'])
def toggle_keyboard_block():
    global keyboard_blocked
    keyboard_blocked = not keyboard_blocked
    return jsonify({'blocked': keyboard_blocked})

@app.route('/block_key', methods=['POST'])
def block_key():
    global blocked_keys
    key = request.json.get('key')
    if key:
        blocked_keys.add(key)
    return '', 204

@app.route('/clear_blocked_keys', methods=['POST'])
def clear_blocked_keys():
    global blocked_keys
    blocked_keys.clear()
    return '', 204

@app.route('/screen_capture')
def screen_capture():
    quality = int(request.args.get('quality', 75))
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            
            # Рисование поверх скриншота
            global drawing_lines, drawing_mode, drawing_color
            if drawing_lines:
                draw = ImageDraw.Draw(img)
                for line in drawing_lines:
                    if len(line) > 1:
                        draw.line(line, fill=drawing_color, width=3)
            
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return jsonify({'image': img_str})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/drawing/start', methods=['POST'])
def drawing_start():
    global drawing_mode
    drawing_mode = True
    return '', 204

@app.route('/drawing/stop', methods=['POST'])
def drawing_stop():
    global drawing_mode
    drawing_mode = False
    return '', 204

@app.route('/drawing/clear', methods=['POST'])
def drawing_clear():
    global drawing_lines
    drawing_lines = []
    return '', 204

@app.route('/drawing/color', methods=['POST'])
def drawing_color_change():
    global drawing_color
    drawing_color = request.json.get('color', '#FF0000')
    return '', 204

@app.route('/drawing/line', methods=['POST'])
def drawing_line():
    global drawing_lines, drawing_mode
    if drawing_mode:
        data = request.json
        x1, y1 = data.get('x1'), data.get('y1')
        x2, y2 = data.get('x2'), data.get('y2')
        drawing_lines.append([(x1, y1), (x2, y2)])
        if len(drawing_lines) > 100:
            drawing_lines = drawing_lines[-100:]
    return '', 204

@app.route('/system_action', methods=['POST'])
def system_action():
    action = request.json.get('action')
    try:
        if action == 'shutdown':
            os.system('shutdown /s /t 5')
        elif action == 'restart':
            os.system('shutdown /r /t 5')
        elif action == 'sleep':
            os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
        elif action == 'lock':
            ctypes.windll.user32.LockWorkStation()
        elif action == 'logout':
            os.system('shutdown /l')
    except:
        pass
    return '', 204

@app.route('/open_program', methods=['POST'])
def open_program():
    path = request.json.get('path', '')
    if path:
        try:
            subprocess.Popen(path, shell=True)
        except:
            pass
    return '', 204

@app.route('/close_program', methods=['POST'])
def close_program():
    name = request.json.get('name', '')
    if name:
        try:
            os.system(f'taskkill /f /im {name}')
        except:
            pass
    return '', 204

@app.route('/system_info')
def system_info():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    uptime = time.time() - psutil.boot_time()
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    
    return jsonify({
        'os': platform.system() + ' ' + platform.release(),
        'cpu': cpu,
        'ram': ram.percent,
        'ram_used': round(ram.used / (1024**3), 1),
        'ram_total': round(ram.total / (1024**3), 1),
        'disk': disk.percent,
        'uptime': f'{hours}ч {minutes}м',
        'ip': socket.gethostbyname(socket.gethostname())
    })

@app.route('/process_list')
def process_list():
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            processes.append({
                'pid': proc.info['pid'],
                'name': proc.info['name'],
                'cpu': proc.info['cpu_percent'],
                'memory': round(proc.info['memory_info'].rss / 1024 / 1024, 1)
            })
        except:
            pass
    return jsonify({'processes': sorted(processes, key=lambda x: x['cpu'], reverse=True)[:50]})

@app.route('/kill_process', methods=['POST'])
def kill_process():
    pid = request.json.get('pid')
    if pid:
        try:
            os.system(f'taskkill /f /pid {pid}')
        except:
            pass
    return '', 204

@app.route('/notification', methods=['POST'])
def send_notification():
    text = request.json.get('text', '')
    fullscreen = request.json.get('fullscreen', False)
    if text:
        try:
            if fullscreen:
                # Полноэкранное уведомление через msg
                os.system(f'msg * "{text}" /time:5')
            else:
                # Обычное уведомление
                os.system(f'msg * "{text}"')
        except:
            pass
    return '', 204

@app.route('/browse_files', methods=['POST'])
def browse_files():
    path = request.json.get('path', 'C:\\')
    files = []
    try:
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            files.append({
                'name': item,
                'path': full_path,
                'is_dir': os.path.isdir(full_path)
            })
    except:
        pass
    return jsonify({'files': files[:100]})

@app.route('/create_file', methods=['POST'])
def create_file():
    path = request.json.get('path', '')
    content = request.json.get('content', '')
    if path:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except:
            pass
    return '', 204

@app.route('/delete_file', methods=['POST'])
def delete_file():
    path = request.json.get('path', '')
    if path and os.path.exists(path):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except:
            pass
    return '', 204

@app.route('/rename_file', methods=['POST'])
def rename_file():
    path = request.json.get('path', '')
    new_name = request.json.get('new_name', '')
    if path and new_name:
        try:
            new_path = os.path.join(os.path.dirname(path), new_name)
            os.rename(path, new_path)
        except:
            pass
    return '', 204

@app.route('/key_logs')
def get_key_logs():
    return jsonify({'logs': key_logs[-100:]})

@app.route('/app_logs')
def get_app_logs():
    return jsonify({'logs': app_logs[-100:]})

@app.route('/clear_key_logs', methods=['POST'])
def clear_key_logs():
    global key_logs
    key_logs = []
    return '', 204

@app.route('/clear_app_logs', methods=['POST'])
def clear_app_logs():
    global app_logs
    app_logs = []
    return '', 204

@app.route('/export_key_logs')
def export_key_logs():
    content = "\n".join([f"{log['time']} - {log['key']}" for log in key_logs])
    return Response(content, mimetype='text/plain', headers={'Content-Disposition': 'attachment;filename=key_logs.txt'})

@app.route('/export_app_logs')
def export_app_logs():
    content = "\n".join([f"{log['time']} - {log['app']}" for log in app_logs])
    return Response(content, mimetype='text/plain', headers={'Content-Disposition': 'attachment;filename=app_logs.txt'})

@app.route('/active_processes')
def active_processes():
    processes = []
    for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
        try:
            processes.append({
                'name': proc.info['name'],
                'cpu': proc.info['cpu_percent'],
                'memory': round(proc.info['memory_info'].rss / 1024 / 1024, 1)
            })
        except:
            pass
    return jsonify({'processes': sorted(processes, key=lambda x: x['cpu'], reverse=True)[:30]})

@app.route('/execute_command', methods=['POST'])
def execute_command():
    command = request.json.get('command', '')
    output = ''
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        if not output:
            output = "Команда выполнена (нет вывода)"
    except subprocess.TimeoutExpired:
        output = "Команда превысила время выполнения (30 сек)"
    except Exception as e:
        output = f"Ошибка: {str(e)}"
    return jsonify({'output': output})

@app.route('/toggle_startup', methods=['POST'])
def toggle_startup():
    try:
        script_path = os.path.abspath(sys.argv[0])
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, "RemoteControlUltimate")
            winreg.CloseKey(key)
            return jsonify({'message': '✅ Удалено из автозагрузки'})
        except:
            winreg.SetValueEx(key, "RemoteControlUltimate", 0, winreg.REG_SZ, script_path)
            winreg.CloseKey(key)
            return jsonify({'message': '✅ Добавлено в автозагрузку'})
    except:
        return jsonify({'message': '❌ Ошибка при изменении автозагрузки'})

@app.route('/volume', methods=['POST'])
def volume_control():
    action = request.json.get('action')
    try:
        if action == 'up':
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)  # Volume Up
        elif action == 'down':
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)  # Volume Down
        elif action == 'mute':
            ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)  # Volume Mute
    except:
        pass
    return '', 204

@app.route('/brightness', methods=['POST'])
def brightness_control():
    action = request.json.get('action')
    try:
        # Используем PowerShell для изменения яркости
        if action == 'up':
            subprocess.run('powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,100)', shell=True)
        elif action == 'down':
            subprocess.run('powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,50)', shell=True)
    except:
        pass
    return '', 204

@app.route('/block_usb', methods=['POST'])
def block_usb():
    try:
        # Блокировка USB через реестр
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\USBSTOR", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, 4)
        winreg.CloseKey(key)
    except:
        pass
    return '', 204

@app.route('/unblock_usb', methods=['POST'])
def unblock_usb():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\USBSTOR", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, 3)
        winreg.CloseKey(key)
    except:
        pass
    return '', 204

@app.route('/disable_taskmanager', methods=['POST'])
def disable_taskmanager():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\System", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except:
        pass
    return '', 204

@app.route('/enable_taskmanager', methods=['POST'])
def enable_taskmanager():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\System", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "DisableTaskMgr")
        winreg.CloseKey(key)
    except:
        pass
    return '', 204

def send_key_to_system(key):
    special_keys = {
        'enter': Key.enter, 'space': Key.space, 'backspace': Key.backspace,
        'tab': Key.tab, 'escape': Key.esc, 'up': Key.up, 'down': Key.down,
        'left': Key.left, 'right': Key.right
    }
    if key in special_keys:
        keyboard.press(special_keys[key])
        keyboard.release(special_keys[key])
    elif len(key) == 1:
        keyboard.press(key)
        keyboard.release(key)
    else:
        keyboard.type(key)

def send_hotkey(hotkey_str):
    key_mapping = {
        'ctrl': Key.ctrl, 'alt': Key.alt, 'shift': Key.shift, 'win': Key.cmd,
        'tab': Key.tab, 'esc': Key.esc, 'f4': Key.f4, 'delete': Key.delete,
        'home': Key.home, 'end': Key.end
    }
    
    parts = hotkey_str.lower().split('+')
    keys = []
    for part in parts:
        if part in key_mapping:
            keys.append(key_mapping[part])
        elif len(part) == 1:
            keys.append(part)
    
    for key in keys:
        keyboard.press(key)
    for key in reversed(keys):
        keyboard.release(key)

if __name__ == '__main__':
    local_ip = socket.gethostbyname(socket.gethostname())
    
    print("="*70)
    print("🎮 ULTIMATE REMOTE CONTROL - ПОЛНЫЙ КОНТРОЛЬ НАД ПК")
    print("="*70)
    print(f"📱 Подключитесь с телефона: http://{local_ip}:5000")
    print(f"💻 Локальный доступ: http://localhost:5000")
    print("="*70)
    print("✨ ОГРОМНЫЕ ВОЗМОЖНОСТИ:")
    print("  • Блокировка мыши/клавиатуры")
    print("  • Лог всех нажатий клавиш")
    print("  • Лог открытых приложений")
    print("  • Рисование на экране")
    print("  • Управление файлами")
    print("  • Управление питанием")
    print("  • Горячие клавиши")
    print("  • Системные команды")
    print("  • И многое другое...")
    print("="*70)
    print("⚠️  Для выхода нажмите Ctrl+C")
    print("="*70)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
