"""
orchestrator.py — Orquestador neutro de tareas
Versión inicial, lista para personalizar.

Este script:
- Lee y administra una cola de tareas en MySQL.
- Ejecuta procesos externos según disponibilidad de CPU/concurrencia.
- Registra logs separados para desarrollador y cliente.
- Viene sin procesos predefinidos (lista vacía en TASKS).
- Incluye comentarios con ejemplos y SQL recomendado.
"""

import os
import sys
import time
import logging
import subprocess
import psutil
import mysql.connector
from mysql.connector import Error

# ==========================
# CONFIGURACIÓN GENERAL
# ==========================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "orchestrator_db"
}

MAX_GLOBAL_CONCURRENT = 3   # máximo de procesos en paralelo
CHECK_INTERVAL = 5          # segundos entre revisiones de cola

# ==========================
# LOGGING
# ==========================
# Log detallado para desarrollador
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("orchestrator_dev.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("orchestrator")

# Log simplificado para cliente (solo info básica)
client_logger = logging.getLogger("client")
client_handler = logging.FileHandler("orchestrator_client.log")
client_handler.setLevel(logging.INFO)
client_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
client_logger.addHandler(client_handler)

# ==========================
# PROCESOS REGISTRADOS
# ==========================
TASKS = {
    # Ejemplo de cómo registrar:
    # "ejemplo": {
    #     "command": "python ejemplo.py --empresa {empresa} --tipo {tipo}",
    #     "max_concurrent": 2
    # }
}

# ==========================
# BASE DE DATOS
# ==========================
def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        logger.error(f"Error conexión BD: {e}")
        return None

def fetch_pending_tasks():
    """Obtiene tareas pendientes desde la tabla."""
    conn = get_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE status='pending' ORDER BY created_at ASC")
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, status, log=""):
    """Actualiza estado de tarea."""
    conn = get_connection()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status=%s, log=%s, updated_at=NOW() WHERE id=%s",
        (status, log, task_id)
    )
    conn.commit()
    conn.close()

# ==========================
# EJECUCIÓN DE TAREAS
# ==========================
running_processes = {}

def can_run(task_name):
    """Verifica si un proceso puede correr (por concurrencia y CPU)."""
    if task_name not in TASKS:
        return False
    conf = TASKS[task_name]

    # limitar concurrencia del proceso
    current = sum(1 for t in running_processes.values() if t["name"] == task_name)
    if current >= conf.get("max_concurrent", 1):
        return False

    # limitar concurrencia global
    if len(running_processes) >= MAX_GLOBAL_CONCURRENT:
        return False

    # evitar sobrecarga de CPU (>90%)
    if psutil.cpu_percent(interval=1) > 90:
        return False

    return True

def start_task(task):
    """Inicia ejecución de una tarea."""
    task_name = task["process"]
    conf = TASKS.get(task_name)
    if not conf:
        logger.warning(f"Tarea desconocida: {task_name}")
        update_task_status(task["id"], "failed", "Proceso no registrado")
        return

    command = conf["command"].format(
        empresa=task.get("empresa", ""),
        tipo=task.get("tipo", "")
    )

    try:
        proc = subprocess.Popen(command, shell=True)
        running_processes[proc.pid] = {"proc": proc, "id": task["id"], "name": task_name}
        update_task_status(task["id"], "running")
        logger.info(f"Iniciada tarea {task['id']} ({task_name})")
        client_logger.info(f"Tarea {task['id']} iniciada ({task_name})")
    except Exception as e:
        logger.error(f"Error al iniciar tarea {task['id']}: {e}")
        update_task_status(task["id"], "failed", str(e))

def check_running():
    """Revisa tareas en ejecución y actualiza si terminaron."""
    finished = []
    for pid, info in running_processes.items():
        ret = info["proc"].poll()
        if ret is not None:  # terminó
            status = "success" if ret == 0 else "failed"
            update_task_status(info["id"], status)
            logger.info(f"Tarea {info['id']} finalizada con estado {status}")
            client_logger.info(f"Tarea {info['id']} finalizada ({status})")
            finished.append(pid)
    for pid in finished:
        del running_processes[pid]

# ==========================
# LOOP PRINCIPAL
# ==========================
def main():
    logger.info("Orquestador iniciado")
    while True:
        check_running()
        tasks = fetch_pending_tasks()
        for t in tasks:
            if can_run(t["process"]):
                start_task(t)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()

# ==========================
# SQL RECOMENDADO
# ==========================
"""
CREATE DATABASE orchestrator_db;

USE orchestrator_db;

CREATE TABLE tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    process VARCHAR(100) NOT NULL,
    empresa VARCHAR(100) DEFAULT NULL,
    tipo VARCHAR(50) DEFAULT NULL,
    status ENUM('pending','running','success','failed') DEFAULT 'pending',
    log TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL
);

-- Opcional: tabla de auditoría
CREATE TABLE task_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
"""
