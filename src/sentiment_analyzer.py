#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para el análisis de sentimiento de noticias.
Utiliza NLTK y TextBlob para analizar el sentimiento de las noticias.
"""

import os
import sys
import yaml
import json
import pandas as pd
import numpy as np
from datetime import datetime
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from textblob import TextBlob
import telegram

class SentimentAnalyzer:
    """Clase para analizar el sentimiento de noticias."""
    
    def __init__(self, config_path):
        """
        Inicializa el analizador de sentimiento.
        
        Args:
            config_path (str): Ruta al archivo de configuración YAML.
        """
        self.config = self._load_config(config_path)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.processed_dir = os.path.join(self.data_dir, 'processed')
        self.results_dir = os.path.join(self.data_dir, 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Inicializar analizadores de sentimiento
        self.sia = SentimentIntensityAnalyzer()
        
        # Configurar niveles de sentimiento
        self.sentiment_levels = 5  # Muy malo, malo, neutro, bueno, muy bueno
        
        # Configurar Telegram si está disponible
        self.telegram_bot = None
        self._setup_telegram()
    
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
    
    def _setup_telegram(self):
        """Configura el bot de Telegram si está disponible."""
        telegram_token = self.config['general'].get('telegram_token')
        telegram_chat_id = self.config['general'].get('telegram_chat_id')
        
        if telegram_token and telegram_token != "YOUR_TELEGRAM_TOKEN" and \
           telegram_chat_id and telegram_chat_id != "YOUR_CHAT_ID":
            try:
                self.telegram_bot = telegram.Bot(token=telegram_token)
                self.telegram_chat_id = telegram_chat_id
                print("Bot de Telegram configurado correctamente")
            except Exception as e:
                print(f"Error al configurar el bot de Telegram: {str(e)}")
                self.telegram_bot = None
    
    def analyze_all_companies(self):
        """
        Analiza el sentimiento para todas las empresas configuradas.
        
        Returns:
            dict: Resultados del análisis de sentimiento por símbolo de empresa.
        """
        results = {}
        
        for company in self.config['companies']:
            symbol = company['symbol']
            name = company['name']
            
            print(f"Analizando sentimiento para {name} ({symbol})...")
            
            try:
                # Cargar datos combinados
                combined_data = self._load_combined_data(symbol)
                
                if combined_data is not None:
                    # Analizar sentimiento
                    sentiment_data = self._analyze_sentiment(combined_data, symbol)
                    results[symbol] = sentiment_data
                    
                    # Enviar resumen por Telegram
                    self._send_sentiment_summary(sentiment_data, symbol, name)
                
            except Exception as e:
                print(f"Error al analizar sentimiento para {symbol}: {str(e)}")
        
        return results
    
    def _load_combined_data(self, symbol):
        """
        Carga los datos combinados de precios y noticias.
        
        Args:
            symbol (str): Símbolo de la empresa.
            
        Returns:
            pandas.DataFrame: DataFrame con datos combinados.
        """
        file_path = os.path.join(self.processed_dir, f"{symbol}_combined.csv")
        
        if not os.path.exists(file_path):
            print(f"No se encontraron datos combinados para {symbol}")
            return None
        
        # Cargar datos
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        
        return df
    
    def _analyze_sentiment(self, df, symbol):
        """
        Analiza el sentimiento de las noticias.
        
        Args:
            df (pandas.DataFrame): DataFrame con datos combinados.
            symbol (str): Símbolo de la empresa.
            
        Returns:
            pandas.DataFrame: DataFrame con resultados del análisis de sentimiento.
        """
        # Crear copia para no modificar el original
        sentiment_df = df.copy()
        
        # Inicializar columnas de sentimiento
        sentiment_df['vader_score'] = 0.0
        sentiment_df['textblob_score'] = 0.0
        sentiment_df['combined_score'] = 0.0
        sentiment_df['sentiment_level'] = 'neutro'
        
        # Analizar sentimiento solo para filas con contenido
        for idx, row in sentiment_df.iterrows():
            if row['content'] and isinstance(row['content'], str):
                # Análisis con VADER
                vader_scores = self.sia.polarity_scores(row['content'])
                vader_compound = vader_scores['compound']
                
                # Análisis con TextBlob
                blob = TextBlob(row['content'])
                textblob_polarity = blob.sentiment.polarity
                
                # Combinar puntuaciones (promedio)
                combined_score = (vader_compound + textblob_polarity) / 2
                
                # Guardar puntuaciones
                sentiment_df.at[idx, 'vader_score'] = vader_compound
                sentiment_df.at[idx, 'textblob_score'] = textblob_polarity
                sentiment_df.at[idx, 'combined_score'] = combined_score
                
                # Asignar nivel de sentimiento
                sentiment_df.at[idx, 'sentiment_level'] = self._get_sentiment_level(combined_score)
        
        # Guardar resultados
        results_file_path = os.path.join(self.results_dir, f"{symbol}_sentiment.csv")
        sentiment_df.to_csv(results_file_path)
        
        return sentiment_df
    
    def _get_sentiment_level(self, score):
        """
        Convierte una puntuación de sentimiento a un nivel de sentimiento.
        
        Args:
            score (float): Puntuación de sentimiento entre -1 y 1.
            
        Returns:
            str: Nivel de sentimiento (muy_malo, malo, neutro, bueno, muy_bueno).
        """
        if score <= -0.6:
            return "muy_malo"
        elif score <= -0.2:
            return "malo"
        elif score <= 0.2:
            return "neutro"
        elif score <= 0.6:
            return "bueno"
        else:
            return "muy_bueno"
    
    def _send_sentiment_summary(self, sentiment_df, symbol, company_name):
        """
        Envía un resumen del análisis de sentimiento por Telegram.
        
        Args:
            sentiment_df (pandas.DataFrame): DataFrame con resultados del análisis.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
        """
        if self.telegram_bot is None:
            return
        
        try:
            # Obtener datos recientes (últimos 7 días)
            recent_data = sentiment_df.iloc[-7:]
            
            # Contar ocurrencias de cada nivel de sentimiento
            sentiment_counts = recent_data['sentiment_level'].value_counts()
            
            # Calcular sentimiento promedio
            avg_sentiment = recent_data['combined_score'].mean()
            overall_sentiment = self._get_sentiment_level(avg_sentiment)
            
            # Crear mensaje
            message = f"📊 *Análisis de Sentimiento para {company_name} ({symbol})*\n\n"
            message += f"Sentimiento general: {self._translate_sentiment(overall_sentiment)}\n"
            message += f"Puntuación promedio: {avg_sentiment:.2f}\n\n"
            
            message += "Distribución de sentimiento (últimos 7 días):\n"
            for level in ["muy_bueno", "bueno", "neutro", "malo", "muy_malo"]:
                count = sentiment_counts.get(level, 0)
                message += f"- {self._translate_sentiment(level)}: {count}\n"
            
            # Tendencia de precio
            if 'close' in recent_data.columns:
                price_change = (recent_data['close'].iloc[-1] / recent_data['close'].iloc[0] - 1) * 100
                message += f"\nCambio de precio (7 días): {price_change:.2f}%\n"
            
            # Predicción basada en sentimiento
            message += f"\nPredicción basada en sentimiento: {self._get_prediction(overall_sentiment)}"
            
            # Enviar mensaje
            self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            print(f"Resumen de sentimiento enviado por Telegram para {symbol}")
            
        except Exception as e:
            print(f"Error al enviar resumen por Telegram: {str(e)}")
    
    def _translate_sentiment(self, sentiment_level):
        """
        Traduce el nivel de sentimiento a un formato más legible.
        
        Args:
            sentiment_level (str): Nivel de sentimiento.
            
        Returns:
            str: Nivel de sentimiento traducido.
        """
        translations = {
            "muy_malo": "Muy Negativo ⚠️",
            "malo": "Negativo 📉",
            "neutro": "Neutro ⚖️",
            "bueno": "Positivo 📈",
            "muy_bueno": "Muy Positivo 🚀"
        }
        
        return translations.get(sentiment_level, sentiment_level)
    
    def _get_prediction(self, sentiment_level):
        """
        Genera una predicción basada en el nivel de sentimiento.
        
        Args:
            sentiment_level (str): Nivel de sentimiento.
            
        Returns:
            str: Predicción de tendencia.
        """
        predictions = {
            "muy_malo": "Posible caída significativa ⚠️📉",
            "malo": "Tendencia bajista probable 📉",
            "neutro": "Sin tendencia clara ⚖️",
            "bueno": "Tendencia alcista probable 📈",
            "muy_bueno": "Posible subida significativa 🚀📈"
        }
        
        return predictions.get(sentiment_level, "Sin predicción disponible")

if __name__ == "__main__":
    # Ruta al archivo de configuración
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'config.yaml'
    )
    
    # Crear instancia del analizador y analizar sentimiento
    analyzer = SentimentAnalyzer(config_path)
    sentiment_results = analyzer.analyze_all_companies()
