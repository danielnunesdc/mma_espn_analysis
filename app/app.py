"""
Aplicação Streamlit para análise de dados de MMA (ESPN Knockout).

Esta aplicação oferece um painel interativo em português que explora
estatísticas de lutas e métricas de desempenho de lutadores a partir
dos dados compilados do SCORE Sports Data Repository.  As fontes de
dados (derivadas do ESPN MMA e do site MMADecisions) estão
disponíveis nos arquivos ``data/mma_wtclass.csv``, ``data/mma_decisions.csv``
e ``data/ufc_stats.csv``.

Seções principais do dashboard:

1. **Distribuição de resultados**: porcentual de lutas finalizadas por
   decisão, finalização e nocaute para cada categoria de peso.
2. **Precisão de quedas**: estatísticas de precisão e quantidade média
   de quedas por luta, segmentadas por classe de peso.
3. **Golpes e precisão**: análise das métricas de golpes por minuto,
   golpes absorvidos e precisão de golpes para cada lutador.
4. **Desempenho dos lutadores**: resumo completo com atributos físicos
   (altura, peso, envergadura, idade) e métricas de performance.
5. **Análises adicionais**: comparações por sexo e distribuição do
   tempo/round de término das lutas.

Para executar a aplicação localmente:

```bash
uv pip install -r requirements.txt
streamlit run app/app.py
```

"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

# adicionar o diretório src ao path para importar data_processing
APP_DIR = Path(__file__).resolve().parent
SRC_DIR = APP_DIR.parent / "src"
sys.path.append(str(SRC_DIR))

from data_processing import (
    load_datasets,
    aggregate_result_by_wtclass,
    takedown_stats_by_class,
    strike_stats,
    fighter_performance_summary,
    map_wtclass_portuguese,
)


@st.cache_data(show_spinner=False)
def get_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carrega os dados em cache para melhorar a performance da app."""
    stats_path = Path(APP_DIR.parent) / "data" / "ufc_stats.csv"
    decisions_path = Path(APP_DIR.parent) / "data" / "mma_decisions.csv"
    wtclass_path = Path(APP_DIR.parent) / "data" / "mma_wtclass.csv"
    return load_datasets(str(stats_path), str(decisions_path), str(wtclass_path))


