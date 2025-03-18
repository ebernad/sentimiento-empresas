#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de instalación para configurar el entorno virtual con uv.
Este script automatiza la creación del entorno virtual y la instalación de dependencias.
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """Verifica que la versión de Python sea compatible."""
    if sys.version_info < (3, 8):
        print("Se requiere Python 3.8 o superior")
        sys.exit(1)
    print(f"✓ Usando Python {sys.version.split()[0]}")

def check_uv_installed():
    """Verifica si uv está instalado, y lo instala si no lo está."""
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        print("✓ uv ya está instalado")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("uv no está instalado. Instalando...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "uv"], check=True)
            print("✓ uv instalado correctamente")
            return True
        except subprocess.CalledProcessError:
            print("Error al instalar uv. Por favor, instálalo manualmente con 'pip install uv'")
            return False

def create_virtual_environment():
    """Crea un entorno virtual con uv."""
    print("Creando entorno virtual con uv...")
    try:
        subprocess.run(["uv", "venv"], check=True)
        print("✓ Entorno virtual creado correctamente")
        return True
    except subprocess.CalledProcessError:
        print("Error al crear el entorno virtual")
        return False

def install_dependencies():
    """Instala las dependencias del proyecto en el entorno virtual."""
    print("Instalando dependencias...")
    
    # Determinar el comando de activación según el sistema operativo
    if platform.system() == "Windows":
        activate_cmd = [".venv\\Scripts\\activate.bat"]
        separator = "&"
    else:
        activate_cmd = ["source", ".venv/bin/activate"]
        separator = "&&"
    
    # Construir el comando completo
    cmd = separator.join([
        " ".join(activate_cmd),
        "uv pip install -r requirements.txt",
        "python -m nltk.downloader punkt vader_lexicon stopwords"
    ])
    
    try:
        if platform.system() == "Windows":
            subprocess.run(cmd, shell=True, check=True)
        else:
            subprocess.run(cmd, shell=True, executable="/bin/bash", check=True)
        print("✓ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError:
        print("Error al instalar las dependencias")
        return False

def install_ruff():
    """Instala ruff para el linting del código."""
    print("Instalando ruff...")
    
    # Determinar el comando de activación según el sistema operativo
    if platform.system() == "Windows":
        activate_cmd = [".venv\\Scripts\\activate.bat"]
        separator = "&"
    else:
        activate_cmd = ["source", ".venv/bin/activate"]
        separator = "&&"
    
    # Construir el comando completo
    cmd = separator.join([
        " ".join(activate_cmd),
        "uv pip install ruff"
    ])
    
    try:
        if platform.system() == "Windows":
            subprocess.run(cmd, shell=True, check=True)
        else:
            subprocess.run(cmd, shell=True, executable="/bin/bash", check=True)
        print("✓ ruff instalado correctamente")
        return True
    except subprocess.CalledProcessError:
        print("Error al instalar ruff")
        return False

def main():
    """Función principal que ejecuta todos los pasos de instalación."""
    print("=== Configuración del entorno para el proyecto de análisis de sentimiento ===")
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("requirements.txt") or not os.path.exists("config"):
        print("Error: Este script debe ejecutarse desde el directorio raíz del proyecto")
        print("Asegúrate de que requirements.txt y el directorio config existen")
        sys.exit(1)
    
    # Ejecutar los pasos de instalación
    check_python_version()
    if not check_uv_installed():
        sys.exit(1)
    if not create_virtual_environment():
        sys.exit(1)
    if not install_dependencies():
        sys.exit(1)
    if not install_ruff():
        sys.exit(1)
    
    print("\n=== Instalación completada con éxito ===")
    print("Para activar el entorno virtual:")
    if platform.system() == "Windows":
        print("  .venv\\Scripts\\activate.bat")
    else:
        print("  source .venv/bin/activate")
    print("\nPara ejecutar el proyecto:")
    print("  python src/main.py")

if __name__ == "__main__":
    main()
