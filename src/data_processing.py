"""
Módulo de processamento de dados para análise de MMA.

Este módulo contém funções utilitárias para carregar os conjuntos de dados
disponibilizados pelo SCORE Sports Data Repository (derivados do ESPN
Knockout) e realizar pré‑processamento e cálculo de métricas. As funções
fornecem resumos estatísticos que são posteriormente utilizados pela
aplicação Streamlit para gerar gráficos interativos e dashboards.

Conteúdo dos conjuntos de dados:

* ``UFC_stats.csv`` – estatísticas de carreira de 1.673 lutadores de MMA.
  Contém colunas como ``SLpM`` (golpes significativos desferidos por
  minuto), ``Str_Acc`` (precisão de golpes, em percentagem), ``SApM``
  (golpes significativos recebidos por minuto), ``Str_Def`` (defesa de
  golpes), ``TD_Avg`` (média de quedas por luta), ``TD_Acc`` (precisão
  de quedas), ``TD_Def`` (defesa de quedas) e ``Sub_Avg`` (média de
  tentativas de finalização por luta).

* ``mma_wtclass.csv`` – resultados de lutas por categoria de peso. Cada
  linha representa uma luta (28.771 no total) com informações como data,
  evento, se valia cinturão, tempo de duração, resultado e nome dos
  lutadores. A coluna ``decision_group`` agrega o método de vitória em
  categorias: ``Decision`` (lutas decididas pelos juízes), ``Submission``
  (finalização), ``KO/TKO`` (nocaute ou nocaute técnico), ``DQ``
  (desclassificação) e ``Unkown/Other``.

* ``mma_decisions.csv`` – detalhamento de lutas que terminaram em decisão.
  Inclui as notas dos juízes, márgens de pontuação e indicadores de
  concordância, mas não é utilizado diretamente nesta análise, pois
  ``mma_wtclass.csv`` já resume os métodos de vitória.

As funções deste módulo retornam DataFrames prontos para uso nos
gráficos, sempre em português e com porcentagens calculadas.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path

# Função utilitária para normalizar nomes dos lutadores
def _normalize_name(name: str | float | int | None) -> str | None:
    """Converte um nome de lutador no formato ``'Sobrenome, Nome'`` para
    ``'Nome Sobrenome'``.

    Os datasets de lutas (`mma_wtclass.csv`) frequentemente armazenam os nomes
    como ``'Sobrenome, Nome'`` (por exemplo, ``'Erosa, Julian'``), enquanto o
    dataset de estatísticas (`UFC_stats.csv`) utiliza ``'Nome Sobrenome'``
    (``'Julian Erosa'``). Para reconciliar os dois conjuntos, este helper
    detecta a presença de uma vírgula e inverte a ordem.

    Parameters
    ----------
    name : str or numeric or None
        Nome original do lutador. Pode ser ``None`` ou valores não
        string que serão retornados sem alterações.

    Returns
    -------
    str or None
        Nome normalizado no formato ``'Nome Sobrenome'`` ou ``None`` se
        ``name`` for ``None``/NaN.
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return None
    # Convert to string and strip whitespace
    name_str = str(name).strip()
    # If there's a comma, assume format 'Last, First'
    if ',' in name_str:
        # Split at first comma
        parts = name_str.split(',', 1)
        last = parts[0].strip()
        first = parts[1].strip()
        return f"{first} {last}"
    return name_str

