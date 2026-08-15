import io
from typing import Union
import polars as pl
import duckdb
from app.schemas.document import (
    TabularAnalyticsSummary,
    TabularColumnStats,
    MetadataValue,
)


class TabularDataService:
    """Motor de análise e sumarização de dados tabulares utilizando Polars e DuckDB."""

    def analyze_csv_bytes(
        self,
        file_bytes: bytes,
        sample_rows_limit: int = 5,
    ) -> tuple[TabularAnalyticsSummary, str]:
        """Carrega e analisa um CSV em memória com Polars e gera um resumo textual para RAG."""
        df = pl.read_csv(io.BytesIO(file_bytes), ignore_errors=True)

        row_count = df.height
        col_count = df.width
        columns = df.columns

        stats_list: list[TabularColumnStats] = []
        for col_name in columns:
            series = df[col_name]
            dtype_str = str(series.dtype)
            null_ct = int(series.null_count())
            uniq_ct = int(series.n_unique())

            mean_val: Union[float, None] = None
            min_val: Union[str, float, int, None] = None
            max_val: Union[str, float, int, None] = None

            if series.dtype.is_numeric():
                non_null = series.drop_nulls()
                if len(non_null) > 0:
                    mean_val = float(non_null.mean()) if non_null.mean() is not None else None
                    raw_min = non_null.min()
                    raw_max = non_null.max()
                    min_val = float(raw_min) if raw_min is not None else None
                    max_val = float(raw_max) if raw_max is not None else None
            else:
                non_null = series.drop_nulls()
                if len(non_null) > 0:
                    min_val = str(non_null.min())
                    max_val = str(non_null.max())

            stats_list.append(
                TabularColumnStats(
                    column_name=col_name,
                    data_type=dtype_str,
                    null_count=null_ct,
                    unique_count=uniq_ct,
                    mean=mean_val,
                    min_value=min_val,
                    max_value=max_val,
                )
            )

        sample_dicts: list[dict[str, MetadataValue]] = []
        sample_df = df.head(sample_rows_limit)
        for row in sample_df.to_dicts():
            row_clean: dict[str, MetadataValue] = {}
            for k, v in row.items():
                if v is None or isinstance(v, (str, int, float, bool)):
                    row_clean[k] = v
                else:
                    row_clean[k] = str(v)
            sample_dicts.append(row_clean)

        summary = TabularAnalyticsSummary(
            row_count=row_count,
            column_count=col_count,
            columns=columns,
            column_stats=stats_list,
            sample_records=sample_dicts,
        )

        # Gera representação textual rica para indexação vetorial
        text_representation = self._generate_markdown_summary(summary, df)
        return summary, text_representation

    def execute_sql_query(
        self,
        query: str,
        df: pl.DataFrame,
        table_name: str = "dataset",
    ) -> list[dict[str, MetadataValue]]:
        """Executa consultas analíticas SQL em memória sobre o DataFrame com DuckDB."""
        conn = duckdb.connect(database=":memory:")
        # Registra o DataFrame do Polars diretamente como tabela virtual
        arrow_table = df.to_arrow()
        conn.register(table_name, arrow_table)

        result_df = conn.execute(query).pl()
        conn.close()

        records: list[dict[str, MetadataValue]] = []
        for row in result_df.to_dicts():
            row_clean: dict[str, MetadataValue] = {}
            for k, v in row.items():
                if v is None or isinstance(v, (str, int, float, bool)):
                    row_clean[k] = v
                else:
                    row_clean[k] = str(v)
            records.append(row_clean)
        return records

    def _generate_markdown_summary(
        self, summary: TabularAnalyticsSummary, df: pl.DataFrame
    ) -> str:
        """Gera uma descrição narrativa e estruturada do dataset para embeddings."""
        lines = [
            f"# Resumo Estruturado de Dados Tabulares",
            f"- Total de Linhas: {summary.row_count}",
            f"- Total de Colunas: {summary.column_count}",
            f"- Colunas Existentes: {', '.join(summary.columns)}",
            "",
            "## Estatísticas por Coluna:",
        ]

        for stat in summary.column_stats:
            stat_line = f"- **{stat.column_name}** ({stat.data_type}): {stat.unique_count} valores únicos, {stat.null_count} nulos."
            if stat.mean is not None:
                stat_line += f" Média: {stat.mean:.2f}, Mín: {stat.min_value}, Máx: {stat.max_value}."
            lines.append(stat_line)

        lines.append("")
        lines.append("## Amostra Inicial dos Dados:")
        # Gera cabeçalho markdown
        header = "| " + " | ".join(summary.columns) + " |"
        separator = "| " + " | ".join(["---"] * len(summary.columns)) + " |"
        lines.append(header)
        lines.append(separator)

        for rec in summary.sample_records:
            row_values = [str(rec.get(col, "")) for col in summary.columns]
            lines.append("| " + " | ".join(row_values) + " |")

        return "\n".join(lines)


tabular_service = TabularDataService()
