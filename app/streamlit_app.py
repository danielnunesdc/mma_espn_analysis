"""
Aplicação Streamlit para análise de dados de MMA com base em dados do ESPN Knockout.

Esta aplicação carrega e explora três conjuntos de dados derivados do ESPN
Knockout (acessíveis no SCORE Sports Data Repository): estatísticas de
lutadores (`UFC_stats.csv`), resultados de lutas por categoria de peso
(`mma_wtclass.csv`) e decisões detalhadas (`mma_decisions.csv`). O foco
principal da análise é comparar a distribuição de métodos de vitória
(decisão, finalização, nocaute) por categoria de peso, avaliar a
precisão de golpes e quedas, bem como fornecer estatísticas gerais dos
lutadores. Todas as métricas e textos são apresentados em português
brasileiro.

Para rodar esta aplicação execute, dentro de um ambiente gerenciado pelo
`uv`, o comando:

```bash
# Sincronize as deps do projeto
uv sync
```

```bash
# Inicie a aplicação Streamlit
streamlit run app/streamlit_app.py
```
 
"""

from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

# Importa o módulo de processamento de dados. Tenta primeiro utilizar a
# estrutura de pacote `mma_espn_analysis`; se não estiver no PYTHONPATH,
# ajusta dinamicamente o caminho para permitir execução local.
import sys
from pathlib import Path

try:
    from mma_espn_analysis.src import data_processing as dp  # type: ignore
except ModuleNotFoundError:
    # Para execuções em que o pacote não foi instalado, adiciona o diretório
    # raiz do projeto ao sys.path e importa a partir de `src`.
    _current = Path(__file__).resolve()
    _root = _current.parents[1]
    sys.path.append(str(_root))
    from src import data_processing as dp  # type: ignore

# Definir o título da página
st.set_page_config(page_title="Análise de MMA - ESPN Knockout", layout="wide")

@st.cache_data
def load_data():
    """Carrega os conjuntos de dados necessários.

    Utiliza funções do módulo ``data_processing`` para carregar os arquivos
    localizados em ``mma_espn_analysis/data``.
    """
    stats_df = dp.load_ufc_stats()
    wt_df = dp.load_wtclass_results()
    return stats_df, wt_df


@st.cache_data
def get_fighter_data(stats_df: pd.DataFrame, wt_df: pd.DataFrame) -> pd.DataFrame:
    """Computa e retorna o resumo de métricas por lutador.

    Esta função invoca ``fighter_summary`` do módulo ``data_processing`` para
    calcular, para cada atleta, o número total de lutas, número de vitórias,
    vitórias por método (nocaute, finalização, decisão, desclassificação,
    outros) e vitórias no primeiro round. Além disso, incorpora métricas de
    desempenho provenientes de ``UFC_stats.csv`` como precisão de golpes,
    precisão de quedas, média de golpes por minuto, média de quedas por
    luta e média de tentativas de finalização.

    Os resultados são retornados em um único DataFrame, que é utilizado em
    diversas partes da aplicação para exibir indicadores e gráficos.

    Parameters
    ----------
    stats_df : pd.DataFrame
        DataFrame carregado de ``UFC_stats.csv`` com estatísticas de
        carreira dos lutadores.
    wt_df : pd.DataFrame
        DataFrame carregado de ``mma_wtclass.csv`` com resultados de
        lutas por categoria de peso.

    Returns
    -------
    pd.DataFrame
        DataFrame de métricas agregadas por lutador.
    """
    summary_df = dp.fighter_summary(wt_df, stats_df)
    return summary_df


def show_overview(stats_df: pd.DataFrame, wt_df: pd.DataFrame) -> None:
    """Apresenta uma visão geral dos conjuntos de dados e das métricas utilizadas."""
    st.markdown("## Visão Geral")
    st.write(
        """
        Os dados utilizados nesta análise foram coletados do ESPN Knockout e
        disponibilizados pelo projeto SCORE Sports Data Repository. O
        arquivo **UFC_stats.csv** contém informações agregadas de carreira
        para 1.673 lutadores, como altura, peso, alcance, precisão de golpes
        (Str_Acc_Pct), precisão de quedas (TD_Acc_Pct), média de golpes
        significativos desferidos por minuto (SLpM), média de quedas por
        luta (TD_Avg) e média de tentativas de finalização (Sub_Avg). O
        arquivo **mma_wtclass.csv** registra 28.771 lutas, listando o método
        de vitória consolidado em cinco categorias (Decision, Submission,
        KO/TKO, DQ, Unkown/Other) e a categoria de peso (wtClass) de cada
        confronto.
        """
    )
    # Mostrar algumas informações básicas
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Número de lutadores", f"{len(stats_df):,}")
        st.metric("Número de lutas", f"{len(wt_df):,}")
    with col2:
        st.metric("Período das lutas", f"{int(wt_df['year'].min())} – {int(wt_df['year'].max())}")
        st.metric("Categorias de peso", f"{wt_df['wtClass'].nunique()}")


