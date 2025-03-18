#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para el análisis de sentimiento de noticias utilizando ChatGPT con contexto histórico.
Integrado con DuckDB para acceso eficiente al histórico de noticias y seguimiento de costes.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import openai
import time
import telegram
import logging

# Importar módulos del proyecto
from config_manager import config_manager
from news_database import NewsDatabase
from openai_cost_tracker import cost_tracker

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("chatgpt_sentiment.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ChatGPTSentimentAnalyzer:
    """Clase para analizar el sentimiento de noticias utilizando ChatGPT con contexto histórico."""
    
    def __init__(self):
        """
        Inicializa el analizador de sentimiento con ChatGPT.
        """
        # Obtener configuraciones
        self.openai_config = config_manager.get_openai_config()
        self.telegram_config = config_manager.get_telegram_config()
        self.companies = config_manager.get_companies()
        
        # Verificar que la API key de OpenAI está configurada
        self.api_key = self.openai_config.get('api_key')
        if not self.api_key or self.api_key == "YOUR_OPENAI_API_KEY":
            logger.warning("API key de OpenAI no configurada. El análisis de sentimiento con ChatGPT no funcionará.")
            self.api_key = None
        
        # Configurar el modelo de ChatGPT a utilizar
        self.model = self.openai_config.get('model', "gpt-3.5-turbo")
        
        # Configurar el rango de contexto histórico
        self.historical_context_range = self.openai_config.get('historical_context_range', "week")
        
        # Inicializar base de datos
        self.db = NewsDatabase()
        
        # Crear directorios necesarios
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.results_dir = os.path.join(self.data_dir, 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Configurar Telegram si está disponible
        self.telegram_bot = None
        self._setup_telegram()
    
    def _setup_telegram(self):
        """Configura el bot de Telegram si está disponible."""
        telegram_token = self.telegram_config.get('token')
        telegram_chat_id = self.telegram_config.get('chat_id')
        
        if telegram_token and telegram_token != "YOUR_TELEGRAM_TOKEN" and \
           telegram_chat_id and telegram_chat_id != "YOUR_CHAT_ID":
            try:
                self.telegram_bot = telegram.Bot(token=telegram_token)
                self.telegram_chat_id = telegram_chat_id
                logger.info("Bot de Telegram configurado correctamente")
            except Exception as e:
                logger.error(f"Error al configurar el bot de Telegram: {str(e)}")
                self.telegram_bot = None
    
    def analyze_all_companies(self):
        """
        Analiza el sentimiento para todas las empresas configuradas.
        
        Returns:
            dict: Resultados del análisis de sentimiento por símbolo de empresa.
        """
        if not self.api_key:
            logger.error("No se puede realizar el análisis de sentimiento sin una API key de OpenAI válida.")
            return {}
        
        results = {}
        
        for company in self.companies:
            symbol = company['symbol']
            name = company['name']
            
            logger.info(f"Analizando sentimiento para {name} ({symbol})...")
            
            try:
                # Cargar datos combinados
                combined_data = self._load_combined_data(symbol)
                
                if combined_data is not None and not combined_data.empty:
                    # Analizar sentimiento
                    sentiment_data = self._analyze_sentiment(combined_data, symbol, name)
                    results[symbol] = sentiment_data
                    
                    # Enviar resumen por Telegram
                    self._send_sentiment_summary(sentiment_data, symbol, name)
                else:
                    logger.warning(f"No se encontraron datos combinados para {symbol}")
                
            except Exception as e:
                logger.error(f"Error al analizar sentimiento para {symbol}: {str(e)}")
        
        return results
    
    def _load_combined_data(self, symbol):
        """
        Carga los datos combinados de precios y noticias.
        
        Args:
            symbol (str): Símbolo de la empresa.
            
        Returns:
            pandas.DataFrame: DataFrame con datos combinados.
        """
        processed_dir = os.path.join(self.data_dir, 'processed')
        file_path = os.path.join(processed_dir, f"{symbol}_combined.csv")
        
        if not os.path.exists(file_path):
            logger.warning(f"No se encontraron datos combinados para {symbol}")
            return None
        
        # Cargar datos
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        
        return df
    
    def _analyze_sentiment(self, df, symbol, company_name):
        """
        Analiza el sentimiento de las noticias utilizando ChatGPT con contexto histórico.
        
        Args:
            df (pandas.DataFrame): DataFrame con datos combinados.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
            
        Returns:
            pandas.DataFrame: DataFrame con resultados del análisis de sentimiento.
        """
        # Crear copia para no modificar el original
        sentiment_df = df.copy()
        
        # Inicializar columnas de sentimiento
        sentiment_df['chatgpt_score'] = 0.0
        sentiment_df['sentiment_level'] = 'neutro'
        sentiment_df['sentiment_explanation'] = ''
        
        # Contador para limitar las llamadas a la API en desarrollo
        api_calls = 0
        max_api_calls = self.openai_config.get('max_daily_calls', 100)
        
        # Analizar sentimiento solo para filas con contenido
        for idx, row in sentiment_df.iterrows():
            if row['content'] and isinstance(row['content'], str) and api_calls < max_api_calls:
                # Obtener fecha en formato legible
                current_date = pd.to_datetime(idx)
                date_str = current_date.strftime('%Y-%m-%d')
                
                # Obtener contexto histórico desde la base de datos
                context_df = self.db.get_historical_context(symbol, current_date, self.historical_context_range)
                historical_context = self.db.format_context_for_prompt(context_df)
                
                # Analizar sentimiento con ChatGPT
                try:
                    sentiment_result = self._analyze_with_chatgpt(
                        row['content'], 
                        company_name, 
                        symbol, 
                        date_str,
                        historical_context
                    )
                    
                    # Incrementar contador de llamadas a la API
                    api_calls += 1
                    
                    # Guardar resultados
                    sentiment_df.at[idx, 'chatgpt_score'] = sentiment_result['score']
                    sentiment_df.at[idx, 'sentiment_level'] = sentiment_result['level']
                    sentiment_df.at[idx, 'sentiment_explanation'] = sentiment_result['explanation']
                    
                    # Esperar para no sobrepasar límites de la API
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error al analizar sentimiento con ChatGPT: {str(e)}")
                    # Usar valores neutros en caso de error
                    sentiment_df.at[idx, 'chatgpt_score'] = 0.0
                    sentiment_df.at[idx, 'sentiment_level'] = 'neutro'
                    sentiment_df.at[idx, 'sentiment_explanation'] = 'Error en el análisis'
        
        # Guardar resultados
        results_file_path = os.path.join(self.results_dir, f"{symbol}_sentiment_chatgpt.csv")
        sentiment_df.to_csv(results_file_path)
        
        logger.info(f"Análisis de sentimiento completado para {symbol}. Realizadas {api_calls} llamadas a la API.")
        
        return sentiment_df
    
    def _analyze_with_chatgpt(self, content, company_name, symbol, date_str, historical_context):
        """
        Analiza el sentimiento de una noticia utilizando ChatGPT con contexto histórico.
        
        Args:
            content (str): Contenido de la noticia.
            company_name (str): Nombre de la empresa.
            symbol (str): Símbolo de la empresa.
            date_str (str): Fecha de la noticia.
            historical_context (str): Contexto histórico de noticias anteriores.
            
        Returns:
            dict: Resultado del análisis con puntuación, nivel y explicación.
        """
        # Preparar el prompt para ChatGPT
        prompt = f"""
        Analiza el sentimiento de la siguiente noticia sobre {company_name} ({symbol}) del {date_str} 
        desde la perspectiva de un inversor en el mercado de valores.
        
        {historical_context}
        
        Noticia actual ({date_str}): "{content}"
        
        Teniendo en cuenta el contexto histórico proporcionado, clasifica el sentimiento en uno de estos cinco niveles: 
        muy_malo, malo, neutro, bueno, muy_bueno.
        
        Asigna también una puntuación numérica entre -1.0 (muy negativo) y 1.0 (muy positivo).
        
        Explica brevemente por qué la noticia podría afectar positiva o negativamente al precio de la acción,
        considerando el contexto histórico cuando sea relevante.
        
        Responde en formato JSON con los siguientes campos:
        - level: el nivel de sentimiento (muy_malo, malo, neutro, bueno, muy_bueno)
        - score: la puntuación numérica entre -1.0 y 1.0
        - explanation: explicación breve (máximo 100 palabras)
        """
        
        # Realizar la llamada a la API de OpenAI
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Eres un analista financiero experto que evalúa el impacto de noticias en el precio de las acciones."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.openai_config.get('temperature', 0.3),
            "max_tokens": self.openai_config.get('max_tokens', 500)
        }
        
        openai.api_key = self.api_key
        response = openai.ChatCompletion.create(
        model=self.model,
        messages=messages,
        temperature=self.openai_config.get('temperature', 0.3),
        max_tokens=self.openai_config.get('max_tokens', 500)
)
        
        if response.status_code != 200:
            logger.error(f"Error en la API de OpenAI: {response.status_code} - {response.text}")
            # Registrar error en el seguimiento de costes
            cost_tracker.track_request(
                prompt=prompt,
                completion="Error: " + response.text,
                model=self.model,
                symbol=symbol,
                news_date=datetime.strptime(date_str, '%Y-%m-%d') if date_str else None,
                status="error"
            )
            raise Exception(f"Error en la API de OpenAI: {response.status_code}")
        
        # Extraer la respuesta
        response_data = response.json()
        response_text = response_data['choices'][0]['message']['content']
        
        # Registrar la llamada en el seguimiento de costes
        cost_tracker.track_request(
            prompt=prompt,
            completion=response_text,
            model=self.model,
            symbol=symbol,
            news_date=datetime.strptime(date_str, '%Y-%m-%d') if date_str else None,
            status="success"
        )
        
        # Intentar parsear la respuesta como JSON
        try:
            # Extraer solo la parte JSON de la respuesta
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
            else:
                # Si no se encuentra formato JSON, intentar extraer la información manualmente
                result = self._extract_sentiment_manually(response_text)
                
            # Verificar que los campos necesarios estén presentes
            if 'level' not in result or 'score' not in result:
                raise ValueError("Respuesta incompleta")
                
            return result
            
        except Exception as e:
            logger.error(f"Error al parsear respuesta de ChatGPT: {str(e)}")
            logger.error(f"Respuesta recibida: {response_text}")
            
            # Devolver un resultado por defecto en caso de error
            return {
                "level": "neutro",
                "score": 0.0,
                "explanation": "No se pudo analizar la respuesta de ChatGPT."
            }
    
    def _extract_sentiment_manually(self, text):
        """
        Extrae manualmente la información de sentimiento de la respuesta de ChatGPT
        cuando no está en formato JSON.
        
        Args:
            text (str): Texto de respuesta de ChatGPT.
            
        Returns:
            dict: Resultado del análisis con puntuación, nivel y explicación.
        """
        result = {
            "level": "neutro",
            "score": 0.0,
            "explanation": ""
        }
        
        # Buscar nivel de sentimiento
        level_keywords = {
            "muy_malo": ["muy negativo", "muy malo", "muy_malo"],
            "malo": ["negativo", "malo"],
            "neutro": ["neutro", "neutral"],
            "bueno": ["positivo", "bueno"],
            "muy_bueno": ["muy positivo", "muy bueno", "muy_bueno"]
        }
        
        for level, keywords in level_keywords.items():
            for keyword in keywords:
                if keyword in text.lower():
                    result["level"] = level
                    break
        
        # Buscar puntuación
        import re
        score_matches = re.findall(r"[-+]?\d*\.\d+|\d+", text)
        for match in score_matches:
            try:
                score = float(match)
                if -1.0 <= score <= 1.0:
                    result["score"] = score
                    break
            except:
                continue
        
        # Extraer explicación
        explanation_markers = ["explicación:", "explanation:", "porque", "ya que", "debido a"]
        for marker in explanation_markers:
            if marker in text.lower():
                parts = text.lower().split(marker)
                if len(parts) > 1:
                    result["explanation"] = parts[1].strip()[:200]  # Limitar a 200 caracteres
                    break
        
        if not result["explanation"]:
            # Si no se encuentra un marcador específico, tomar el último párrafo
            paragraphs = text.split('\n')
            non_empty_paragraphs = [p for p in paragraphs if p.strip()]
            if non_empty_paragraphs:
                result["explanation"] = non_empty_paragraphs[-1].strip()[:200]
        
        return result
    
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
            avg_sentiment = recent_data['chatgpt_score'].mean()
            
            # Determinar el nivel general basado en el promedio
            if avg_sentiment <= -0.6:
                overall_sentiment = "muy_malo"
            elif avg_sentiment <= -0.2:
                overall_sentiment = "malo"
            elif avg_sentiment <= 0.2:
                overall_sentiment = "neutro"
            elif avg_sentiment <= 0.6:
                overall_sentiment = "bueno"
            else:
                overall_sentiment = "muy_bueno"
            
            # Crear mensaje
            message = f"📊 *Análisis de Sentimiento con ChatGPT para {company_name} ({symbol})*\n\n"
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
            
            # Añadir explicación de la noticia más reciente con sentimiento
            recent_with_explanation = recent_data[recent_data['sentiment_explanation'] != '']
            if not recent_with_explanation.empty:
                latest = recent_with_explanation.iloc[-1]
                message += f"\n\n*Última noticia analizada ({latest.name.strftime('%Y-%m-%d')}):*\n"
                message += f"Sentimiento: {self._translate_sentiment(latest['sentiment_level'])}\n"
                message += f"Explicación: {latest['sentiment_explanation']}"
            
            # Añadir información de costes
            total_cost = cost_tracker.get_total_cost()
            message += f"\n\n*Información de costes de OpenAI:*\n"
            message += f"Coste total acumulado: ${total_cost:.4f} USD"
            
            # Enviar mensaje
            self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Resumen de sentimiento enviado por Telegram para {symbol}")
            
        except Exception as e:
            logger.error(f"Error al enviar resumen por Telegram: {str(e)}")
    
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
    # Crear instancia del analizador y analizar sentimiento
    analyzer = ChatGPTSentimentAnalyzer()
    sentiment_results = analyzer.analyze_all_companies()
    
    # Generar informe de costes
    cost_report = cost_tracker.generate_cost_report()
    print(f"Informe de costes generado en: {cost_report}")