# Diretório que contém os arquivos de dados.
# Partimos de ``data_processing.py`` em ``mma_espn_analysis/src``. O
# diretório pai imediato (parents[1]) é ``mma_espn_analysis``. Dentro dele
# existe a pasta ``data`` com os CSVs. Portanto utilizamos parents[1].
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def load_ufc_stats(path: Path | str | None = None) -> pd.DataFrame:
    """Carrega o conjunto de dados ``UFC_stats.csv``.

    Parameters
    ----------
    path : Path or str, optional
        Caminho alternativo para o arquivo CSV. Se None, utiliza
        ``DATA_DIR / 'UFC_stats.csv'``.

    Returns
    -------
    pd.DataFrame
        DataFrame com estatísticas de lutadores.
    """
    if path is None:
        path = DATA_DIR / "UFC_stats.csv"
    df = pd.read_csv(path)
    # Convertir algumas colunas para tipos numéricos e normalizar nomes
    df.rename(columns={
        "Str_Acc": "Str_Acc_Pct",
        "TD_Acc": "TD_Acc_Pct",
        "Str_Def": "Str_Def_Pct",
        "TD_Def": "TD_Def_Pct",
    }, inplace=True)
    # Converter porcentagens de strings para floats caso necessário
    for col in ["Str_Acc_Pct", "TD_Acc_Pct", "Str_Def_Pct", "TD_Def_Pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_wtclass_results(path: Path | str | None = None) -> pd.DataFrame:
    """Carrega o conjunto de dados ``mma_wtclass.csv``.

    Parameters
    ----------
    path : Path or str, optional
        Caminho alternativo para o arquivo CSV. Se None, utiliza
        ``DATA_DIR / 'mma_wtclass.csv'``.

    Returns
    -------
    pd.DataFrame
        DataFrame com resultados de lutas por categoria de peso.
    """
    if path is None:
        path = DATA_DIR / "mma_wtclass.csv"
    df = pd.read_csv(path)
    return df


def win_percentages_by_method(df_wt: pd.DataFrame) -> pd.DataFrame:
    """Calcula a distribuição de métodos de vitória em todas as lutas.

    Parameters
    ----------
    df_wt : pd.DataFrame
        DataFrame carregado a partir de ``mma_wtclass.csv``.

    Returns
    -------
    pd.DataFrame
        Tabela com as colunas ``metodo`` (Submission, Decision, KO/TKO, DQ,
        Unkown/Other), ``quantidade`` e ``percentual``.
    """
    counts = df_wt['decision_group'].value_counts().reset_index()
    counts.columns = ['metodo', 'quantidade']
    counts['percentual'] = counts['quantidade'] / counts['quantidade'].sum() * 100
    counts = counts.sort_values('percentual', ascending=False).reset_index(drop=True)
    return counts


def win_percentages_by_weight_and_method(df_wt: pd.DataFrame) -> pd.DataFrame:
    """Calcula o percentual de cada método de vitória por categoria de peso.

    Parameters
    ----------
    df_wt : pd.DataFrame
        DataFrame de lutas por categoria de peso.

    Returns
    -------
    pd.DataFrame
        DataFrame com colunas ``wtClass``, ``metodo``, ``quantidade``,
        ``percentual``. Cada linha representa uma combinação de categoria de
        peso e método de vitória.
    """
    # Contagem por categoria e método
    grouped = df_wt.groupby(['wtClass', 'decision_group']).size().reset_index(name='quantidade')
    # Calcular total por categoria
    totals = grouped.groupby('wtClass')['quantidade'].transform('sum')
    grouped['percentual'] = grouped['quantidade'] / totals * 100
    # Renomear coluna para português
    grouped.rename(columns={'decision_group': 'metodo'}, inplace=True)
    return grouped


def summary_fighter_stats(df_stats: pd.DataFrame) -> dict[str, float]:
    """Gera estatísticas resumo globais dos lutadores.

    Calcula métricas como média e mediana de precisão de golpes, média de
    quedas por luta, etc.

    Parameters
    ----------
    df_stats : pd.DataFrame
        DataFrame de lutadores carregado de ``UFC_stats.csv``.

    Returns
    -------
    dict
        Dicionário com métricas agregadas.
    """
    stats = {}
    # Precisão média de golpes
    stats['media_precisao_golpes'] = df_stats['Str_Acc_Pct'].mean()
    stats['mediana_precisao_golpes'] = df_stats['Str_Acc_Pct'].median()
    # Precisão média de quedas
    stats['media_precisao_quedas'] = df_stats['TD_Acc_Pct'].mean()
    stats['mediana_precisao_quedas'] = df_stats['TD_Acc_Pct'].median()
    # Média de quedas por luta
    stats['media_quedas_por_luta'] = df_stats['TD_Avg'].mean()
    stats['mediana_quedas_por_luta'] = df_stats['TD_Avg'].median()
    # Média de golpes desferidos por minuto
    stats['media_golpes_por_minuto'] = df_stats['SLpM'].mean()
    stats['mediana_golpes_por_minuto'] = df_stats['SLpM'].median()
    # Média de tentativas de finalização por luta
    stats['media_finalizacao_por_luta'] = df_stats['Sub_Avg'].mean()
    stats['mediana_finalizacao_por_luta'] = df_stats['Sub_Avg'].median()
    return stats


def top_fighters_by_metric(df_stats: pd.DataFrame, metric: str, top_n: int = 10) -> pd.DataFrame:
    """Seleciona os principais lutadores de acordo com uma métrica.

    Parameters
    ----------
    df_stats : pd.DataFrame
        DataFrame com estatísticas de lutadores.
    metric : str
        Nome da coluna métrica (ex. ``Str_Acc_Pct``, ``TD_Acc_Pct``).
    top_n : int
        Número de lutadores no topo a serem retornados.

    Returns
    -------
    pd.DataFrame
        DataFrame com colunas ``fighter_name`` e a métrica escolhida.
    """
    if metric not in df_stats.columns:
        raise ValueError(f"Métrica '{metric}' não encontrada no DataFrame.")
    subset = df_stats[['fighter_name', metric]].dropna().copy()
    subset = subset.sort_values(metric, ascending=False).head(top_n)
    return subset


def fights_per_year(df_wt: pd.DataFrame) -> pd.DataFrame:
    """Conta o número de lutas por ano.

    Parameters
    ----------
    df_wt : pd.DataFrame
        DataFrame de lutas por categoria de peso.

    Returns
    -------
    pd.DataFrame
        DataFrame com colunas ``ano`` e ``quantidade``, ordenado pelo ano.
    """
    counts = df_wt.groupby('year').size().reset_index(name='quantidade').sort_values('year')
    counts.rename(columns={'year': 'ano'}, inplace=True)
    return counts


def fights_by_round(df_wt: pd.DataFrame) -> pd.DataFrame:
    """Analisa a duração das lutas pela contagem de rounds.

    Parameters
    ----------
    df_wt : pd.DataFrame
        DataFrame de lutas por categoria de peso.

    Returns
    -------
    pd.DataFrame
        DataFrame com colunas ``rounds`` e ``quantidade``.
    """
    counts = df_wt['round'].value_counts().reset_index()
    counts.columns = ['rounds', 'quantidade']
    counts = counts.sort_values('rounds')
    return counts


def fighter_summary(df_wt: pd.DataFrame, df_stats: pd.DataFrame) -> pd.DataFrame:
    """Computa métricas agregadas por lutador a partir dos dados de lutas e estatísticas.

    A função calcula, para cada lutador, o número de lutas, número de vitórias,
    vitórias por método (KO/TKO, Submission, Decision, DQ, Other), vitórias no
    primeiro round e porcentagem de vitórias. Em seguida, incorpora
    informações de precisão de quedas, precisão de golpes e outros indicadores
    do conjunto ``UFC_stats.csv``.

    Parameters
    ----------
    df_wt : pd.DataFrame
        DataFrame de lutas por categoria de peso.
    df_stats : pd.DataFrame
        DataFrame de estatísticas de lutadores.

    Returns
    -------
    pd.DataFrame
        DataFrame agregando métricas por lutador.
    """
    # Inicializar dicionários para contagem
    from collections import defaultdict
    total_fights = defaultdict(int)
    total_wins = defaultdict(int)
    wins_ko = defaultdict(int)
    wins_sub = defaultdict(int)
    wins_dec = defaultdict(int)
    wins_dq = defaultdict(int)
    wins_other = defaultdict(int)
    wins_round1 = defaultdict(int)

    # Iterar sobre cada luta
    for _, row in df_wt.iterrows():
        # Atualizar total de lutas para ambos os lutadores
        # Normalizar nomes no formato "Nome Sobrenome"
        fighter1_raw = row['p1_name']
        fighter2_raw = row['p2_name']
        fighter1 = _normalize_name(fighter1_raw)
        fighter2 = _normalize_name(fighter2_raw)
        if fighter1 is not None:
            total_fights[fighter1] += 1
        if fighter2 is not None:
            total_fights[fighter2] += 1
        # Determinar o vencedor e atualizar contagens
        method = row['decision_group']
        # As colunas ``p1_result`` e ``p2_result`` armazenam códigos abreviados
        # indicando o resultado do combate para cada atleta: ``W`` para vitória,
        # ``L`` para derrota e ``D`` para empate/no contest. Normalizamos para
        # maiúsculas e verificamos se houve vitória.
        p1_res = str(row['p1_result']).strip().upper() if pd.notna(row['p1_result']) else ''
        p2_res = str(row['p2_result']).strip().upper() if pd.notna(row['p2_result']) else ''
        # Caso o lutador 1 vença
        if p1_res == 'W' and fighter1 is not None:
            total_wins[fighter1] += 1
            if row['round'] == 1:
                wins_round1[fighter1] += 1
            if method == 'KO/TKO':
                wins_ko[fighter1] += 1
            elif method == 'Submission':
                wins_sub[fighter1] += 1
            elif method == 'Decision':
                wins_dec[fighter1] += 1
            elif method == 'DQ':
                wins_dq[fighter1] += 1
            else:
                wins_other[fighter1] += 1
        # Caso o lutador 2 vença
        elif p2_res == 'W' and fighter2 is not None:
            total_wins[fighter2] += 1
            if row['round'] == 1:
                wins_round1[fighter2] += 1
            if method == 'KO/TKO':
                wins_ko[fighter2] += 1
            elif method == 'Submission':
                wins_sub[fighter2] += 1
            elif method == 'Decision':
                wins_dec[fighter2] += 1
            elif method == 'DQ':
                wins_dq[fighter2] += 1
            else:
                wins_other[fighter2] += 1

    # Construir DataFrame
    fighters = set(list(total_fights.keys()) + list(df_stats['fighter_name']))
    rows = []
    for fighter in fighters:
        tf = total_fights.get(fighter, 0)
        tw = total_wins.get(fighter, 0)
        row = {
            'fighter_name': fighter,
            'total_fights': tf,
            'total_wins': tw,
            'win_percent': tw / tf * 100 if tf > 0 else 0,
            'wins_ko': wins_ko.get(fighter, 0),
            'wins_sub': wins_sub.get(fighter, 0),
            'wins_dec': wins_dec.get(fighter, 0),
            'wins_dq': wins_dq.get(fighter, 0),
            'wins_other': wins_other.get(fighter, 0),
            'wins_round1': wins_round1.get(fighter, 0),
        }
        rows.append(row)
    summary_df = pd.DataFrame(rows)
    # Calcular percentuais de cada método
    for col in ['wins_ko', 'wins_sub', 'wins_dec', 'wins_dq', 'wins_other', 'wins_round1']:
        pct_col = col + '_pct'
        summary_df[pct_col] = summary_df[col] / summary_df['total_wins'].replace(0, np.nan) * 100
    # Incorporar dados de estatísticas individuais
    stats_subset = df_stats[['fighter_name', 'TD_Acc_Pct', 'Str_Acc_Pct', 'SLpM', 'TD_Avg', 'Sub_Avg']]
    merged = summary_df.merge(stats_subset, how='left', on='fighter_name')
    return merged


def fighter_wins_by_category_and_method(df_wt: pd.DataFrame) -> pd.DataFrame:
    """Agrupa vitórias por lutador, categoria de peso e método de vitória.

    Esta função varre o DataFrame de lutas ``df_wt`` e constrói um novo
    DataFrame contendo apenas as vitórias. Cada registro guarda o nome do
    lutador vencedor, a categoria de peso e o método de vitória. Em seguida,
    os registros são agrupados para contar quantas vitórias cada atleta
    possui em cada categoria e método.

    A implementação é resiliente a dados ausentes. Caso não haja nenhuma
    vitória registrada (por exemplo, se ``df_wt`` estiver vazio), a função
    retornará um DataFrame vazio com as colunas esperadas.

    Parameters
    ----------
    df_wt : pd.DataFrame
        DataFrame de lutas por categoria de peso.

    Returns
    -------
    pd.DataFrame
        DataFrame com colunas ``fighter_name``, ``wtClass``, ``metodo`` e
        ``wins`` representando o número de vitórias.
    """
    records: list[dict[str, object]] = []
    # Construir lista de vitórias
    for _, row in df_wt.iterrows():
        method = row.get('decision_group')
        weight_class = row.get('wtClass')
        # Determinar o vencedor a partir dos códigos de resultado
        winner: str | None = None
        p1_res = str(row.get('p1_result')).strip().upper() if pd.notna(row.get('p1_result')) else ''
        p2_res = str(row.get('p2_result')).strip().upper() if pd.notna(row.get('p2_result')) else ''
        if p1_res == 'W':
            winner = row.get('p1_name')
        elif p2_res == 'W':
            winner = row.get('p2_name')
        if winner:
            # Normalizar o nome para combinar com ``UFC_stats.csv``
            normalized = _normalize_name(winner)
            if normalized:
                records.append({
                    'fighter_name': normalized,
                    'wtClass': weight_class,
                    'metodo': method,
                })
    # Se não houver registros, retornar DataFrame vazio com colunas definidas
    if not records:
        return pd.DataFrame(columns=['fighter_name', 'wtClass', 'metodo', 'wins'])
    df = pd.DataFrame(records)
    # Agrupar e contar vitórias por lutador, categoria e método
    grouped = df.value_counts(['fighter_name', 'wtClass', 'metodo']).reset_index(name='wins')
    return grouped