def plot_win_percentages(wt_df: pd.DataFrame) -> None:
    """Desenha gráficos de distribuição de métodos de vitória."""
    st.markdown("## Distribuição de métodos de vitória")
    counts = dp.win_percentages_by_method(wt_df)
    # Traduzir nomes para português (Decision -> Decisão, etc.)
    translation = {
        'Decision': 'Decisão',
        'Submission': 'Finalização',
        'KO/TKO': 'Nocaute/KO',
        'DQ': 'Desclassificação',
        'Unkown/Other': 'Desconhecido/Outro'
    }
    counts['metodo_pt'] = counts['metodo'].map(translation)
    # Gráfico de pizza
    fig_pie = px.pie(
        counts,
        names='metodo_pt',
        values='quantidade',
        title='Proporção global de métodos de vitória',
        hole=0.4,
    )
    fig_pie.update_traces(textposition='inside', texttemplate='%{percent:.1%}', hovertemplate='%{label}: %{percent:.1%}<extra></extra>')
    st.plotly_chart(fig_pie, use_container_width=True)
    # Tabela
    st.dataframe(counts[['metodo_pt', 'quantidade', 'percentual']].rename(columns={
        'metodo_pt': 'Método', 'quantidade': 'Quantidade', 'percentual': 'Percentual (%)'
    }).style.format({'Percentual (%)': '{:.2f}'}), use_container_width=True)


def plot_win_percentages_by_weight(wt_df: pd.DataFrame) -> None:
    """Gráfico interativo da distribuição de métodos de vitória por categoria de peso."""
    st.markdown("## Métodos de vitória por categoria de peso")
    grouped = dp.win_percentages_by_weight_and_method(wt_df)
    translation = {
        'Decision': 'Decisão',
        'Submission': 'Finalização',
        'KO/TKO': 'Nocaute/KO',
        'DQ': 'Desclassificação',
        'Unkown/Other': 'Desconhecido/Outro'
    }
    grouped['metodo_pt'] = grouped['metodo'].map(translation)
    # Ordenar categorias de peso de forma mais intuitiva (por peso médio)
    # Definir lista aproximada de ordem baseada em pesos médios (apenas para visualização)
    ordem = [
        'Strawweight', 'Flyweight', 'Bantamweight', 'Featherweight',
        'Lightweight', 'Welterweight', 'Middleweight', 'Light Heavyweight',
        'Heavyweight', 'Catchweight'
    ]
    grouped['wtClass'] = pd.Categorical(grouped['wtClass'], categories=ordem, ordered=True)
    # Stacked bar chart
    fig = px.bar(
        grouped,
        x='wtClass',
        y='percentual',
        color='metodo_pt',
        title='Distribuição de métodos de vitória por categoria de peso',
        labels={'percentual': 'Percentual (%)', 'wtClass': 'Categoria de peso', 'metodo_pt': 'Método'},
        barmode='stack'
    )
    fig.update_layout(legend_title_text='Método de vitória')
    st.plotly_chart(fig, use_container_width=True)


def plot_accuracy_and_strikes(stats_df: pd.DataFrame) -> None:
    """Exibe histogramas de precisão de quedas, de golpes e média de golpes por minuto."""
    st.markdown("## Precisão de quedas e golpes")
    col1, col2, col3 = st.columns(3)
    with col1:
        fig_td_acc = px.histogram(
            stats_df,
            x='TD_Acc_Pct',
            nbins=30,
            title='Distribuição da precisão de quedas (%)',
            labels={'TD_Acc_Pct': 'Precisão de quedas (%)'},
        )
        st.plotly_chart(fig_td_acc, use_container_width=True)
    with col2:
        fig_str_acc = px.histogram(
            stats_df,
            x='Str_Acc_Pct',
            nbins=30,
            title='Distribuição da precisão de golpes (%)',
            labels={'Str_Acc_Pct': 'Precisão de golpes (%)'},
        )
        st.plotly_chart(fig_str_acc, use_container_width=True)
    with col3:
        fig_slpm = px.histogram(
            stats_df,
            x='SLpM',
            nbins=30,
            title='Golpes significativos desferidos por minuto',
            labels={'SLpM': 'Golpes por minuto'},
        )
        st.plotly_chart(fig_slpm, use_container_width=True)
    # Mostrar estatísticas resumidas
    summary = dp.summary_fighter_stats(stats_df)
    st.markdown("### Estatísticas resumidas")
    for k, v in summary.items():
        st.write(f"**{k.replace('_', ' ').capitalize()}:** {v:.2f}")


