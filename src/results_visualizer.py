#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para la visualización de resultados del análisis de sentimiento y correlación.
Genera gráficos interactivos y dashboards para visualizar los resultados.
"""

import os
import sys
import yaml
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.ticker as mtick

class ResultsVisualizer:
    """Clase para visualizar los resultados del análisis de sentimiento y correlación."""
    
    def __init__(self, config_path):
        """
        Inicializa el visualizador de resultados.
        
        Args:
            config_path (str): Ruta al archivo de configuración YAML.
        """
        self.config = self._load_config(config_path)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.results_dir = os.path.join(self.data_dir, 'results')
        self.correlation_dir = os.path.join(self.results_dir, 'correlation')
        self.visualization_dir = os.path.join(self.results_dir, 'visualization')
        os.makedirs(self.visualization_dir, exist_ok=True)
        
        # Configurar colores para visualización
        self.colors = self.config['visualization']['colors']
        
        # Configurar estilo de seaborn
        sns.set(style="whitegrid")
    
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
    
    def visualize_all_companies(self):
        """
        Genera visualizaciones para todas las empresas configuradas.
        
        Returns:
            dict: Rutas a las visualizaciones generadas por símbolo de empresa.
        """
        results = {}
        
        for company in self.config['companies']:
            symbol = company['symbol']
            name = company['name']
            
            print(f"Generando visualizaciones para {name} ({symbol})...")
            
            try:
                # Cargar datos de sentimiento
                sentiment_data = self._load_sentiment_data(symbol)
                
                if sentiment_data is not None:
                    # Generar visualizaciones
                    visualization_paths = self._generate_visualizations(sentiment_data, symbol, name)
                    results[symbol] = visualization_paths
                
            except Exception as e:
                print(f"Error al generar visualizaciones para {symbol}: {str(e)}")
        
        # Generar visualización comparativa de todas las empresas
        try:
            comparative_path = self._generate_comparative_visualization()
            results['comparative'] = comparative_path
        except Exception as e:
            print(f"Error al generar visualización comparativa: {str(e)}")
        
        return results
    
    def _load_sentiment_data(self, symbol):
        """
        Carga los datos de sentimiento.
        
        Args:
            symbol (str): Símbolo de la empresa.
            
        Returns:
            pandas.DataFrame: DataFrame con datos de sentimiento.
        """
        file_path = os.path.join(self.results_dir, f"{symbol}_sentiment.csv")
        
        if not os.path.exists(file_path):
            print(f"No se encontraron datos de sentimiento para {symbol}")
            return None
        
        # Cargar datos
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        
        return df
    
    def _generate_visualizations(self, df, symbol, company_name):
        """
        Genera visualizaciones para una empresa específica.
        
        Args:
            df (pandas.DataFrame): DataFrame con datos de sentimiento.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
            
        Returns:
            dict: Rutas a las visualizaciones generadas.
        """
        visualization_paths = {}
        
        # 1. Gráfico de líneas: Evolución del precio y sentimiento a lo largo del tiempo
        time_series_path = self._create_time_series_plot(df, symbol, company_name)
        visualization_paths['time_series'] = time_series_path
        
        # 2. Gráfico de calor: Mapa de calor del sentimiento a lo largo del tiempo
        heatmap_path = self._create_sentiment_heatmap(df, symbol, company_name)
        visualization_paths['heatmap'] = heatmap_path
        
        # 3. Gráfico de distribución: Distribución de sentimientos
        distribution_path = self._create_sentiment_distribution(df, symbol, company_name)
        visualization_paths['distribution'] = distribution_path
        
        # 4. Gráfico de rendimientos: Rendimientos por nivel de sentimiento
        returns_path = self._create_returns_by_sentiment(df, symbol, company_name)
        visualization_paths['returns'] = returns_path
        
        # 5. Gráfico de volatilidad: Volatilidad por nivel de sentimiento
        volatility_path = self._create_volatility_by_sentiment(df, symbol, company_name)
        visualization_paths['volatility'] = volatility_path
        
        return visualization_paths
    
    def _create_time_series_plot(self, df, symbol, company_name):
        """
        Crea un gráfico de líneas con la evolución del precio y sentimiento.
        
        Args:
            df (pandas.DataFrame): DataFrame con datos de sentimiento.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
            
        Returns:
            str: Ruta al gráfico generado.
        """
        plt.figure(figsize=(14, 10))
        
        # Crear dos ejes y para diferentes escalas
        ax1 = plt.gca()
        ax2 = ax1.twinx()
        
        # Graficar precio de cierre
        ax1.plot(df.index, df['close'], 'b-', linewidth=2, label='Precio de Cierre')
        ax1.set_xlabel('Fecha', fontsize=12)
        ax1.set_ylabel('Precio de Cierre ($)', color='b', fontsize=12)
        ax1.tick_params(axis='y', labelcolor='b')
        
        # Formatear eje x para mostrar fechas de manera legible
        ax1.xaxis.set_major_locator(mdates.MonthLocator())
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        plt.xticks(rotation=45)
        
        # Graficar sentimiento
        sentiment_color = 'r'
        ax2.plot(df.index, df['combined_score'], color=sentiment_color, linewidth=2, label='Puntuación de Sentimiento')
        ax2.set_ylabel('Puntuación de Sentimiento', color=sentiment_color, fontsize=12)
        ax2.tick_params(axis='y', labelcolor=sentiment_color)
        
        # Añadir línea horizontal en y=0 para el sentimiento
        ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.7)
        
        # Añadir título
        plt.title(f'Evolución del Precio y Sentimiento para {company_name} ({symbol})', fontsize=14)
        
        # Añadir leyendas
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        # Añadir grid
        ax1.grid(True, alpha=0.3)
        
        # Guardar gráfico
        plt.tight_layout()
        output_path = os.path.join(self.visualization_dir, f"{symbol}_time_series.png")
        plt.savefig(output_path, dpi=300)
        plt.close()
        
        return output_path
    
    def _create_sentiment_heatmap(self, df, symbol, company_name):
        """
        Crea un mapa de calor del sentimiento a lo largo del tiempo.
        
        Args:
            df (pandas.DataFrame): DataFrame con datos de sentimiento.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
            
        Returns:
            str: Ruta al gráfico generado.
        """
        # Preparar datos para el mapa de calor
        # Resamplear los datos por semana y calcular el sentimiento promedio
        weekly_sentiment = df.resample('W').agg({
            'combined_score': 'mean',
            'close': 'last'
        })
        
        # Crear una matriz para el mapa de calor
        # Filas: semanas, Columnas: meses
        weekly_sentiment['year'] = weekly_sentiment.index.year
        weekly_sentiment['month'] = weekly_sentiment.index.month
        weekly_sentiment['week'] = weekly_sentiment.index.isocalendar().week
        
        # Pivotar para crear la matriz
        pivot_table = weekly_sentiment.pivot_table(
            index='week', 
            columns=['year', 'month'], 
            values='combined_score',
            aggfunc='mean'
        )
        
        # Crear etiquetas para los meses
        month_labels = []
        for year, month in pivot_table.columns.levels[0].zip(pivot_table.columns.levels[1]):
            month_name = {
                1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
            }[month]
            month_labels.append(f"{month_name} {year}")
        
        # Crear figura
        plt.figure(figsize=(16, 10))
        
        # Crear mapa de colores personalizado
        colors = [self.colors['muy_malo'], self.colors['malo'], self.colors['neutro'], 
                 self.colors['bueno'], self.colors['muy_bueno']]
        cmap = LinearSegmentedColormap.from_list('sentiment_cmap', colors, N=100)
        
        # Crear mapa de calor
        ax = sns.heatmap(
            pivot_table, 
            cmap=cmap,
            center=0,
            linewidths=0.5,
            linecolor='gray',
            cbar_kws={'label': 'Puntuación de Sentimiento'}
        )
        
        # Configurar etiquetas
        ax.set_xlabel('Mes', fontsize=12)
        ax.set_ylabel('Semana del Año', fontsize=12)
        ax.set_title(f'Mapa de Calor del Sentimiento para {company_name} ({symbol})', fontsize=14)
        
        # Ajustar etiquetas del eje x
        ax.set_xticklabels(month_labels, rotation=45, ha='right')
        
        # Guardar gráfico
        plt.tight_layout()
        output_path = os.path.join(self.visualization_dir, f"{symbol}_sentiment_heatmap.png")
        plt.savefig(output_path, dpi=300)
        plt.close()
        
        return output_path
    
    def _create_sentiment_distribution(self, df, symbol, company_name):
        """
        Crea un gráfico de distribución de sentimientos.
        
        Args:
            df (pandas.DataFrame): DataFrame con datos de sentimiento.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
            
        Returns:
            str: Ruta al gráfico generado.
        """
        plt.figure(figsize=(14, 8))
        
        # Contar ocurrencias de cada nivel de sentimiento
        sentiment_counts = df['sentiment_level'].value_counts().reindex(
            ['muy_malo', 'malo', 'neutro', 'bueno', 'muy_bueno']
        )
        
        # Crear paleta de colores
        colors = [self.colors['muy_malo'], self.colors['malo'], self.colors['neutro'], 
                 self.colors['bueno'], self.colors['muy_bueno']]
        
        # Crear gráfico de barras
        ax = sns.barplot(
            x=sentiment_counts.index,
            y=sentiment_counts.values,
            palette=colors
        )
        
        # Añadir etiquetas
        ax.set_xlabel('Nivel de Sentimiento', fontsize=12)
        ax.set_ylabel('Número de Días', fontsize=12)
        ax.set_title(f'Distribución de Sentimientos para {company_name} ({symbol})', fontsize=14)
        
        # Cambiar etiquetas del eje x
        ax.set_xticklabels(['Muy Negativo', 'Negativo', 'Neutro', 'Positivo', 'Muy Positivo'])
        
        # Añadir valores en las barras
        for i, v in enumerate(sentiment_counts.values):
            ax.text(i, v + 0.5, str(v), ha='center')
        
        # Guardar gráfico
        plt.tight_layout()
        output_path = os.path.join(self.visualization_dir, f"{symbol}_sentiment_distribution.png")
        plt.savefig(output_path, dpi=300)
        plt.close()
        
        return output_path
    
    def _create_returns_by_sentiment(self, df, symbol, company_name):
        """
        Crea un gráfico de rendimientos por nivel de sentimiento.
        
        Args:
            df (pandas.DataFrame): DataFrame con datos de sentimiento.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
            
        Returns:
            str: Ruta al gráfico generado.
        """
        # Crear copia para no modificar el original
        returns_df = df.copy()
        
        # Calcular rendimientos futuros (1, 3 y 5 días)
        for days in [1, 3, 5]:
            returns_df[f'return_{days}d'] = returns_df['close'].pct_change(periods=days).shift(-days) * 100
        
        # Eliminar filas con valores NaN
        returns_df.dropna(inplace=True)
        
        # Calcular rendimientos promedio por nivel de sentimiento
        returns_by_sentiment = returns_df.groupby('sentiment_level').agg({
            'return_1d': 'mean',
            'return_3d': 'mean',
            'return_5d': 'mean'
        })
        
        # Reordenar índice
        returns_by_sentiment = returns_by_sentiment.reindex(['muy_malo', 'malo', 'neutro', 'bueno', 'muy_bueno'])
        
        # Crear figura
        plt.figure(figsize=(14, 8))
        
        # Crear paleta de colores
        colors = [self.colors['muy_malo'], self.colors['malo'], self.colors['neutro'], 
                 self.colors['bueno'], self.colors['muy_bueno']]
        
        # Configurar posiciones de las barras
        x = np.arange(len(returns_by_sentiment.index))
        width = 0.25
        
        # Crear barras
        plt.bar(x - width, returns_by_sentiment['return_1d'], width, label='1 Día', color=colors, alpha=0.7)
        plt.bar(x, returns_by_sentiment['return_3d'], width, label='3 Días', color=colors, alpha=0.85)
        plt.bar(x + width, returns_by_sentiment['return_5d'], width, label='5 Días', color=colors)
        
        # Añadir línea horizontal en y=0
        plt.axhline(y=0, color='gray', linestyle='--', alpha=0.7)
        
        # Añadir etiquetas y título
        plt.xlabel('Nivel de Sentimiento', fontsize=12)
        plt.ylabel('Rendimiento Promedio (%)', fontsize=12)
        plt.title(f'Rendimientos por Nivel de Sentimiento para {company_name} ({symbol})', fontsize=14)
        plt.xticks(x, ['Muy Negativo', 'Negativo', 'Neutro', 'Positivo', 'Muy Positivo'])
        plt.legend()
        
        # Formatear eje y como porcentaje
        plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(decimals=1))
        
        # Añadir valores en las barras para 3 días
        for i, v in enumerate(returns_by_sentiment['return_3d']):
            plt.text(i, v + 0.2, f"{v:.2f}%", ha='center')
        
        # Guardar gráfico
        plt.tight_layout()
        output_path = os.path.join(self.visualization_dir, f"{symbol}_returns_by_sentiment.png")
        plt.savefig(output_path, dpi=300)
        plt.close()
        
        return output_path
    
    def _create_volatility_by_sentiment(self, df, symbol, company_name):
        """
        Crea un gráfico de volatilidad por nivel de sentimiento.
        
        Args:
            df (pandas.DataFrame): DataFrame con datos de sentimiento.
            symbol (str): Símbolo de la empresa.
            company_name (str): Nombre de la empresa.
            
        Returns:
            str: Ruta al gráfico generado.
        """
        # Crear copia para no modificar el original
        volatility_df = df.copy()
        
        # Calcular volatilidad por nivel de sentimiento
        volatility_by_sentiment = volatility_df.groupby('sentiment_level').agg({
            'volatility': 'mean'
        }) * 100  # Convertir a porcentaje
        
        # Reordenar índice
        volatility_by_sentiment = volatility_by_sentiment.reindex(['muy_malo', 'malo', 'neutro', 'bueno', 'muy_bueno'])
        
        # Crear figura
        plt.figure(figsize=(14, 8))
        
        # Crear paleta de colores
        colors = [self.colors['muy_malo'], self.colors['malo'], self.colors['neutro'], 
                 self.colors['bueno'], self.colors['muy_bueno']]
        
        # Crear gráfico de barras
        ax = sns.barplot(
            x=volatility_by_sentiment.index,
            y=volatility_by_sentiment['volatility'],
            palette=colors
        )
        
        # Añadir etiquetas
        ax.set_xlabel('Nivel de Sentimiento', fontsize=12)
        ax.set_ylabel('Volatilidad Promedio (%)', fontsize=12)
        ax.set_title(f'Volatilidad por Nivel de Sentimiento para {company_name} ({symbol})', fontsize=14)
        
        # Cambiar etiquetas del eje x
        ax.set_xticklabels(['Muy Negativo', 'Negativo', 'Neutro', 'Positivo', 'Muy Positivo'])
        
        # Formatear eje y como porcentaje
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=1))
        
        # Añadir valores en las barras
        for i, v in enumerate(volatility_by_sentiment['volatility']):
            ax.text(i, v + 0.05, f"{v:.2f}%", ha='center')
        
        # Guardar gráfico
        plt.tight_layout()
        output_path = os.path.join(self.visualization_dir, f"{symbol}_volatility_by_sentiment.png")
        plt.savefig(output_path, dpi=300)
        plt.close()
        
        return output_path
    
    def _generate_comparative_visualization(self):
        """
        Genera una visualización comparativa de todas las empresas.
        
        Returns:
            str: Ruta al gráfico generado.
        """
        # Recopilar datos de sentimiento para todas las empresas
        all_companies_data = {}
        
        for company in self.config['companies']:
            symbol = company['symbol']
            name = company['name']
            
            sentiment_data = self._load_sentiment_data(symbol)
            if sentiment_data is not None:
                # Calcular sentimiento promedio por mes
                sentiment_data['month'] = sentiment_data.index.to_period('M')
                monthly_sentiment = sentiment_data.groupby('month').agg({
                    'combined_score': 'mean'
                })
                monthly_sentiment.index = monthly_sentiment.index.to_timestamp()
                
                all_companies_data[symbol] = {
                    'name': name,
                    'data': monthly_sentiment
                }
        
        if not all_companies_data:
            print("No hay datos disponibles para la visualización comparativa")
            return None
        
        # Crear figura
        plt.figure(figsize=(16, 10))
        
        # Graficar sentimiento promedio mensual para cada empresa
        for symbol, company_data in all_companies_data.items():
            plt.plot(
                company_data['data'].index,
                company_data['data']['combined_score'],
                linewidth=2,
                label=f"{company_data['name']} ({symbol})"
            )
        
        # Añadir línea horizontal en y=0
        plt.axhline(y=0, color='gray', linestyle='--', alpha=0.7)
        
        # Formatear eje x para mostrar fechas de manera legible
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        plt.xticks(rotation=45)
        
        # Añadir etiquetas y título
        plt.xlabel('Fecha', fontsize=12)
        plt.ylabel('Puntuación de Sentimiento Promedio', fontsize=12)
        plt.title('Comparativa de Sentimiento entre Empresas', fontsize=14)
        
        # Añadir leyenda
        plt.legend(loc='best')
        
        # Añadir grid
        plt.grid(True, alpha=0.3)
        
        # Guardar gráfico
        plt.tight_layout()
        output_path = os.path.join(self.visualization_dir, "comparative_sentiment.png")
        plt.savefig(output_path, dpi=300)
        plt.close()
        
        return output_path

if __name__ == "__main__":
    # Ruta al archivo de configuración
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'config.yaml'
    )
    
    # Crear instancia del visualizador y generar visualizaciones
    visualizer = ResultsVisualizer(config_path)
    visualization_paths = visualizer.visualize_all_companies()
