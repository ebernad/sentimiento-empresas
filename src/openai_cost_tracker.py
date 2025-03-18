#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para el seguimiento y cálculo de costes de tokens de OpenAI.
Almacena información detallada sobre cada llamada a la API en DuckDB.
"""

import os
import sys
import json
import duckdb
import pandas as pd
from datetime import datetime
import logging
import tiktoken

# Importar módulos del proyecto
from config_manager import config_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("openai_costs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OpenAICostTracker:
    """Clase para el seguimiento y cálculo de costes de tokens de OpenAI."""
    
    def __init__(self):
        """
        Inicializa el seguimiento de costes de OpenAI.
        """
        # Obtener configuración
        self.openai_config = config_manager.get_openai_config()
        
        # Crear directorios necesarios
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.db_path = os.path.join(self.data_dir, 'openai_costs.duckdb')
        
        # Inicializar la base de datos
        self._init_database()
        
        # Precios por modelo (en USD por 1000 tokens)
        # Fuente: https://openai.com/pricing
        self.model_prices = {
            'gpt-3.5-turbo': {
                'input': 0.0015,   # $0.0015 por 1K tokens de entrada
                'output': 0.002    # $0.002 por 1K tokens de salida
            },
            'gpt-4': {
                'input': 0.03,     # $0.03 por 1K tokens de entrada
                'output': 0.06     # $0.06 por 1K tokens de salida
            },
            'gpt-4-turbo': {
                'input': 0.01,     # $0.01 por 1K tokens de entrada
                'output': 0.03     # $0.03 por 1K tokens de salida
            }
        }
        
        # Modelo por defecto
        self.default_model = self.openai_config.get('model', 'gpt-3.5-turbo')
        
        # Inicializar codificador de tokens
        self.tokenizers = {}
    
    def _init_database(self):
        """
        Inicializa la base de datos DuckDB para el seguimiento de costes.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Crear tabla de costes si no existe
            conn.execute("""
                CREATE TABLE IF NOT EXISTS openai_costs (
                    id VARCHAR PRIMARY KEY,
                    timestamp TIMESTAMP,
                    model VARCHAR,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    prompt_cost DOUBLE,
                    completion_cost DOUBLE,
                    total_cost DOUBLE,
                    symbol VARCHAR,
                    news_date DATE,
                    request_type VARCHAR,
                    status VARCHAR
                )
            """)
            
            # Crear índices para búsquedas eficientes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_costs_timestamp ON openai_costs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_costs_symbol ON openai_costs(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_costs_model ON openai_costs(model)")
            
            # Cerrar conexión
            conn.close()
            
            logger.info("Base de datos de costes inicializada correctamente")
            
        except Exception as e:
            logger.error(f"Error al inicializar la base de datos de costes: {str(e)}")
            raise
    
    def _get_tokenizer(self, model):
        """
        Obtiene el codificador de tokens para un modelo específico.
        
        Args:
            model (str): Nombre del modelo de OpenAI.
            
        Returns:
            tiktoken.Encoding: Codificador de tokens para el modelo.
        """
        if model not in self.tokenizers:
            try:
                if model.startswith('gpt-4'):
                    self.tokenizers[model] = tiktoken.encoding_for_model("gpt-4")
                elif model.startswith('gpt-3.5'):
                    self.tokenizers[model] = tiktoken.encoding_for_model("gpt-3.5-turbo")
                else:
                    # Modelo desconocido, usar cl100k_base como fallback
                    self.tokenizers[model] = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.error(f"Error al obtener tokenizer para {model}: {str(e)}")
                # Usar cl100k_base como fallback
                self.tokenizers[model] = tiktoken.get_encoding("cl100k_base")
        
        return self.tokenizers[model]
    
    def count_tokens(self, text, model=None):
        """
        Cuenta el número de tokens en un texto.
        
        Args:
            text (str): Texto a contar.
            model (str, optional): Modelo para el que contar tokens. Si no se especifica, se usa el modelo por defecto.
            
        Returns:
            int: Número de tokens.
        """
        if model is None:
            model = self.default_model
        
        tokenizer = self._get_tokenizer(model)
        return len(tokenizer.encode(text))
    
    def calculate_cost(self, prompt_tokens, completion_tokens, model=None):
        """
        Calcula el coste de una llamada a la API de OpenAI.
        
        Args:
            prompt_tokens (int): Número de tokens en el prompt.
            completion_tokens (int): Número de tokens en la respuesta.
            model (str, optional): Modelo utilizado. Si no se especifica, se usa el modelo por defecto.
            
        Returns:
            tuple: (prompt_cost, completion_cost, total_cost) en USD.
        """
        if model is None:
            model = self.default_model
        
        # Si el modelo no está en la lista de precios, usar gpt-3.5-turbo como fallback
        if model not in self.model_prices:
            logger.warning(f"Modelo {model} no encontrado en la lista de precios. Usando precios de gpt-3.5-turbo.")
            model = 'gpt-3.5-turbo'
        
        # Calcular costes
        prompt_cost = (prompt_tokens / 1000) * self.model_prices[model]['input']
        completion_cost = (completion_tokens / 1000) * self.model_prices[model]['output']
        total_cost = prompt_cost + completion_cost
        
        return (prompt_cost, completion_cost, total_cost)
    
    def track_request(self, prompt, completion, model=None, symbol=None, news_date=None, request_type="sentiment_analysis", status="success"):
        """
        Registra una llamada a la API de OpenAI y calcula su coste.
        
        Args:
            prompt (str): Texto del prompt enviado a la API.
            completion (str): Texto de la respuesta recibida.
            model (str, optional): Modelo utilizado. Si no se especifica, se usa el modelo por defecto.
            symbol (str, optional): Símbolo de la empresa relacionada con la llamada.
            news_date (datetime, optional): Fecha de la noticia analizada.
            request_type (str, optional): Tipo de solicitud (por defecto, "sentiment_analysis").
            status (str, optional): Estado de la solicitud ("success" o "error").
            
        Returns:
            dict: Información sobre la llamada y su coste.
        """
        if model is None:
            model = self.default_model
        
        try:
            # Contar tokens
            prompt_tokens = self.count_tokens(prompt, model)
            completion_tokens = self.count_tokens(completion, model)
            total_tokens = prompt_tokens + completion_tokens
            
            # Calcular costes
            prompt_cost, completion_cost, total_cost = self.calculate_cost(prompt_tokens, completion_tokens, model)
            
            # Generar ID único
            request_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(prompt)}"
            
            # Preparar datos para guardar
            data = {
                'id': request_id,
                'timestamp': datetime.now(),
                'model': model,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens,
                'prompt_cost': prompt_cost,
                'completion_cost': completion_cost,
                'total_cost': total_cost,
                'symbol': symbol if symbol else '',
                'news_date': news_date if news_date else None,
                'request_type': request_type,
                'status': status
            }
            
            # Guardar en la base de datos
            self._save_to_db(data)
            
            # Registrar en el log
            logger.info(f"API call tracked: {total_tokens} tokens, ${total_cost:.6f} USD")
            
            return data
            
        except Exception as e:
            logger.error(f"Error al registrar llamada a la API: {str(e)}")
            return None
    
    def _save_to_db(self, data):
        """
        Guarda información de coste en la base de datos.
        
        Args:
            data (dict): Datos a guardar.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Insertar datos
            conn.execute("""
                INSERT INTO openai_costs 
                (id, timestamp, model, prompt_tokens, completion_tokens, total_tokens, 
                prompt_cost, completion_cost, total_cost, symbol, news_date, request_type, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['id'],
                data['timestamp'],
                data['model'],
                data['prompt_tokens'],
                data['completion_tokens'],
                data['total_tokens'],
                data['prompt_cost'],
                data['completion_cost'],
                data['total_cost'],
                data['symbol'],
                data['news_date'],
                data['request_type'],
                data['status']
            ))
            
            # Cerrar conexión
            conn.close()
            
        except Exception as e:
            logger.error(f"Error al guardar datos de coste en la base de datos: {str(e)}")
    
    def get_costs_summary(self, start_date=None, end_date=None, symbol=None, model=None):
        """
        Obtiene un resumen de costes de la API de OpenAI.
        
        Args:
            start_date (datetime, optional): Fecha de inicio para filtrar.
            end_date (datetime, optional): Fecha de fin para filtrar.
            symbol (str, optional): Símbolo de empresa para filtrar.
            model (str, optional): Modelo para filtrar.
            
        Returns:
            pandas.DataFrame: DataFrame con el resumen de costes.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Construir consulta
            query = "SELECT * FROM openai_costs WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if model:
                query += " AND model = ?"
                params.append(model)
            
            # Ejecutar consulta
            if params:
                df = conn.execute(query, params).fetchdf()
            else:
                df = conn.execute(query).fetchdf()
            
            # Cerrar conexión
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener resumen de costes: {str(e)}")
            return pd.DataFrame()
    
    def get_daily_costs(self, days=30, symbol=None):
        """
        Obtiene un resumen de costes diarios.
        
        Args:
            days (int, optional): Número de días a incluir.
            symbol (str, optional): Símbolo de empresa para filtrar.
            
        Returns:
            pandas.DataFrame: DataFrame con costes diarios.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Construir consulta
            query = """
                SELECT 
                    DATE_TRUNC('day', timestamp) AS date,
                    COUNT(*) AS requests,
                    SUM(prompt_tokens) AS prompt_tokens,
                    SUM(completion_tokens) AS completion_tokens,
                    SUM(total_tokens) AS total_tokens,
                    SUM(prompt_cost) AS prompt_cost,
                    SUM(completion_cost) AS completion_cost,
                    SUM(total_cost) AS total_cost
                FROM openai_costs
                WHERE timestamp >= CURRENT_DATE - INTERVAL ? DAY
            """
            params = [days]
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " GROUP BY DATE_TRUNC('day', timestamp) ORDER BY date DESC"
            
            # Ejecutar consulta
            df = conn.execute(query, params).fetchdf()
            
            # Cerrar conexión
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener costes diarios: {str(e)}")
            return pd.DataFrame()
    
    def get_costs_by_symbol(self, start_date=None, end_date=None):
        """
        Obtiene un resumen de costes por símbolo de empresa.
        
        Args:
            start_date (datetime, optional): Fecha de inicio para filtrar.
            end_date (datetime, optional): Fecha de fin para filtrar.
            
        Returns:
            pandas.DataFrame: DataFrame con costes por símbolo.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Construir consulta
            query = """
                SELECT 
                    symbol,
                    COUNT(*) AS requests,
                    SUM(prompt_tokens) AS prompt_tokens,
                    SUM(completion_tokens) AS completion_tokens,
                    SUM(total_tokens) AS total_tokens,
                    SUM(prompt_cost) AS prompt_cost,
                    SUM(completion_cost) AS completion_cost,
                    SUM(total_cost) AS total_cost
                FROM openai_costs
                WHERE symbol != ''
            """
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            query += " GROUP BY symbol ORDER BY total_cost DESC"
            
            # Ejecutar consulta
            if params:
                df = conn.execute(query, params).fetchdf()
            else:
                df = conn.execute(query).fetchdf()
            
            # Cerrar conexión
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener costes por símbolo: {str(e)}")
            return pd.DataFrame()
    
    def get_total_cost(self, start_date=None, end_date=None):
        """
        Obtiene el coste total de la API de OpenAI.
        
        Args:
            start_date (datetime, optional): Fecha de inicio para filtrar.
            end_date (datetime, optional): Fecha de fin para filtrar.
            
        Returns:
            float: Coste total en USD.
        """
        try:
            # Conectar a la base de datos
            conn = duckdb.connect(self.db_path)
            
            # Construir consulta
            query = "SELECT SUM(total_cost) FROM openai_costs WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            # Ejecutar consulta
            if params:
                result = conn.execute(query, params).fetchone()
            else:
                result = conn.execute(query).fetchone()
            
            # Cerrar conexión
            conn.close()
            
            return result[0] if result[0] is not None else 0.0
            
        except Exception as e:
            logger.error(f"Error al obtener coste total: {str(e)}")
            return 0.0
    
    def generate_cost_report(self, output_file=None):
        """
        Genera un informe detallado de costes.
        
        Args:
            output_file (str, optional): Ruta al archivo de salida. Si no se especifica,
                                        se guarda en data/results/openai_cost_report.md.
            
        Returns:
            str: Ruta al archivo de informe generado.
        """
        try:
            # Determinar ruta de salida
            if output_file is None:
                results_dir = os.path.join(self.data_dir, 'results')
                os.makedirs(results_dir, exist_ok=True)
                output_file = os.path.join(results_dir, 'openai_cost_report.md')
            
            # Obtener datos
            total_cost = self.get_total_cost()
            daily_costs = self.get_daily_costs(30)
            costs_by_symbol = self.get_costs_by_symbol()
            
            # Generar informe
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# Informe de Costes de OpenAI\n\n")
                f.write(f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("## Resumen General\n\n")
                f.write(f"- **Coste Total**: ${total_cost:.4f} USD\n")
                
                if not daily_costs.empty:
                    total_requests = daily_costs['requests'].sum()
                    total_tokens = daily_costs['total_tokens'].sum()
                    f.write(f"- **Total de Solicitudes**: {total_requests}\n")
                    f.write(f"- **Total de Tokens**: {total_tokens}\n")
                    f.write(f"- **Coste Promedio por Solicitud**: ${(total_cost / total_requests if total_requests > 0 else 0):.6f} USD\n")
                    f.write(f"- **Coste Promedio por 1K Tokens**: ${(total_cost / (total_tokens / 1000) if total_tokens > 0 else 0):.6f} USD\n\n")
                
                f.write("## Costes por Empresa\n\n")
                if not costs_by_symbol.empty:
                    f.write("| Empresa | Solicitudes | Tokens | Coste (USD) |\n")
                    f.write("|---------|-------------|--------|-------------|\n")
                    for _, row in costs_by_symbol.iterrows():
                        f.write(f"| {row['symbol']} | {row['requests']} | {row['total_tokens']} | ${row['total_cost']:.4f} |\n")
                else:
                    f.write("No hay datos disponibles por empresa.\n")
                
                f.write("\n## Costes Diarios (Últimos 30 días)\n\n")
                if not daily_costs.empty:
                    f.write("| Fecha | Solicitudes | Tokens | Coste (USD) |\n")
                    f.write("|-------|-------------|--------|-------------|\n")
                    for _, row in daily_costs.iterrows():
                        date_str = row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], datetime) else str(row['date'])
                        f.write(f"| {date_str} | {row['requests']} | {row['total_tokens']} | ${row['total_cost']:.4f} |\n")
                else:
                    f.write("No hay datos disponibles para los últimos 30 días.\n")
                
                f.write("\n## Recomendaciones\n\n")
                f.write("- Considerar ajustar el parámetro `max_daily_calls` para controlar los costes diarios.\n")
                f.write("- Revisar el uso de contexto histórico, ya que aumenta significativamente el número de tokens.\n")
                f.write("- Para reducir costes, considerar usar `gpt-3.5-turbo` en lugar de modelos GPT-4 cuando sea posible.\n")
            
            logger.info(f"Informe de costes generado en {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error al generar informe de costes: {str(e)}")
            return None

# Instancia global para uso en todo el proyecto
cost_tracker = OpenAICostTracker()

if __name__ == "__main__":
    # Ejemplo de uso
    tracker = OpenAICostTracker()
    
    # Generar informe de costes
    report_file = tracker.generate_cost_report()
    print(f"Informe generado en: {report_file}")
    
    # Mostrar coste total
    total_cost = tracker.get_total_cost()
    print(f"Coste total: ${total_cost:.4f} USD")
    
    # Mostrar costes por símbolo
    costs_by_symbol = tracker.get_costs_by_symbol()
    if not costs_by_symbol.empty:
        print("\nCostes por empresa:")
        print(costs_by_symbol)
