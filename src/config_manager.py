#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para cargar configuraciones y credenciales desde archivos YAML.
Proporciona una interfaz unificada para acceder a todas las configuraciones del proyecto.
"""

import os
import yaml
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("config_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConfigManager:
    """Clase para gestionar la configuración y credenciales del proyecto."""
    
    def __init__(self, config_dir=None):
        """
        Inicializa el gestor de configuración.
        
        Args:
            config_dir (str, optional): Directorio de configuración. Si no se especifica,
                                       se usa el directorio 'config' en la raíz del proyecto.
        """
        if config_dir is None:
            # Directorio de configuración por defecto
            self.config_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config'
            )
        else:
            self.config_dir = config_dir
        
        # Rutas a los archivos de configuración
        self.config_path = os.path.join(self.config_dir, 'config.yaml')
        self.credentials_path = os.path.join(self.config_dir, 'credentials.yaml')
        
        # Cargar configuraciones
        self.config = self._load_yaml(self.config_path)
        self.credentials = self._load_yaml(self.credentials_path)
        
        # Verificar que se cargaron correctamente
        if not self.config:
            logger.warning(f"No se pudo cargar la configuración desde {self.config_path}")
            self.config = {}
        
        if not self.credentials:
            logger.warning(f"No se pudo cargar las credenciales desde {self.credentials_path}")
            self.credentials = {}
    
    def _load_yaml(self, file_path):
        """
        Carga un archivo YAML.
        
        Args:
            file_path (str): Ruta al archivo YAML.
            
        Returns:
            dict: Contenido del archivo YAML, o un diccionario vacío si hay error.
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file)
            else:
                logger.error(f"El archivo {file_path} no existe")
                return {}
        except Exception as e:
            logger.error(f"Error al cargar {file_path}: {str(e)}")
            return {}
    
    def get_config(self, section=None, key=None, default=None):
        """
        Obtiene un valor de configuración.
        
        Args:
            section (str, optional): Sección de la configuración.
            key (str, optional): Clave dentro de la sección.
            default: Valor por defecto si no se encuentra la configuración.
            
        Returns:
            El valor de configuración, o el valor por defecto si no se encuentra.
        """
        if section is None:
            return self.config
        
        if section not in self.config:
            return default
        
        if key is None:
            return self.config[section]
        
        if key not in self.config[section]:
            return default
        
        return self.config[section][key]
    
    def get_credential(self, section, key=None, default=None):
        """
        Obtiene un valor de credencial.
        
        Args:
            section (str): Sección de credenciales (ej: 'openai', 'telegram').
            key (str, optional): Clave dentro de la sección.
            default: Valor por defecto si no se encuentra la credencial.
            
        Returns:
            El valor de la credencial, o el valor por defecto si no se encuentra.
        """
        if section not in self.credentials:
            return default
        
        if key is None:
            return self.credentials[section]
        
        if key not in self.credentials[section]:
            return default
        
        return self.credentials[section][key]
    
    def get_companies(self):
        """
        Obtiene la lista de empresas configuradas.
        
        Returns:
            list: Lista de diccionarios con información de las empresas.
        """
        return self.config.get('companies', [])
    
    def get_database_config(self):
        """
        Obtiene la configuración de la base de datos.
        
        Returns:
            dict: Configuración de la base de datos.
        """
        return self.config.get('database', {'type': 'duckdb', 'filename': 'news_database.duckdb'})
    
    def get_openai_config(self):
        """
        Obtiene la configuración de OpenAI.
        
        Returns:
            dict: Configuración de OpenAI.
        """
        return self.credentials.get('openai', {})
    
    def get_telegram_config(self):
        """
        Obtiene la configuración de Telegram.
        
        Returns:
            dict: Configuración de Telegram.
        """
        return self.credentials.get('telegram', {})
    
    def get_news_api_config(self):
        """
        Obtiene la configuración de la API de noticias.
        
        Returns:
            dict: Configuración de la API de noticias.
        """
        return self.credentials.get('news_api', {})
    
    def is_valid_credential(self, section, key):
        """
        Verifica si una credencial es válida (no está vacía ni es el valor por defecto).
        
        Args:
            section (str): Sección de credenciales.
            key (str): Clave dentro de la sección.
            
        Returns:
            bool: True si la credencial es válida, False en caso contrario.
        """
        value = self.get_credential(section, key)
        
        if value is None:
            return False
        
        if isinstance(value, str) and (value == "" or value.startswith("YOUR_")):
            return False
        
        return True
    
    def validate_required_credentials(self):
        """
        Valida que todas las credenciales requeridas estén configuradas.
        
        Returns:
            tuple: (is_valid, missing_credentials) - Booleano indicando si todas las credenciales
                  requeridas están configuradas, y lista de credenciales faltantes.
        """
        required_credentials = [
            ('news_api', 'api_key'),
            ('openai', 'api_key'),
            ('telegram', 'token'),
            ('telegram', 'chat_id')
        ]
        
        missing = []
        
        for section, key in required_credentials:
            if not self.is_valid_credential(section, key):
                missing.append(f"{section}.{key}")
        
        return len(missing) == 0, missing

# Instancia global para uso en todo el proyecto
config_manager = ConfigManager()

if __name__ == "__main__":
    # Ejemplo de uso
    cm = ConfigManager()
    
    # Mostrar configuración general
    print("Configuración general:")
    print(f"Intervalo de actualización: {cm.get_config('general', 'update_interval')}")
    print(f"Años históricos: {cm.get_config('general', 'historical_years')}")
    
    # Mostrar empresas configuradas
    print("\nEmpresas configuradas:")
    for company in cm.get_companies():
        print(f"- {company['name']} ({company['symbol']})")
    
    # Validar credenciales
    is_valid, missing = cm.validate_required_credentials()
    if is_valid:
        print("\nTodas las credenciales requeridas están configuradas correctamente.")
    else:
        print("\nFaltan las siguientes credenciales:")
        for cred in missing:
            print(f"- {cred}")
