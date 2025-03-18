#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para la integración con Apache Superset para visualización de dashboards.
Prepara los datos y configura la conexión con Superset.
"""

import os
import sys
import json
import pandas as pd
import duckdb
import sqlalchemy
from sqlalchemy import create_engine
import logging
from datetime import datetime, timedelta
import yaml

# Importar módulos del proyecto
from config_manager import config_manager
from news_database import NewsDatabase
from openai_cost_tracker import cost_tracker

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("superset_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SupersetIntegration:
    """Clase para la integración con Apache Superset para visualización de dashboards."""
    
    def __init__(self):
        """
        Inicializa la integración con Superset.
        """
        # Obtener configuración
        self.superset_config = config_manager.get_config('superset', {})
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Crear directorios necesarios
        self.data_dir = os.path.join(self.project_dir, 'data')
        self.superset_dir = os.path.join(self.project_dir, 'superset')
        os.makedirs(self.superset_dir, exist_ok=True)
        
        # Configurar conexión a la base de datos
        self.db_path = os.path.join(self.data_dir, 'superset_data.db')
        self.connection_string = f"sqlite:///{self.db_path}"
        
        # Inicializar base de datos para Superset
        self._init_database()
    
    def _init_database(self):
        """
        Inicializa la base de datos SQLite para Superset.
        """
        try:
            # Crear conexión SQLAlchemy
            engine = create_engine(self.connection_string)
            
            # Crear tablas básicas si no existen
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("""
                    CREATE TABLE IF NOT EXISTS metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Insertar o actualizar metadatos
                conn.execute(sqlalchemy.text("""
                    INSERT OR REPLACE INTO metadata (key, value, updated_at)
                    VALUES ('last_update', :last_update, CURRENT_TIMESTAMP)
                """), {"last_update": datetime.now().isoformat()})
                
                conn.commit()
            
            logger.info(f"Base de datos para Superset inicializada en {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error al inicializar la base de datos para Superset: {str(e)}")
            raise
    
    def export_data_for_superset(self):
        """
        Exporta los datos necesarios para Superset.
        
        Returns:
            dict: Información sobre los datos exportados.
        """
        results = {}
        
        try:
            # Exportar datos de sentimiento
            results['sentiment'] = self._export_sentiment_data()
            
            # Exportar datos de costes de OpenAI
            results['costs'] = self._export_openai_costs()
            
            # Exportar datos de correlación
            results['correlation'] = self._export_correlation_data()
            
            # Generar archivo de configuración para Superset
            self._generate_superset_config()
            
            logger.info("Datos exportados correctamente para Superset")
            
            return results
            
        except Exception as e:
            logger.error(f"Error al exportar datos para Superset: {str(e)}")
            return {"error": str(e)}
    
    def _export_sentiment_data(self):
        """
        Exporta los datos de sentimiento para Superset.
        
        Returns:
            dict: Información sobre los datos exportados.
        """
        try:
            # Crear conexión SQLAlchemy
            engine = create_engine(self.connection_string)
            
            # Obtener lista de empresas
            companies = config_manager.get_companies()
            
            # Contador de registros exportados
            total_exported = 0
            
            # Procesar cada empresa
            for company in companies:
                symbol = company['symbol']
                
                # Cargar datos de sentimiento
                sentiment_path = os.path.join(self.data_dir, 'results', f"{symbol}_sentiment_chatgpt.csv")
                
                if os.path.exists(sentiment_path):
                    # Cargar datos
                    df = pd.read_csv(sentiment_path, index_col=0, parse_dates=True)
                    
                    # Añadir columna de símbolo
                    df['symbol'] = symbol
                    df['company_name'] = company['name']
                    
                    # Convertir índice a columna de fecha
                    df.reset_index(inplace=True)
                    df.rename(columns={'index': 'date'}, inplace=True)
                    
                    # Guardar en la base de datos
                    df.to_sql('sentiment_data', engine, if_exists='append', index=False)
                    
                    total_exported += len(df)
                    
                    logger.info(f"Exportados {len(df)} registros de sentimiento para {symbol}")
                else:
                    logger.warning(f"No se encontraron datos de sentimiento para {symbol}")
            
            # Crear índices para mejorar rendimiento
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("CREATE INDEX IF NOT EXISTS idx_sentiment_symbol ON sentiment_data(symbol)"))
                conn.execute(sqlalchemy.text("CREATE INDEX IF NOT EXISTS idx_sentiment_date ON sentiment_data(date)"))
                conn.commit()
            
            return {"total_exported": total_exported}
            
        except Exception as e:
            logger.error(f"Error al exportar datos de sentimiento: {str(e)}")
            return {"error": str(e)}
    
    def _export_openai_costs(self):
        """
        Exporta los datos de costes de OpenAI para Superset.
        
        Returns:
            dict: Información sobre los datos exportados.
        """
        try:
            # Crear conexión SQLAlchemy
            engine = create_engine(self.connection_string)
            
            # Obtener datos de costes
            costs_df = cost_tracker.get_costs_summary()
            
            if not costs_df.empty:
                # Guardar en la base de datos
                costs_df.to_sql('openai_costs', engine, if_exists='replace', index=False)
                
                # Crear índices para mejorar rendimiento
                with engine.connect() as conn:
                    conn.execute(sqlalchemy.text("CREATE INDEX IF NOT EXISTS idx_costs_timestamp ON openai_costs(timestamp)"))
                    conn.execute(sqlalchemy.text("CREATE INDEX IF NOT EXISTS idx_costs_symbol ON openai_costs(symbol)"))
                    conn.commit()
                
                logger.info(f"Exportados {len(costs_df)} registros de costes de OpenAI")
                
                return {"total_exported": len(costs_df)}
            else:
                logger.warning("No se encontraron datos de costes de OpenAI")
                return {"total_exported": 0}
            
        except Exception as e:
            logger.error(f"Error al exportar datos de costes de OpenAI: {str(e)}")
            return {"error": str(e)}
    
    def _export_correlation_data(self):
        """
        Exporta los datos de correlación para Superset.
        
        Returns:
            dict: Información sobre los datos exportados.
        """
        try:
            # Crear conexión SQLAlchemy
            engine = create_engine(self.connection_string)
            
            # Obtener lista de empresas
            companies = config_manager.get_companies()
            
            # Contador de registros exportados
            total_exported = 0
            
            # Procesar cada empresa
            for company in companies:
                symbol = company['symbol']
                
                # Cargar datos de correlación
                correlation_path = os.path.join(self.data_dir, 'results', 'correlation', f"{symbol}_correlation.csv")
                
                if os.path.exists(correlation_path):
                    # Cargar datos
                    df = pd.read_csv(correlation_path)
                    
                    # Añadir columna de símbolo
                    df['symbol'] = symbol
                    df['company_name'] = company['name']
                    
                    # Guardar en la base de datos
                    df.to_sql('correlation_data', engine, if_exists='append', index=False)
                    
                    total_exported += len(df)
                    
                    logger.info(f"Exportados {len(df)} registros de correlación para {symbol}")
                else:
                    logger.warning(f"No se encontraron datos de correlación para {symbol}")
            
            # Crear índices para mejorar rendimiento
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("CREATE INDEX IF NOT EXISTS idx_correlation_symbol ON correlation_data(symbol)"))
                conn.commit()
            
            return {"total_exported": total_exported}
            
        except Exception as e:
            logger.error(f"Error al exportar datos de correlación: {str(e)}")
            return {"error": str(e)}
    
    def _generate_superset_config(self):
        """
        Genera el archivo de configuración para Superset.
        """
        try:
            # Configuración para Superset
            superset_config = {
                "databases": [
                    {
                        "database_name": "Análisis de Sentimiento",
                        "sqlalchemy_uri": self.connection_string,
                        "tables": [
                            {
                                "table_name": "sentiment_data",
                                "main_dttm_col": "date",
                                "description": "Datos de análisis de sentimiento de noticias"
                            },
                            {
                                "table_name": "openai_costs",
                                "main_dttm_col": "timestamp",
                                "description": "Datos de costes de OpenAI"
                            },
                            {
                                "table_name": "correlation_data",
                                "description": "Datos de correlación entre sentimiento y precios"
                            }
                        ]
                    }
                ],
                "dashboards": [
                    {
                        "dashboard_title": "Análisis de Sentimiento por Empresa",
                        "description": "Visualización del sentimiento de noticias por empresa"
                    },
                    {
                        "dashboard_title": "Seguimiento de Costes de OpenAI",
                        "description": "Visualización de costes de OpenAI por día y empresa"
                    },
                    {
                        "dashboard_title": "Correlación Sentimiento-Precio",
                        "description": "Visualización de la correlación entre sentimiento y movimientos de precios"
                    }
                ]
            }
            
            # Guardar configuración
            config_path = os.path.join(self.superset_dir, 'superset_config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(superset_config, f, indent=2)
            
            logger.info(f"Configuración para Superset generada en {config_path}")
            
        except Exception as e:
            logger.error(f"Error al generar configuración para Superset: {str(e)}")
    
    def generate_superset_instructions(self):
        """
        Genera instrucciones para configurar Superset.
        
        Returns:
            str: Ruta al archivo de instrucciones generado.
        """
        try:
            # Crear archivo de instrucciones
            instructions_path = os.path.join(self.superset_dir, 'superset_setup.md')
            
            with open(instructions_path, 'w', encoding='utf-8') as f:
                f.write("# Configuración de Apache Superset\n\n")
                f.write("Este documento proporciona instrucciones para configurar Apache Superset con los datos del proyecto de análisis de sentimiento.\n\n")
                
                f.write("## Requisitos previos\n\n")
                f.write("- Docker y Docker Compose instalados\n")
                f.write("- Puerto 8088 disponible para Superset\n\n")
                
                f.write("## Pasos para la configuración\n\n")
                
                f.write("### 1. Iniciar Superset con Docker Compose\n\n")
                f.write("```bash\n")
                f.write("cd superset\n")
                f.write("docker-compose up -d\n")
                f.write("```\n\n")
                
                f.write("### 2. Crear usuario administrador\n\n")
                f.write("```bash\n")
                f.write("docker-compose exec superset superset fab create-admin \\\n")
                f.write("    --username admin \\\n")
                f.write("    --firstname Admin \\\n")
                f.write("    --lastname User \\\n")
                f.write("    --email admin@example.com \\\n")
                f.write("    --password admin\n")
                f.write("```\n\n")
                
                f.write("### 3. Inicializar la base de datos de Superset\n\n")
                f.write("```bash\n")
                f.write("docker-compose exec superset superset db upgrade\n")
                f.write("docker-compose exec superset superset init\n")
                f.write("```\n\n")
                
                f.write("### 4. Acceder a Superset\n\n")
                f.write("Abrir en el navegador: http://localhost:8088\n")
                f.write("- Usuario: admin\n")
                f.write("- Contraseña: admin\n\n")
                
                f.write("### 5. Configurar la conexión a la base de datos\n\n")
                f.write("1. En Superset, ir a **Data > Databases > + Database**\n")
                f.write("2. Seleccionar **SQLite**\n")
                f.write("3. Configurar la conexión:\n")
                f.write("   - **Database Name**: Análisis de Sentimiento\n")
                f.write(f"   - **SQLAlchemy URI**: {self.connection_string}\n")
                f.write("4. Hacer clic en **Test Connection** para verificar\n")
                f.write("5. Hacer clic en **Connect** para guardar\n\n")
                
                f.write("### 6. Importar los datasets\n\n")
                f.write("1. En Superset, ir a **Data > Datasets > + Dataset**\n")
                f.write("2. Seleccionar la base de datos **Análisis de Sentimiento**\n")
                f.write("3. Seleccionar el esquema **main**\n")
                f.write("4. Seleccionar la tabla **sentiment_data**\n")
                f.write("5. Hacer clic en **Add** para añadir el dataset\n")
                f.write("6. Repetir para las tablas **openai_costs** y **correlation_data**\n\n")
                
                f.write("### 7. Crear los dashboards\n\n")
                f.write("#### Dashboard de Análisis de Sentimiento\n\n")
                f.write("1. En Superset, ir a **Dashboards > + Dashboard**\n")
                f.write("2. Nombrar el dashboard como **Análisis de Sentimiento por Empresa**\n")
                f.write("3. Añadir los siguientes gráficos:\n")
                f.write("   - Gráfico de líneas de sentimiento por fecha\n")
                f.write("   - Gráfico de barras de distribución de niveles de sentimiento\n")
                f.write("   - Tabla de noticias recientes con explicaciones\n")
                f.write("   - Filtros por empresa y rango de fechas\n\n")
                
                f.write("#### Dashboard de Seguimiento de Costes\n\n")
                f.write("1. En Superset, ir a **Dashboards > + Dashboard**\n")
                f.write("2. Nombrar el dashboard como **Seguimiento de Costes de OpenAI**\n")
                f.write("3. Añadir los siguientes gráficos:\n")
                f.write("   - Gráfico de líneas de costes diarios\n")
                f.write("   - Gráfico de barras de costes por empresa\n")
                f.write("   - Gráfico de área de tokens enviados vs. recibidos\n")
                f.write("   - Indicadores de coste total y promedio por solicitud\n")
                f.write("   - Filtros por rango de fechas y empresa\n\n")
                
                f.write("#### Dashboard de Correlación\n\n")
                f.write("1. En Superset, ir a **Dashboards > + Dashboard**\n")
                f.write("2. Nombrar el dashboard como **Correlación Sentimiento-Precio**\n")
                f.write("3. Añadir los siguientes gráficos:\n")
                f.write("   - Gráfico de dispersión de sentimiento vs. cambio de precio\n")
                f.write("   - Gráfico de calor de correlación por empresa y periodo\n")
                f.write("   - Tabla de correlaciones con significancia estadística\n")
                f.write("   - Filtros por empresa y periodo de tiempo\n\n")
                
                f.write("## Ejemplos de consultas SQL para gráficos\n\n")
                
                f.write("### Sentimiento promedio por día y empresa\n\n")
                f.write("```sql\n")
                f.write("SELECT \n")
                f.write("    date, \n")
                f.write("    symbol, \n")
                f.write("    company_name,\n")
                f.write("    AVG(chatgpt_score) as avg_sentiment,\n")
                f.write("    COUNT(*) as news_count\n")
                f.write("FROM \n")
                f.write("    sentiment_data\n")
                f.write("GROUP BY \n")
                f.write("    date, symbol, company_name\n")
                f.write("ORDER BY \n")
                f.write("    date DESC\n")
                f.write("```\n\n")
                
                f.write("### Costes diarios de OpenAI\n\n")
                f.write("```sql\n")
                f.write("SELECT \n")
                f.write("    DATE(timestamp) as date, \n")
                f.write("    SUM(prompt_tokens) as total_prompt_tokens,\n")
                f.write("    SUM(completion_tokens) as total_completion_tokens,\n")
                f.write("    SUM(total_tokens) as total_tokens,\n")
                f.write("    SUM(total_cost) as total_cost,\n")
                f.write("    COUNT(*) as request_count\n")
                f.write("FROM \n")
                f.write("    openai_costs\n")
                f.write("GROUP BY \n")
                f.write("    DATE(timestamp)\n")
                f.write("ORDER BY \n")
                f.write("    date DESC\n")
                f.write("```\n\n")
                
                f.write("### Correlación entre sentimiento y cambio de precio\n\n")
                f.write("```sql\n")
                f.write("SELECT \n")
                f.write("    symbol, \n")
                f.write("    company_name,\n")
                f.write("    time_period,\n")
                f.write("    sentiment_price_correlation,\n")
                f.write("    p_value,\n")
                f.write("    CASE \n")
                f.write("        WHEN p_value < 0.05 THEN 'Significativo' \n")
                f.write("        ELSE 'No significativo' \n")
                f.write("    END as significance\n")
                f.write("FROM \n")
                f.write("    correlation_data\n")
                f.write("ORDER BY \n")
                f.write("    ABS(sentiment_price_correlation) DESC\n")
                f.write("```\n\n")
            
            logger.info(f"Instrucciones para Superset generadas en {instructions_path}")
            
            return instructions_path
            
        except Exception as e:
            logger.error(f"Error al generar instrucciones para Superset: {str(e)}")
            return None
    
    def generate_docker_compose(self):
        """
        Genera el archivo docker-compose.yml para Superset.
        
        Returns:
            str: Ruta al archivo docker-compose.yml generado.
        """
        try:
            # Crear archivo docker-compose.yml
            docker_compose_path = os.path.join(self.superset_dir, 'docker-compose.yml')
            
            docker_compose = {
                "version": "3",
                "services": {
                    "redis": {
                        "image": "redis:latest",
                        "restart": "unless-stopped",
                        "volumes": ["redis:/data"]
                    },
                    "db": {
                        "image": "postgres:13",
                        "restart": "unless-stopped",
                        "environment": [
                            "POSTGRES_DB=superset",
                            "POSTGRES_PASSWORD=superset",
                            "POSTGRES_USER=superset"
                        ],
                        "volumes": ["db_data:/var/lib/postgresql/data"]
                    },
                    "superset": {
                        "image": "apache/superset:latest",
                        "restart": "unless-stopped",
                        "depends_on": ["db", "redis"],
                        "environment": [
                            "SUPERSET_SECRET_KEY=your_secret_key_here",
                            "DATABASE_DB=superset",
                            "DATABASE_HOST=db",
                            "DATABASE_PASSWORD=superset",
                            "DATABASE_USER=superset",
                            "DATABASE_PORT=5432",
                            "DATABASE_DIALECT=postgresql",
                            "REDIS_HOST=redis",
                            "REDIS_PORT=6379"
                        ],
                        "ports": ["8088:8088"],
                        "volumes": [
                            "./superset_home:/app/superset_home",
                            f"{self.db_path}:/app/data/superset_data.db"
                        ]
                    }
                },
                "volumes": {
                    "db_data": {},
                    "redis": {}
                }
            }
            
            # Guardar archivo docker-compose.yml
            with open(docker_compose_path, 'w', encoding='utf-8') as f:
                yaml.dump(docker_compose, f, default_flow_style=False)
            
            logger.info(f"Archivo docker-compose.yml generado en {docker_compose_path}")
            
            return docker_compose_path
            
        except Exception as e:
            logger.error(f"Error al generar archivo docker-compose.yml: {str(e)}")
            return None

if __name__ == "__main__":
    # Crear instancia de integración con Superset
    superset = SupersetIntegration()
    
    # Exportar datos para Superset
    results = superset.export_data_for_superset()
    print("Resultados de exportación:", results)
    
    # Generar instrucciones para Superset
    instructions_path = superset.generate_superset_instructions()
    print(f"Instrucciones generadas en: {instructions_path}")
    
    # Generar archivo docker-compose.yml
    docker_compose_path = superset.generate_docker_compose()
    print(f"Archivo docker-compose.yml generado en: {docker_compose_path}")
