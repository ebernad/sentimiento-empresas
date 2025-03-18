#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para la recopilación de noticias utilizando la API de noticias.
Integrado con DuckDB para almacenamiento eficiente.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
import time
import logging
from newsapi import NewsApiClient

# Importar módulos del proyecto
from config_manager import config_manager
from news_database import NewsDatabase

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("news_collector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NewsCollector:
    """Clase para recopilar noticias relacionadas con empresas."""
    
    def __init__(self):
        """
        Inicializa el recopilador de noticias.
        """
        # Obtener configuración
        self.news_api_config = config_manager.get_news_api_config()
        self.companies = config_manager.get_companies()
        period_config = config_manager.get_config('general','historical_period')
        self.historical_period_value = period_config.get('value', 1)
        self.historical_period_unit = period_config.get('unit', 'years')
        
        # Verificar API key
        self.api_key = self.news_api_config.get('api_key')
        if not self.api_key or self.api_key == "YOUR_NEWS_API_KEY":
            logger.warning("API key de noticias no configurada. La recopilación de noticias no funcionará.")
            self.api_key = None
        
        # Inicializar cliente de API de noticias
        if self.api_key:
            self.newsapi = NewsApiClient(api_key=self.api_key)
        else:
            self.newsapi = None
        
        # Inicializar base de datos
        self.db = NewsDatabase()
        
        # Crear directorios necesarios
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.news_dir = os.path.join(self.data_dir, 'news')
        os.makedirs(self.news_dir, exist_ok=True)
    
    def collect_historical_news(self):
        """
        Recopila noticias históricas para todas las empresas configuradas.
        
        Returns:
            dict: Resultados de la recopilación por símbolo de empresa.
        """
        if not self.api_key:
            logger.error("No se puede recopilar noticias sin una API key válida.")
            return {}
        
        results = {}
        
        for company in self.companies:
            symbol = company['symbol']
            name = company['name']
            
            logger.info(f"Recopilando noticias históricas para {name} ({symbol})...")
            
            try:
                # Calcular fecha de inicio (hace X años)
                end_date = datetime.now()
                if self.historical_period_unit == 'years':
                    start_date = end_date - timedelta(days=365 * self.historical_period_value)
                elif self.historical_period_unit == 'months':
                    start_date = end_date - timedelta(days=28 * self.historical_period_value)
                elif self.historical_period_unit == 'weeks':
                    start_date = end_date - timedelta(weeks=self.historical_period_value)
                elif self.historical_period_unit == 'days':
                    start_date = end_date - timedelta(days=self.historical_period_value)
                else:
                    # Unidad no reconocida, usar años por defecto
                    start_date = end_date - timedelta(days=365)
                
                # Recopilar noticias
                news_list = self._collect_news_for_period(symbol, name, start_date, end_date)
                
                # Guardar noticias en la base de datos
                total_processed, new_saved = self.db.save_news(news_list, symbol)
                
                results[symbol] = {
                    'total_collected': len(news_list),
                    'new_saved': new_saved
                }
                
                logger.info(f"Recopiladas {len(news_list)} noticias para {symbol}, {new_saved} nuevas guardadas en la base de datos")
                
                # Esperar para no sobrepasar límites de la API
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error al recopilar noticias para {symbol}: {str(e)}")
                results[symbol] = {'error': str(e)}
        
        return results
    
    def update_news(self, days_back=7):
        """
        Actualiza las noticias para todas las empresas configuradas.
        
        Args:
            days_back (int): Número de días hacia atrás para buscar noticias.
            
        Returns:
            dict: Resultados de la actualización por símbolo de empresa.
        """
        if not self.api_key:
            logger.error("No se puede actualizar noticias sin una API key válida.")
            return {}
        
        results = {}
        
        for company in self.companies:
            symbol = company['symbol']
            name = company['name']
            
            logger.info(f"Actualizando noticias para {name} ({symbol})...")
            
            try:
                # Calcular fechas
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                # Recopilar noticias
                news_list = self._collect_news_for_period(symbol, name, start_date, end_date)
                
                # Guardar noticias en la base de datos
                total_processed, new_saved = self.db.save_news(news_list, symbol)
                
                results[symbol] = {
                    'total_collected': len(news_list),
                    'new_saved': new_saved
                }
                
                logger.info(f"Actualizadas {len(news_list)} noticias para {symbol}, {new_saved} nuevas guardadas en la base de datos")
                
                # Esperar para no sobrepasar límites de la API
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error al actualizar noticias para {symbol}: {str(e)}")
                results[symbol] = {'error': str(e)}
        
        return results
    
    def _collect_news_for_period(self, symbol, company_name, start_date, end_date):
        """
        Recopila noticias para una empresa en un periodo específico.
        
        Args:
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
            start_date (datetime): Fecha de inicio.
            end_date (datetime): Fecha de fin.
            
        Returns:
            list: Lista de noticias recopiladas.
        """
        all_news = []
        
        # Convertir fechas a formato YYYY-MM-DD
        from_date = start_date.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')
        
        # Buscar por nombre de la empresa
        try:
            response = self.newsapi.get_everything(
                q=company_name,
                from_param=from_date,
                to=to_date,
                language='en',
                sort_by='relevancy',
                page_size=100
            )
            
            if response['status'] == 'ok':
                # Añadir noticias a la lista
                for article in response['articles']:
                    # Añadir timestamp de recopilación
                    article['collected_at'] = datetime.now().isoformat()
                    all_news.append(article)
        except Exception as e:
            logger.error(f"Error al buscar noticias por nombre de empresa: {str(e)}")
        
        # Buscar por símbolo de la empresa
        try:
            response = self.newsapi.get_everything(
                q=symbol,
                from_param=from_date,
                to=to_date,
                language='en',
                sort_by='relevancy',
                page_size=100
            )
            
            if response['status'] == 'ok':
                # Añadir noticias a la lista, evitando duplicados
                for article in response['articles']:
                    # Verificar si la noticia ya está en la lista
                    if not any(news['url'] == article['url'] for news in all_news):
                        # Añadir timestamp de recopilación
                        article['collected_at'] = datetime.now().isoformat()
                        all_news.append(article)
        except Exception as e:
            logger.error(f"Error al buscar noticias por símbolo: {str(e)}")
        
        return all_news

if __name__ == "__main__":
    # Crear instancia del recopilador y recopilar noticias
    collector = NewsCollector()
    
    # Verificar argumentos
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        # Actualizar noticias
        results = collector.update_news()
    else:
        # Recopilar noticias históricas
        results = collector.collect_historical_news()
    
    # Mostrar resultados
    for symbol, result in results.items():
        if 'error' in result:
            print(f"{symbol}: Error - {result['error']}")
        else:
            print(f"{symbol}: Recopiladas {result['total_collected']} noticias, {result['new_saved']} nuevas guardadas")
