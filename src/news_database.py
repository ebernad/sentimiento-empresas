#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para la gestión de la base de datos DuckDB para almacenamiento de noticias.
Proporciona funciones para crear, actualizar y consultar la base de datos de noticias.
"""

import os
import sys
import yaml
import json
import duckdb
import pandas as pd
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("duckdb_news.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NewsDatabase:
    """Clase para gestionar la base de datos DuckDB de noticias."""
    
    def __init__(self, config_path=None):
        """
        Inicializa la base de datos de noticias.
        
        Args:
            config_path (str, optional): Ruta al archivo de configuración YAML.
                                        Si no se proporciona, se usa la ruta por defecto.
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config',
                'config.yaml'
            )
        self.config = self._load_config(config_path)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.db_path = os.path.join(self.data_dir, 'news_database.duckdb')
        
        # Crear directorio de datos si no existe
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Inicializar la base de datos
        self._init_database()
    
    def _load_config(self, config_path):
        """
        Carga la configuración desde el archivo YAML.
        
        Args:
            config_path (str): Ruta al archivo de configuración.
            
        Returns:
            dict: Configuración cargada.
        """
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    
    def _init_database(self):
        """
        Inicializa la base de datos DuckDB y crea las tablas necesarias si no existen.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Crear tabla de noticias si no existe
            conn.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id VARCHAR PRIMARY KEY,
                    symbol VARCHAR,
                    title VARCHAR,
                    description VARCHAR,
                    content VARCHAR,
                    url VARCHAR,
                    published_at TIMESTAMP,
                    source_name VARCHAR,
                    source_url VARCHAR,
                    collected_at TIMESTAMP,
                    relevance FLOAT
                )
            """)
            
            # Crear índices para búsquedas eficientes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_news_symbol ON news(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_news_published_at ON news(published_at)")
            
            # Cerrar conexión
            conn.close()
            
            logger.info("Base de datos inicializada correctamente")
            
        except Exception as e:
            logger.error(f"Error al inicializar la base de datos: {str(e)}")
            raise
    
    def migrate_from_json(self, news_dir):
        """
        Migra los datos de noticias desde archivos JSON a la base de datos DuckDB.
        
        Args:
            news_dir (str): Directorio que contiene los archivos JSON de noticias.
            
        Returns:
            int: Número de noticias migradas.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Contador de noticias migradas
            total_migrated = 0
            
            # Recorrer archivos JSON en el directorio
            for filename in os.listdir(news_dir):
                if filename.endswith('_news.json'):
                    # Extraer símbolo de la empresa del nombre del archivo
                    symbol = filename.split('_')[0]
                    
                    # Ruta completa al archivo JSON
                    json_path = os.path.join(news_dir, filename)
                    
                    # Cargar noticias desde el archivo JSON
                    with open(json_path, 'r', encoding='utf-8') as f:
                        news_list = json.load(f)
                    
                    # Migrar cada noticia a la base de datos
                    for news in news_list:
                        # Generar ID único para la noticia
                        news_id = f"{symbol}_{hash(news.get('url', '') + news.get('publishedAt', ''))}"
                        
                        # Convertir fecha de publicación a formato datetime
                        published_at = news.get('publishedAt', '')
                        if isinstance(published_at, str):
                            try:
                                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                            except:
                                published_at = datetime.now()
                        
                        # Convertir fecha de recopilación a formato datetime
                        collected_at = news.get('collected_at', '')
                        if isinstance(collected_at, str):
                            try:
                                collected_at = datetime.fromisoformat(collected_at.replace('Z', '+00:00'))
                            except:
                                collected_at = datetime.now()
                        elif not collected_at:
                            collected_at = datetime.now()
                        
                        # Extraer información de la fuente
                        source_name = news.get('source', {}).get('name', '')
                        source_url = news.get('source', {}).get('url', '')
                        
                        # Insertar noticia en la base de datos
                        conn.execute("""
                            INSERT OR IGNORE INTO news 
                            (id, symbol, title, description, content, url, published_at, source_name, source_url, collected_at, relevance)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            news_id,
                            symbol,
                            news.get('title', ''),
                            news.get('description', ''),
                            news.get('content', ''),
                            news.get('url', ''),
                            published_at,
                            source_name,
                            source_url,
                            collected_at,
                            news.get('relevance', 0.5)
                        ))
                        
                        total_migrated += 1
            
            # Cerrar conexión
            conn.close()
            
            logger.info(f"Migración completada: {total_migrated} noticias migradas a DuckDB")
            
            return total_migrated
            
        except Exception as e:
            logger.error(f"Error al migrar noticias desde JSON: {str(e)}")
            return 0
    
    def save_news(self, news_list, symbol):
        """
        Guarda una lista de noticias en la base de datos.
        
        Args:
            news_list (list): Lista de noticias a guardar.
            symbol (str): Símbolo de la empresa.
            
        Returns:
            tuple: (total_saved, new_saved) - Total de noticias procesadas y nuevas noticias guardadas.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Contadores
            total_processed = 0
            new_saved = 0
            
            # Procesar cada noticia
            for news in news_list:
                # Generar ID único para la noticia
                news_id = f"{symbol}_{hash(news.get('url', '') + news.get('publishedAt', ''))}"
                
                # Verificar si la noticia ya existe
                result = conn.execute(f"SELECT id FROM news WHERE id = '{news_id}'").fetchone()
                
                if not result:
                    # Convertir fecha de publicación a formato datetime
                    published_at = news.get('publishedAt', '')
                    if isinstance(published_at, str):
                        try:
                            published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        except:
                            published_at = datetime.now()
                    
                    # Extraer información de la fuente
                    source_name = news.get('source', {}).get('name', '')
                    source_url = news.get('source', {}).get('url', '')
                    
                    # Insertar noticia en la base de datos
                    conn.execute("""
                        INSERT INTO news 
                        (id, symbol, title, description, content, url, published_at, source_name, source_url, collected_at, relevance)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        news_id,
                        symbol,
                        news.get('title', ''),
                        news.get('description', ''),
                        news.get('content', ''),
                        news.get('url', ''),
                        published_at,
                        source_name,
                        source_url,
                        datetime.now(),
                        news.get('relevance', 0.5)
                    ))
                    
                    new_saved += 1
                
                total_processed += 1
            
            # Cerrar conexión
            conn.close()
            
            logger.info(f"Noticias guardadas para {symbol}: {new_saved} nuevas de {total_processed} procesadas")
            
            return (total_processed, new_saved)
            
        except Exception as e:
            logger.error(f"Error al guardar noticias en la base de datos: {str(e)}")
            return (0, 0)
    
    def get_news_by_symbol(self, symbol, limit=None):
        """
        Obtiene todas las noticias de una empresa.
        
        Args:
            symbol (str): Símbolo de la empresa.
            limit (int, optional): Límite de noticias a obtener.
            
        Returns:
            pandas.DataFrame: DataFrame con las noticias.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Construir consulta
            query = f"SELECT * FROM news WHERE symbol = '{symbol}' ORDER BY published_at DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            # Ejecutar consulta
            df = conn.execute(query).fetchdf()
            
            # Cerrar conexión
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener noticias por símbolo: {str(e)}")
            return pd.DataFrame()
    
    def get_news_by_date_range(self, symbol, start_date, end_date=None):
        """
        Obtiene noticias de una empresa en un rango de fechas.
        
        Args:
            symbol (str): Símbolo de la empresa.
            start_date (datetime): Fecha de inicio.
            end_date (datetime, optional): Fecha de fin. Si no se especifica, se usa la fecha actual.
            
        Returns:
            pandas.DataFrame: DataFrame con las noticias.
        """
        try:
            # Si no se especifica fecha de fin, usar fecha actual
            if end_date is None:
                end_date = datetime.now()
            
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Ejecutar consulta
            df = conn.execute(f"""
                SELECT * FROM news 
                WHERE symbol = '{symbol}' 
                AND published_at >= '{start_date.isoformat()}' 
                AND published_at <= '{end_date.isoformat()}'
                ORDER BY published_at DESC
            """).fetchdf()
            
            # Cerrar conexión
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener noticias por rango de fechas: {str(e)}")
            return pd.DataFrame()
    
    def get_historical_context(self, symbol, current_date, context_range):
        """
        Obtiene noticias históricas para proporcionar contexto.
        
        Args:
            symbol (str): Símbolo de la empresa.
            current_date (datetime): Fecha actual.
            context_range (str): Rango de contexto ('week', 'month', 'year', 'all').
            
        Returns:
            pandas.DataFrame: DataFrame con las noticias de contexto.
        """
        try:
            # Determinar la fecha límite según el rango configurado
            if context_range == "week":
                limit_date = current_date - timedelta(days=7)
            elif context_range == "month":
                limit_date = current_date - timedelta(days=30)
            elif context_range == "year":
                limit_date = current_date - timedelta(days=365)
            elif context_range == "all":
                # Para 'all', usamos una fecha muy antigua
                limit_date = datetime(1970, 1, 1)
            else:
                # Por defecto, usar una semana
                limit_date = current_date - timedelta(days=7)
            
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Ejecutar consulta
            df = conn.execute(f"""
                SELECT * FROM news 
                WHERE symbol = '{symbol}' 
                AND published_at >= '{limit_date.isoformat()}' 
                AND published_at < '{current_date.isoformat()}'
                ORDER BY published_at DESC
                LIMIT 10
            """).fetchdf()
            
            # Cerrar conexión
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener contexto histórico: {str(e)}")
            return pd.DataFrame()
    
    def get_news_count(self, symbol=None):
        """
        Obtiene el número de noticias en la base de datos.
        
        Args:
            symbol (str, optional): Símbolo de la empresa. Si no se especifica, se cuentan todas las noticias.
            
        Returns:
            int: Número de noticias.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Construir consulta
            if symbol:
                query = f"SELECT COUNT(*) FROM news WHERE symbol = '{symbol}'"
            else:
                query = "SELECT COUNT(*) FROM news"
            
            # Ejecutar consulta
            count = conn.execute(query).fetchone()[0]
            
            # Cerrar conexión
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Error al obtener conteo de noticias: {str(e)}")
            return 0
    
    def search_news(self, symbol, keywords, limit=10):
        """
        Busca noticias que contengan palabras clave específicas.
        
        Args:
            symbol (str): Símbolo de la empresa.
            keywords (str): Palabras clave a buscar.
            limit (int, optional): Límite de noticias a obtener.
            
        Returns:
            pandas.DataFrame: DataFrame con las noticias encontradas.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Construir consulta
            query = f"""
                SELECT * FROM news 
                WHERE symbol = '{symbol}' 
                AND (
                    title LIKE '%{keywords}%' 
                    OR description LIKE '%{keywords}%' 
                    OR content LIKE '%{keywords}%'
                )
                ORDER BY published_at DESC
                LIMIT {limit}
            """
            
            # Ejecutar consulta
            df = conn.execute(query).fetchdf()
            
            # Cerrar conexión
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error al buscar noticias: {str(e)}")
            return pd.DataFrame()
    
    def format_context_for_prompt(self, context_df):
        """
        Formatea el contexto histórico para incluirlo en el prompt de ChatGPT.
        
        Args:
            context_df (pandas.DataFrame): DataFrame con las noticias de contexto.
            
        Returns:
            str: Contexto histórico formateado.
        """
        if context_df.empty:
            return "No hay contexto histórico disponible."
        
        # Formatear el contexto
        context = "Contexto histórico:\n"
        
        for _, row in context_df.iterrows():
            date_str = row['published_at'].strftime('%Y-%m-%d')
            title = row['title']
            context += f"- {date_str}: {title}\n"
        
        return context

if __name__ == "__main__":
    # Ruta al archivo de configuración
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'config.yaml'
    )
    
    # Crear instancia de la base de datos
    db = NewsDatabase(config_path)
    
    # Migrar datos desde JSON si existen
    news_dir = os.path.join(db.data_dir, 'news')
    if os.path.exists(news_dir):
        migrated = db.migrate_from_json(news_dir)
        print(f"Migradas {migrated} noticias desde archivos JSON")
    
    # Mostrar estadísticas
    total_news = db.get_news_count()
    print(f"Total de noticias en la base de datos: {total_news}")
    
    # Mostrar conteo por empresa
    for company in db.config['companies']:
        symbol = company['symbol']
        count = db.get_news_count(symbol)
        print(f"Noticias para {symbol}: {count}")