def main() -> None:
    st.set_page_config(page_title="Análise MMA - ESPN Knockout", layout="wide")
    st.title("📊 Análise de dados de MMA - ESPN Knockout")
    st.markdown(
        """
        Este painel interativo apresenta uma exploração abrangente dos
        **dados de lutas de MMA** coletados a partir do ESPN Knockout e do site
        [MMADecisions](https://mmadecisions.com/).  A fonte original dos
        dados está documentada pelo SCORE Sports Data Repository【451531794402788†L294-L301】,
        que compila resultados de lutas, decisões dos juízes e estatísticas
        detalhadas de desempenho dos lutadores【451531794402788†L322-L329】.

        Use os menus e filtros abaixo para investigar como as lutas
        terminam em diferentes categorias de peso, a precisão das quedas,
        métricas de golpes e outras características dos lutadores.
        """
    )

    stats_df, decisions_df, wtclass_df = get_data()

    # transformar alguns dados comuns antecipadamente
    wtclass_df['wtClass_pt'] = wtclass_df['wtClass'].apply(map_wtclass_portuguese)
    # traduzir sexo
    sex_map = {'M': 'Masculino', 'F': 'Feminino'}
    wtclass_df['p1_sex_pt'] = wtclass_df['p1_sex'].map(sex_map).fillna('Desconhecido')

    # criar abas para organização
    tabs = st.tabs([
        "Resultados por peso",
        "Precisão de quedas",
        "Golpes e precisão",
        "Desempenho dos lutadores",
        "Análises adicionais",
    ])

    # --- Aba 1: Distribuição de resultados por categoria de peso ---
    with tabs[0]:
        st.header("Distribuição de resultados por categoria de peso")
        result_agg = aggregate_result_by_wtclass(wtclass_df)
        # ordenar classes de peso por peso médio estimado (aproximadamente)
        order_map = {
            'Peso palha': 115,
            'Peso mosca': 125,
            'Peso galo': 135,
            'Peso pena': 145,
            'Peso leve': 155,
            'Peso meio-médio': 170,
            'Peso médio': 185,
            'Peso meio-pesado': 205,
            'Peso pesado': 265,
            'Peso casado': 180,
            'Peso aberto': 300,
        }
        result_agg['ordem'] = result_agg['wtClass_pt'].map(order_map)
        result_agg = result_agg.sort_values('ordem')
        # gráfico de barras empilhadas com plotly
        fig = px.bar(
            result_agg,
            x="wtClass_pt",
            y="porcentagem",
            color="decision_group_pt",
            labels={
                "wtClass_pt": "Categoria de peso",
                "porcentagem": "Percentual de lutas (%)",
                "decision_group_pt": "Tipo de resultado",
            },
            title="Proporção de resultados por categoria de peso",
        )
        fig.update_layout(barmode="stack", xaxis_title="Categoria de peso", legend_title="Resultado")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(result_agg[[
            "wtClass_pt", "decision_group_pt", "lutas", "porcentagem"
        ]].rename(columns={
            "wtClass_pt": "Categoria de peso",
            "decision_group_pt": "Tipo de resultado",
            "lutas": "Número de lutas",
            "porcentagem": "Percentual (%)",
        }))

    # --- Aba 2: Precisão de quedas ---
    with tabs[1]:
        st.header("Precisão de quedas por classe de peso")
        td_stats = takedown_stats_by_class(stats_df)
        # Selecionar apenas a métrica de precisão de quedas
        acc_df = td_stats[td_stats['metrica'] == 'Precisão de Quedas'].copy()
        fig2 = px.bar(
            acc_df,
            x="classe_peso",
            y="media",
            labels={
                "classe_peso": "Categoria de peso",
                "media": "Precisão média (%)",
            },
            title="Precisão média de quedas por categoria de peso",
        )
        fig2.update_yaxes(range=[0, 100])
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(acc_df.rename(columns={
            "classe_peso": "Categoria de peso",
            "media": "Média (%)",
            "mediana": "Mediana (%)",
            "q1": "1º quartil",
            "q3": "3º quartil",
        }))

    # --- Aba 3: Golpes e precisão ---
    with tabs[2]:
        st.header("Métricas de golpes")
        strikes_df = strike_stats(stats_df)
        # filtro por categoria de peso
        classes = sorted(strikes_df['classe_peso'].unique())
        selected_classes = st.multiselect(
            "Selecione as categorias de peso para exibir", classes, default=classes
        )
        filtered_strikes = strikes_df[strikes_df['classe_peso'].isin(selected_classes)]
        # gráfico de dispersão golpes x precisão
        fig3 = px.scatter(
            filtered_strikes,
            x="Golpes por minuto",
            y="Precisão de golpes",
            color="classe_peso",
            hover_data=["Lutador", "Golpes absorvidos por minuto"],
            labels={
                "Golpes por minuto": "Golpes por minuto",
                "Precisão de golpes": "Precisão de golpes (%)",
                "classe_peso": "Categoria de peso",
            },
            title="Precisão de golpes vs. volume de golpes",
        )
        fig3.update_layout(legend_title="Categoria de peso")
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(filtered_strikes)

    # --- Aba 4: Desempenho dos lutadores ---
    with tabs[3]:
        st.header("Resumo do desempenho dos lutadores")
        perf_df = fighter_performance_summary(stats_df)
        # filtros
        peso_options = ["Todas"] + sorted(perf_df['classe_peso'].dropna().unique())
        selected_weight = st.selectbox("Filtrar por categoria de peso", options=peso_options)
        df_display = perf_df.copy()
        if selected_weight != "Todas":
            df_display = df_display[df_display['classe_peso'] == selected_weight]
        # ordenar por precisão de golpes ou quedas
        metric_order = st.selectbox(
            "Ordenar por métrica", options=[
                "Precisão de golpes", "Precisão de quedas", "Golpes por minuto", "Quedas por luta", "Finalizações por luta"
            ]
        )
        df_display = df_display.sort_values(metric_order, ascending=False)
        st.dataframe(df_display)

    # --- Aba 5: Análises adicionais ---
    with tabs[4]:
        st.header("Análises adicionais")
        # Distribuição de resultados por sexo
        st.subheader("Distribuição de resultados por sexo")
        sex_counts = (
            wtclass_df
            .groupby(['p1_sex_pt', 'decision_group'])
            .size()
            .reset_index(name='lutas')
        )
        # traduzir decision_group novamente
        sex_counts['decision_pt'] = sex_counts['decision_group'].map({
            'Decision': 'Decisão',
            'Submission': 'Finalização',
            'KO/TKO': 'Nocaute',
            'Unkown/Other': 'Outro',
            'DQ': 'Desqualificação',
        }).fillna(sex_counts['decision_group'])
        fig4 = px.bar(
            sex_counts,
            x='p1_sex_pt',
            y='lutas',
            color='decision_pt',
            labels={
                'p1_sex_pt': 'Sexo',
                'lutas': 'Número de lutas',
                'decision_pt': 'Tipo de resultado',
            },
            title="Número de lutas e tipos de resultado por sexo do lutador 1",
        )
        fig4.update_layout(barmode="stack", legend_title="Resultado")
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(sex_counts.rename(columns={
            'p1_sex_pt': 'Sexo',
            'lutas': 'Número de lutas',
            'decision_pt': 'Tipo de resultado'
        }))

        # tempo médio de término por categoria de peso (round)
        st.subheader("Tempo médio/round de término por categoria de peso")
        # converter round em numérico; algumas lutas podem terminar em round 0 (NC)
        temp_df = wtclass_df.copy()
        temp_df['round_num'] = pd.to_numeric(temp_df['round'], errors='coerce')
        round_stats = (
            temp_df.groupby('wtClass_pt')['round_num']
            .agg(media_round='mean', mediana_round='median', total_lutas='count')
            .reset_index()
        )
        fig5 = px.bar(
            round_stats,
            x='wtClass_pt',
            y='media_round',
            labels={
                'wtClass_pt': 'Categoria de peso',
                'media_round': 'Round médio de término',
            },
            title="Round médio em que as lutas terminam por categoria de peso",
        )
        st.plotly_chart(fig5, use_container_width=True)
        st.dataframe(round_stats.rename(columns={
            'wtClass_pt': 'Categoria de peso',
            'media_round': 'Round médio',
            'mediana_round': 'Mediana do round',
            'total_lutas': 'Número de lutas'
        }))

if __name__ == "__main__":
    main()