def plot_top_fighters(stats_df: pd.DataFrame) -> None:
    """Permite selecionar uma métrica e exibe os lutadores no topo dessa métrica."""
    st.markdown("## Ranking de lutadores por métrica")
    metric_map = {
        'Precisão de golpes (%)': 'Str_Acc_Pct',
        'Precisão de quedas (%)': 'TD_Acc_Pct',
        'Média de quedas por luta': 'TD_Avg',
        'Média de golpes por minuto': 'SLpM',
        'Média de tentativas de finalização': 'Sub_Avg'
    }
    metric_display = st.selectbox(
        'Selecione a métrica para ranquear os lutadores:',
        list(metric_map.keys()),
        index=0
    )
    metric_col = metric_map[metric_display]
    top_df = dp.top_fighters_by_metric(stats_df, metric_col, top_n=10)
    top_df = top_df.rename(columns={metric_col: metric_display, 'fighter_name': 'Lutador'})
    st.dataframe(top_df.reset_index(drop=True), use_container_width=True)


def plot_fighter_metrics(stats_df: pd.DataFrame, wt_df: pd.DataFrame) -> None:
    """Permite explorar as métricas individuais de cada lutador.

    Exibe um seletor de lutadores e, ao escolher um nome, apresenta
    indicadores numéricos e um gráfico polar comparando as principais
    estatísticas desse atleta.
    """
    st.markdown("## Estatísticas por lutador")
    fighters = sorted(stats_df['fighter_name'].dropna().unique())
    selected = st.selectbox('Selecione um lutador:', fighters, index=0)
    # Carregar dados agregados
    summary_df = get_fighter_data(stats_df, wt_df)
    # Procurar linha do lutador na tabela resumo
    summ_row = summary_df[summary_df['fighter_name'] == selected].iloc[0]
    # Mostrar métricas numéricas gerais (vitórias e precisões)
    # Organizar as métricas a exibir. Incluímos mais indicadores de desempenho
    # (precisão de golpes, média de golpes por minuto, quedas por luta e
    # finalizações por luta) para oferecer uma visão mais completa do lutador.
    from collections import OrderedDict
    metrics_map = OrderedDict([
        ('Vitórias por nocaute', summ_row['wins_ko']),
        ('Vitórias por finalização', summ_row['wins_sub']),
        ('Vitórias no 1º round', summ_row['wins_round1']),
        ('Vitórias por decisão', summ_row['wins_dec']),
        ('Precisão de quedas (%)', summ_row['TD_Acc_Pct']),
        ('Precisão de golpes (%)', summ_row['Str_Acc_Pct']),
        ('Golpes por minuto', summ_row['SLpM']),
        ('Quedas por luta', summ_row['TD_Avg']),
        ('Finalizações por luta', summ_row['Sub_Avg']),
    ])
    # Criar colunas dinamicamente para acomodar todos os indicadores. Usamos
    # três colunas por linha para melhor legibilidade.
    n_cols = 3
    metrics_cols = st.columns(n_cols)
    for idx, (label, value) in enumerate(metrics_map.items()):
        # Selecionar a coluna com base no índice
        col = metrics_cols[idx % n_cols]
        # Se o valor for NaN (ausente), exibir 'N/D'
        if pd.isna(value):
            display_value = 'N/D'
        else:
            display_value = f"{value:.0f}" if 'Vitórias' in label else f"{value:.2f}"
        col.metric(label, display_value)
    # Gráfico de vitórias por método
    method_counts = pd.DataFrame({
        'Método': ['KO/TKO', 'Finalização', 'Decisão', 'Desclassificação', 'Outro'],
        'Vitórias': [summ_row['wins_ko'], summ_row['wins_sub'], summ_row['wins_dec'], summ_row['wins_dq'], summ_row['wins_other']],
    })
    method_counts['Percentual'] = method_counts['Vitórias'] / summ_row['total_wins'] * 100 if summ_row['total_wins'] > 0 else 0
    fig_method = px.bar(
        method_counts,
        x='Método',
        y='Vitórias',
        title=f'Vitórias por método – {selected}',
        labels={'Vitórias': 'Número de vitórias'},
        text=method_counts['Percentual'].apply(lambda x: f"{x:.1f}%"),
        color='Método'
    )
    fig_method.update_traces(textposition='outside')
    st.plotly_chart(fig_method, use_container_width=True)
    # Gráfico de vitórias por categoria
    # Calcular vitórias por categoria diretamente a partir do conjunto de lutas
    # Selecionar as lutas em que o lutador venceu
    # Nas colunas ``p1_result`` e ``p2_result`` os resultados são armazenados como
    # 'W' (vitória), 'L' (derrota) ou 'D' (empate/no contest). Além disso, os
    # nomes dos lutadores em ``mma_wtclass.csv`` seguem frequentemente o
    # formato ``'Sobrenome, Nome'``, enquanto em ``UFC_stats.csv`` (e na
    # interface) utilizamos ``'Nome Sobrenome'``. Para filtrar corretamente
    # as vitórias do lutador selecionado, definimos uma função de
    # normalização dos nomes que inverte a ordem quando há vírgula.
    def _normalize_name_local(name: str | float | None) -> str | None:
        if name is None or (isinstance(name, float) and pd.isna(name)):
            return None
        name_str = str(name).strip()
        if ',' in name_str:
            parts = name_str.split(',', 1)
            last = parts[0].strip()
            first = parts[1].strip()
            return f"{first} {last}"
        return name_str
    # Aplicar normalização para comparar nomes
    p1_norm = wt_df['p1_name'].apply(_normalize_name_local)
    p2_norm = wt_df['p2_name'].apply(_normalize_name_local)
    mask1 = (p1_norm == selected) & (wt_df['p1_result'].str.upper() == 'W')
    mask2 = (p2_norm == selected) & (wt_df['p2_result'].str.upper() == 'W')
    fighter_wins = wt_df[mask1 | mask2].copy()
    if not fighter_wins.empty:
        cat_counts = fighter_wins.groupby(['wtClass', 'decision_group']).size().reset_index(name='wins')
        # Traduzir métodos para português
        trans = {
            'KO/TKO': 'Nocaute',
            'Submission': 'Finalização',
            'Decision': 'Decisão',
            'DQ': 'Desclassificação',
            'Unkown/Other': 'Outro'
        }
        cat_counts['Metodo_pt'] = cat_counts['decision_group'].map(trans)
        fig_cat = px.bar(
            cat_counts,
            x='wtClass',
            y='wins',
            color='Metodo_pt',
            title=f'Vitórias por categoria de peso e método – {selected}',
            labels={'wtClass': 'Categoria', 'wins': 'Vitórias', 'Metodo_pt': 'Método'},
            barmode='stack'
        )
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info('O lutador selecionado não possui vitórias registradas no conjunto de dados.')


