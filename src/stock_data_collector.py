#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para la recopilación de datos históricos de acciones.
Utiliza la API de Yahoo Finance para obtener datos históricos de precios.
"""
import os
import yaml
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import logging
import time

class StockDataCollector:
    """Clase para recopilar datos históricos de acciones."""
    
    def __init__(self, config_path=None):
        """
        Inicializa el recopilador de datos de acciones.
        
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
        os.makedirs(os.path.join(self.data_dir, 'stocks'), exist_ok=True)
        
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
    
    def _get_date_range(self):
        """
        Calcula el rango de fechas para los datos históricos.
        
        Returns:
            tuple: (fecha_inicio, fecha_fin) como objetos datetime.
        """
        end_date = datetime.now()
        
        # Obtener configuración del período histórico
        period_config = self.config.get('general', {}).get('historical_period', {})
        period_value = period_config.get('value', 1)
        period_unit = period_config.get('unit', 'years')
        
        # Validar valor
        if period_value < 1:
            period_value = 1
        
        # Calcular fecha de inicio según la unidad
        if period_unit == 'years':
            if period_value > 5:  # Limitar a 5 años máximo
                period_value = 5
            start_date = end_date - timedelta(days=365 * period_value)
        elif period_unit == 'months':
            if period_value > 60:  # Limitar a 60 meses máximo (5 años)
                period_value = 60
            start_date = end_date - timedelta(days=30 * period_value)
        elif period_unit == 'weeks':
            if period_value > 260:  # Limitar a 260 semanas máximo (5 años)
                period_value = 260
            start_date = end_date - timedelta(weeks=period_value)
        elif period_unit == 'days':
            if period_value > 1825:  # Limitar a 1825 días máximo (5 años)
                period_value = 1825
            start_date = end_date - timedelta(days=period_value)
        else:
            # Unidad no reconocida, usar años por defecto
            start_date = end_date - timedelta(days=365)
        
        return start_date, end_date
    
    def collect_historical_data(self, symbol=None):
        """
        Recopila datos históricos para todas las empresas configuradas o para un símbolo específico.
        
        Args:
            symbol (str, optional): Símbolo de la empresa. Si se proporciona, solo se recopilan datos
                                para esa empresa. Si es None, se recopilan datos para todas las empresas.
        
        Returns:
            dict: Datos históricos por símbolo de empresa.
        """
        logger = logging.getLogger(__name__)
        results = {}
        start_date, end_date = self._get_date_range()
        
        # Si se proporciona un símbolo específico, solo recopilar datos para esa empresa
        if symbol:
            logger.info(f"Recopilando datos históricos para {symbol}...")
            try:
                # Usar yfinance para obtener datos históricos
                ticker = yf.Ticker(symbol)
                stock_data = ticker.history(start=start_date, end=end_date, interval="1d")
                
                # Procesamiento y guardado de datos...
                
            except Exception as e:
                logger.error(f"Error al recopilar datos para {symbol}: {str(e)}")
            
            return results
        
        # Si no se proporciona un símbolo, recopilar datos para todas las empresas configuradas
        for company in self.config['companies']:
            # Si no se proporciona un símbolo, recopilar datos para todas las empresas configuradas

            symbol = company['symbol']
            
            logger.info(f"Recopilando datos históricos para {symbol}...")
            
            try:
                # Usar yfinance para obtener datos históricos
                ticker = yf.Ticker(symbol)
                stock_data = ticker.history(start=start_date, end=end_date, interval="1d")
                
                if not stock_data.empty:
                    # Renombrar columnas para mantener compatibilidad
                    stock_data.rename(columns={
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume',
                        'Adj Close': 'adjclose'
                    }, inplace=True)
                    
                    # Guardar los datos
                    results[symbol] = stock_data
                    self._save_stock_data(stock_data, symbol)
                else:
                    logger.warning(f"No se encontraron datos para {symbol}")
                
                # Esperar un poco para no sobrecargar la API
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error al recopilar datos para {symbol}: {str(e)}")
            
    def _process_stock_data(self, stock_data, symbol):
        """
        Procesa los datos de acciones obtenidos de la API.
        
        Args:
            stock_data (dict): Datos de acciones de la API.
            symbol (str): Símbolo de la empresa.
            
        Returns:
            pandas.DataFrame: DataFrame con los datos procesados.
        """
        try:
            # Extraer los datos relevantes
            chart_data = stock_data.get('chart', {})
            result = chart_data.get('result', [])
            
            if not result:
                print(f"No se encontraron datos para {symbol}")
                return None
            
            # Obtener timestamps y datos de precios
            timestamps = result[0].get('timestamp', [])
            indicators = result[0].get('indicators', {})
            quote = indicators.get('quote', [{}])[0]
            adjclose = indicators.get('adjclose', [{}])[0].get('adjclose', [])
            
            # Crear DataFrame
            df = pd.DataFrame({
                'timestamp': timestamps,
                'open': quote.get('open', []),
                'high': quote.get('high', []),
                'low': quote.get('low', []),
                'close': quote.get('close', []),
                'volume': quote.get('volume', []),
                'adjclose': adjclose
            })
            
            # Convertir timestamp a datetime
            df['date'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('date', inplace=True)
            df.drop('timestamp', axis=1, inplace=True)
            
            # Eliminar filas con valores nulos
            df.dropna(inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Error al procesar datos para {symbol}: {str(e)}")
            return None
    
    def _save_stock_data(self, df, symbol):
        """
        Guarda los datos de acciones en un archivo CSV.
        
        Args:
            df (pandas.DataFrame): DataFrame con los datos.
            symbol (str): Símbolo de la empresa.
        """
        file_path = os.path.join(self.data_dir, 'stocks', f"{symbol}_historical.csv")
        df.to_csv(file_path)
        print(f"Datos guardados en {file_path}")
    
    def get_stock_insights(self, symbol):
        """
        Obtiene información adicional sobre la acción.
        
        Args:
            symbol (str): Símbolo de la empresa.
            
        Returns:
            dict: Información adicional sobre la acción.
        """
        try:
            insights = self.client.call_api(
                'YahooFinance/get_stock_insights',
                query={'symbol': symbol}
            )
            
            # Guardar los insights en un archivo JSON
            import json
            file_path = os.path.join(self.data_dir, 'stocks', f"{symbol}_insights.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(insights, f, indent=2)
                
            return insights
        except Exception as e:
            print(f"Error al obtener insights para {symbol}: {str(e)}")
            return None
    
    def get_analyst_opinions(self, symbol):
        """
        Obtiene opiniones de analistas sobre la acción.
        
        Args:
            symbol (str): Símbolo de la empresa.
            
        Returns:
            dict: Opiniones de analistas sobre la acción.
        """
        try:
            opinions = self.client.call_api(
                'YahooFinance/get_stock_what_analyst_are_saying',
                query={'symbol': symbol}
            )
            
            # Guardar las opiniones en un archivo JSON
            import json
            file_path = os.path.join(self.data_dir, 'stocks', f"{symbol}_analyst_opinions.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(opinions, f, indent=2)
                
            return opinions
        except Exception as e:
            print(f"Error al obtener opiniones de analistas para {symbol}: {str(e)}")
            return None

if __name__ == "__main__":
    # Ruta al archivo de configuración
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'config.yaml'
    )
    
    # Crear instancia del recopilador y obtener datos históricos
    collector = StockDataCollector(config_path)
    historical_data = collector.collect_historical_data()
    
    # Obtener insights y opiniones de analistas para cada empresa
    for company in collector.config['companies']:
        symbol = company['symbol']
        collector.get_stock_insights(symbol)
        collector.get_analyst_opinions(symbol)
