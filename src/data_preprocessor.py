#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para el preprocesamiento de datos de noticias y precios de acciones.
Prepara los datos para el análisis de sentimiento y correlación.
"""

import os
import yaml
import pandas as pd
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
import logging
import duckdb

class DataPreprocessor:
    """Clase para preprocesar datos de noticias y precios de acciones."""
    
    def __init__(self, config_path=None):
        """
        Inicializa el preprocesador de datos.
        
        Args:
            config_path (str): Ruta al archivo de configuración YAML.
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config',
                'config.yaml'
            )
        self.config = self._load_config(config_path)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.processed_dir = os.path.join(self.data_dir, 'processed')
        os.makedirs(self.processed_dir, exist_ok=True)
        
        # Asegurar que los recursos de NLTK estén descargados
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
            nltk.data.find('sentiment/vader_lexicon')
        except LookupError:
            print("Descargando recursos de NLTK...")
            nltk.download('punkt')
            nltk.download('stopwords')
            nltk.download('wordnet')
            nltk.download('vader_lexicon')
        
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
    
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
    
    def preprocess_all_data(self):
        """
        Preprocesa todos los datos de noticias y precios para todas las empresas.
        
        Returns:
            dict: Datos preprocesados por símbolo de empresa.
        """
        results = {}
        
        for company in self.config['companies']:
            symbol = company['symbol']
            
            print(f"Preprocesando datos para {symbol}...")
            
            try:
                # Preprocesar datos de precios
                stock_data = self._preprocess_stock_data(symbol)
                
                # Preprocesar noticias
                news_data = self._preprocess_news_data(symbol)
                
                # Combinar datos de precios y noticias
                combined_data = self._combine_data(stock_data, news_data, symbol)
                
                if combined_data is not None:
                    results[symbol] = combined_data
                
            except Exception as e:
                print(f"Error al preprocesar datos para {symbol}: {str(e)}")
        
        return results
    
    def _preprocess_stock_data(self, symbol):
        """
        Preprocesa los datos de precios de acciones.
        
        Args:
            symbol (str): Símbolo de la empresa.
            
        Returns:
            pandas.DataFrame: DataFrame con los datos de precios preprocesados.
        """
        file_path = os.path.join(self.data_dir, 'stocks', f"{symbol}_historical.csv")
        
        if not os.path.exists(file_path):
            print(f"No se encontraron datos históricos para {symbol}")
            return None
        
        # Cargar datos
        df = pd.read_csv(file_path, index_col='Date', parse_dates=True)
        
        # Calcular indicadores técnicos básicos
        # Rendimiento diario
        df['daily_return'] = df['close'].pct_change()
        
        # Media móvil de 5 y 20 días
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        
        # Volatilidad (desviación estándar de rendimientos en 10 días)
        df['volatility'] = df['daily_return'].rolling(window=10).std()
        
        # Eliminar filas con valores NaN
        df.dropna(inplace=True)
        
        # Guardar datos preprocesados
        processed_file_path = os.path.join(self.processed_dir, f"{symbol}_stock_processed.csv")
        df.to_csv(processed_file_path)
        
        return df
    
    def _preprocess_news_data(self, symbol):
        logger = logging.getLogger(__name__)
        """
        Preprocesa los datos de noticias para un símbolo específico.
        
        Args:
            symbol (str): Símbolo de la empresa.
            
        Returns:
            pandas.DataFrame: DataFrame con los datos de noticias preprocesados.
        """
        try:
            # Conectar a la base de datos DuckDB
            db_path = os.path.join(self.data_dir, 'news_database.duckdb')
            conn = duckdb.connect(db_path)
            
            # Consultar noticias para el símbolo específico
            query = f"""
                SELECT 
                    title, 
                    description, 
                    content, 
                    published_at, 
                    url, 
                    source_name,
                    relevance
                FROM news 
                WHERE symbol = '{symbol}' 
                ORDER BY published_at DESC
            """
            
            # Ejecutar consulta y obtener DataFrame
            news_df = conn.execute(query).fetchdf()
            
            # Cerrar conexión
            conn.close()
            
            if news_df.empty:
                logger.warning(f"No se encontraron noticias para {symbol} en la base de datos")
                return pd.DataFrame()
            
            # Preprocesar texto de noticias
            news_df['text'] = news_df.apply(
                lambda row: f"{row['title']} {row['description']} {row['content']}", 
                axis=1
            )
            
            # Limpiar texto
            news_df['text'] = news_df['text'].apply(self._clean_text)
            
            # Convertir fecha de publicación a datetime si no lo es ya
            if not pd.api.types.is_datetime64_any_dtype(news_df['published_at']):
                news_df['published_at'] = pd.to_datetime(news_df['published_at'])
            
            # Ordenar por fecha
            news_df = news_df.sort_values('published_at')
            
            # Guardar DataFrame preprocesado
            output_path = os.path.join(self.data_dir, 'preprocessed', f"{symbol}_news_preprocessed.csv")
            news_df.to_csv(output_path, index=False)
            
            logger.info(f"Datos de noticias preprocesados para {symbol}: {len(news_df)} noticias")
            
            return news_df
            
        except Exception as e:
            logger.error(f"Error al preprocesar datos de noticias para {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def _clean_text(self, text):
        """
        Limpia y preprocesa texto.
        
        Args:
            text (str): Texto a limpiar.
            
        Returns:
            str: Texto limpio.
        """
        if not isinstance(text, str) or pd.isna(text):
            return ""
        
        # Convertir a minúsculas
        text = text.lower()
        
        # Eliminar URLs
        text = re.sub(r'http\S+', '', text)
        
        # Eliminar caracteres especiales y números
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)
        
        # Tokenizar
        tokens = word_tokenize(text)
        
        # Eliminar stopwords y lematizar
        tokens = [self.lemmatizer.lemmatize(word) for word in tokens if word not in self.stop_words]
        
        # Unir tokens
        cleaned_text = ' '.join(tokens)
        
        return cleaned_text
    
    def _combine_data(self, stock_data, news_data, symbol):
        """
        Combina datos de precios y noticias.
        
        Args:
            stock_data (pandas.DataFrame): DataFrame con datos de precios.
            news_data (pandas.DataFrame): DataFrame con noticias.
            symbol (str): Símbolo de la empresa.
            
        Returns:
            pandas.DataFrame: DataFrame combinado.
        """
        if stock_data is None or news_data is None:
            return None
        
        # Agrupar noticias por día
        news_data['date'] = news_data.index.date
        daily_news = news_data.groupby('date').agg({
            'content': lambda x: ' '.join(x),
            'url': 'count'
        }).rename(columns={'url': 'news_count'})
        daily_news.index = pd.to_datetime(daily_news.index)
        
        # Convertir índice de stock_data a date para la unión
        stock_data_copy = stock_data.copy()
        stock_data_copy.index = pd.to_datetime(stock_data_copy.index)
        stock_data_copy['date'] = stock_data_copy.index.date
        stock_data_copy.index = pd.to_datetime(stock_data_copy.index)
        
        # Unir datos de precios con noticias
        combined = pd.merge(
            stock_data_copy,
            daily_news,
            left_index=True,
            right_index=True,
            how='left'
        )
        
        # Rellenar valores faltantes
        combined['news_count'] = combined['news_count'].fillna(0)
        combined['content'] = combined['content'].fillna('')
        
        # Guardar datos combinados
        combined_file_path = os.path.join(self.processed_dir, f"{symbol}_combined.csv")
        combined.to_csv(combined_file_path)
        
        return combined

if __name__ == "__main__":
    # Ruta al archivo de configuración
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'config.yaml'
    )
    
    # Crear instancia del preprocesador y preprocesar datos
    preprocessor = DataPreprocessor(config_path)
    preprocessed_data = preprocessor.preprocess_all_data()