def plot_additional_insights(wt_df: pd.DataFrame) -> None:
    """Exibe análises adicionais: lutas por ano e por número de rounds."""
    st.markdown("## Outras Análises")
    col1, col2 = st.columns(2)
    # Lutas por ano
    fights_year_df = dp.fights_per_year(wt_df)
    fig_year = px.line(
        fights_year_df,
        x='ano',
        y='quantidade',
        title='Número de lutas por ano',
        labels={'ano': 'Ano', 'quantidade': 'Quantidade de lutas'},
    )
    with col1:
        st.plotly_chart(fig_year, use_container_width=True)
    # Lutas por número de rounds
    rounds_df = dp.fights_by_round(wt_df)
    fig_rounds = px.bar(
        rounds_df,
        x='rounds',
        y='quantidade',
        title='Distribuição de lutas por número de rounds',
        labels={'rounds': 'Rounds', 'quantidade': 'Quantidade'},
    )
    with col2:
        st.plotly_chart(fig_rounds, use_container_width=True)


def main():
    """Função principal que organiza o layout da aplicação."""
    stats_df, wt_df = load_data()
    st.title("Análise de MMA com dados do ESPN Knockout")
    st.markdown(
        "Esta análise explora estatísticas de lutas e lutadores de MMA a partir de dados publicados no **ESPN Knockout**."
    )
    # Navegação por abas
    tabs = st.tabs([
        "Visão Geral", "Métodos de vitória", "Precisão e Golpes",
        "Estatísticas por lutador", "Ranking de lutadores", "Outras Análises"
    ])
    with tabs[0]:
        show_overview(stats_df, wt_df)
    with tabs[1]:
        plot_win_percentages(wt_df)
        plot_win_percentages_by_weight(wt_df)
    with tabs[2]:
        plot_accuracy_and_strikes(stats_df)
    with tabs[3]:
        plot_fighter_metrics(stats_df, wt_df)
    with tabs[4]:
        plot_top_fighters(stats_df)
    with tabs[5]:
        plot_additional_insights(wt_df)


if __name__ == "__main__":
    main()