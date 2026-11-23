from __future__ import annotations

import csv
import io
import statistics
import zipfile
from collections import Counter
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET

from pydantic import ValidationError

from app.ai.agents.base import Agent, AgentContext
from app.ai.agents.registry import AgentRegistry
from app.ai.provider import AIProvider, get_ai_provider
from app.schemas.data_analyst import DataAnalysisRequest, DataAnalysisResponse


class DataAnalystAgent(Agent):
    id = 'data-analyst-agent'
    name = 'data-analyst-agent'
    description = 'Validates uploaded datasets, inspects schema, computes quality metrics, and reports deterministic insights.'
    version = '1.0.0'
    input_schema = DataAnalysisRequest
    output_schema = DataAnalysisResponse
    tools = ()
    required_permissions = ('workspace:read',)
    workspace_access_required = True

    def __init__(self, ai_provider: AIProvider | None = None) -> None:
        self.ai_provider = ai_provider or get_ai_provider()

    def validate_input(self, payload: dict[str, Any]) -> DataAnalysisRequest:
        try:
            validated = super().validate_input(payload)
            if isinstance(validated, dict):
                return DataAnalysisRequest.model_validate(validated)
            return validated
        except ValidationError as exc:
            raise ValueError(f'Invalid input for {self.name}: {exc}') from exc

    def authorize_workspace(self, user_id: int | None, workspace_id: int, current_workspace_id: int | None) -> None:
        if workspace_id <= 0:
            raise ValueError('workspace_id must be greater than zero.')
        if current_workspace_id is not None and workspace_id != current_workspace_id:
            raise PermissionError('The requested workspace does not match the current execution context.')
        if user_id is None:
            raise PermissionError('A valid user is required to analyze a dataset in a workspace.')

    @staticmethod
    def _normalize_value(value: Any) -> str:
        if value is None:
            return ''
        text = str(value).strip()
        if text in {'', 'nan', 'NaN', 'N/A', 'NA', 'null', 'None'}:
            return ''
        return text

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        text = DataAnalystAgent._normalize_value(value)
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    @staticmethod
    def _detect_type(values: list[Any]) -> str:
        non_missing = [value for value in values if DataAnalystAgent._normalize_value(value)]
        if not non_missing:
            return 'unknown'

        parsed_numeric = 0
        parsed_date = 0
        for value in non_missing:
            if DataAnalystAgent._safe_float(value) is not None:
                parsed_numeric += 1
                continue
            try:
                datetime.fromisoformat(str(value).strip())
                parsed_date += 1
            except ValueError:
                pass

        if parsed_numeric == len(non_missing):
            return 'numeric'
        if parsed_date == len(non_missing):
            return 'date'
        if len(set(non_missing)) <= max(10, min(25, len(non_missing) // 2)):
            return 'categorical'
        return 'text'

    @staticmethod
    def _classify_column(values: list[Any]) -> str:
        inferred = DataAnalystAgent._detect_type(values)
        if inferred == 'numeric':
            return 'numeric'
        if inferred == 'date':
            return 'date'
        if inferred == 'categorical':
            return 'categorical'
        return 'text'

    @staticmethod
    def _numeric_summary(values: list[Any]) -> dict[str, Any] | None:
        numeric_values = [float(v) for v in values if DataAnalystAgent._safe_float(v) is not None]
        if not numeric_values:
            return None
        mean_value = sum(numeric_values) / len(numeric_values)
        median_value = statistics.median(numeric_values)
        minimum_value = min(numeric_values)
        maximum_value = max(numeric_values)
        stddev_value = statistics.pstdev(numeric_values) if len(numeric_values) > 1 else 0.0
        return {
            'count': len(numeric_values),
            'mean': round(mean_value, 6),
            'median': round(median_value, 6),
            'minimum': round(minimum_value, 6),
            'maximum': round(maximum_value, 6),
            'standard_deviation': round(stddev_value, 6),
        }

    @staticmethod
    def _categorical_summary(values: list[Any]) -> dict[str, Any]:
        cleaned = [DataAnalystAgent._normalize_value(value) for value in values if DataAnalystAgent._normalize_value(value)]
        counts = Counter(cleaned)
        top_items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        return {
            'unique_values': len(counts),
            'top_values': [{'value': value, 'count': count} for value, count in top_items],
        }

    @staticmethod
    def _parse_csv(content: bytes) -> list[dict[str, str]]:
        if not content:
            return []
        if b'\x00' in content:
            raise ValueError('CSV file is malformed or unreadable.')

        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('CSV file is malformed or unreadable.') from exc

        if not text.strip():
            return []

        rows = list(csv.reader(io.StringIO(text, newline='')))
        filtered_rows = [row for row in rows if any(cell.strip() for cell in row)]
        if not filtered_rows:
            return []

        header = [str(value).strip() or f'column_{index + 1}' for index, value in enumerate(filtered_rows[0])]
        if not header:
            return []

        for row in filtered_rows[1:]:
            if len(row) != len(header):
                raise ValueError('CSV file is malformed: inconsistent column counts.')

        normalized_rows: list[dict[str, str]] = []
        for row in filtered_rows[1:]:
            normalized_row: dict[str, str] = {}
            for index, field in enumerate(header):
                normalized_row[field] = DataAnalystAgent._normalize_value(row[index] if index < len(row) else '')
            normalized_rows.append(normalized_row)
        return normalized_rows

    @staticmethod
    def _parse_xlsx(content: bytes) -> list[dict[str, str]]:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as workbook:
                shared_strings: list[str] = []
                if 'xl/sharedStrings.xml' in workbook.namelist():
                    tree = ET.fromstring(workbook.read('xl/sharedStrings.xml'))
                    for node in tree.findall('.//{*}si'):
                        text_parts = [part.text or '' for part in node.findall('.//{*}t')]
                        shared_strings.append(''.join(text_parts))

                sheet_names = [name for name in workbook.namelist() if name.startswith('xl/worksheets/sheet') and name.endswith('.xml')]
                if not sheet_names:
                    raise ValueError('XLSX workbook does not contain any worksheet data.')

                sheet_root = ET.fromstring(workbook.read(sheet_names[0]))
                rows: list[list[str]] = []
                for row in sheet_root.findall('.//{*}sheetData/{*}row'):
                    values: list[str] = []
                    for cell in row.findall('{*}c'):
                        cell_type = cell.get('t')
                        if cell_type == 's':
                            index_text = cell.findtext('{*}v', default='')
                            try:
                                index = int(index_text)
                            except ValueError:
                                index = -1
                            value = shared_strings[index] if 0 <= index < len(shared_strings) else ''
                        elif cell_type == 'inlineStr':
                            value = ''.join(part.text or '' for part in cell.findall('.//{*}t'))
                        else:
                            value = cell.findtext('{*}v', default='')
                        values.append(DataAnalystAgent._normalize_value(value))
                    rows.append(values)

                if not rows:
                    return []

                header_names = [str(value).strip() or f'column_{index + 1}' for index, value in enumerate(rows[0])]
                parsed_rows: list[dict[str, str]] = []
                for row_values in rows[1:]:
                    item: dict[str, str] = {}
                    for index, header_name in enumerate(header_names):
                        item[header_name] = row_values[index] if index < len(row_values) else ''
                    parsed_rows.append(item)
                return parsed_rows
        except (zipfile.BadZipFile, ET.ParseError) as exc:
            raise ValueError('XLSX file is malformed or unreadable.') from exc

    @staticmethod
    def _parse_dataset(content: bytes, content_type: str, filename: str) -> list[dict[str, str]]:
        normalized_type = (content_type or filename.rsplit('.', 1)[-1]).lower().strip()
        if normalized_type in {'csv', 'text/csv'} or filename.lower().endswith('.csv'):
            return DataAnalystAgent._parse_csv(content)
        if normalized_type in {'xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'} or filename.lower().endswith('.xlsx'):
            return DataAnalystAgent._parse_xlsx(content)
        raise ValueError('Unsupported dataset format. Only CSV and XLSX files are supported.')

    @staticmethod
    def _build_chart_ready(columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chart_ready: list[dict[str, Any]] = []
        for column in columns:
            if column.get('classification') == 'categorical' and column.get('top_values'):
                chart_ready.append({
                    'column': column['name'],
                    'chart_type': 'bar',
                    'labels': [entry['value'] for entry in column['top_values'][:10]],
                    'values': [entry['count'] for entry in column['top_values'][:10]],
                })
        return chart_ready

    async def execute(self, payload: dict[str, Any], context: AgentContext | None = None) -> dict[str, Any]:
        validated = self.validate_input(payload)
        if context is not None:
            self.authorize_workspace(context.user_id, validated.workspace_id, context.workspace_id)

        filename = validated.filename
        content = validated.file_content
        if content is None:
            raise ValueError('No dataset content was provided for analysis.')

        rows = self._parse_dataset(content, validated.content_type, filename)
        if not rows:
            return DataAnalysisResponse(
                dataset={
                    'filename': filename,
                    'row_count': 0,
                    'column_count': 0,
                    'column_names': [],
                    'content_type': validated.content_type,
                },
                columns=[],
                statistics={'numeric_columns': {}},
                data_quality={
                    'missing_values': 0,
                    'duplicate_rows': 0,
                    'empty_columns': [],
                    'invalid_values': 0,
                    'notes': ['The dataset is empty and contains no rows.'],
                },
                insights=['The dataset contains no rows, so no reliable data trends can be determined.'],
                chart_ready=[],
                execution_id=context.execution_id if context is not None else None,
                status='completed',
            ).model_dump(mode='json', exclude_none=True)

        headers = list(rows[0].keys())
        column_values: dict[str, list[Any]] = {header: [row.get(header, '') for row in rows] for header in headers}

        column_entries: list[dict[str, Any]] = []
        statistics_summary: dict[str, Any] = {'numeric_columns': {}}
        total_missing = 0
        duplicate_rows = 0
        seen_rows: set[tuple[Any, ...]] = set()
        empty_columns: list[str] = []
        invalid_values = 0

        for header in headers:
            values = column_values.get(header, [])
            missing_count = sum(1 for value in values if not self._normalize_value(value))
            total_missing += missing_count
            classification = self._classify_column(values)
            summary = {
                'name': header,
                'inferred_type': self._detect_type(values),
                'classification': classification,
                'missing_count': missing_count,
                'missing_percentage': round((missing_count / len(values)) * 100, 2) if values else 0.0,
                'unique_value_count': len({self._normalize_value(value) for value in values if self._normalize_value(value)}),
            }
            if classification == 'numeric':
                numeric_stats = self._numeric_summary(values)
                if numeric_stats is not None:
                    summary['statistics'] = numeric_stats
                    statistics_summary['numeric_columns'][header] = numeric_stats
            elif classification in {'categorical', 'text'}:
                categorical_summary = self._categorical_summary(values)
                summary['frequencies'] = categorical_summary['top_values']
                summary['top_values'] = categorical_summary['top_values']
            if missing_count == len(values):
                empty_columns.append(header)
            column_entries.append(summary)

        for row in rows:
            tuple_value = tuple(str(value) for value in row.values())
            if tuple_value in seen_rows:
                duplicate_rows += 1
            else:
                seen_rows.add(tuple_value)

        for header in headers:
            values = column_values.get(header, [])
            if self._classify_column(values) == 'numeric':
                invalid_values += sum(
                    1
                    for value in values
                    if self._normalize_value(value) and self._safe_float(value) is None
                )

        dataset_info = {
            'filename': filename,
            'row_count': len(rows),
            'column_count': len(headers),
            'column_names': headers,
            'content_type': validated.content_type,
        }

        insights: list[str] = []
        for column in column_entries:
            if column['missing_percentage'] > 25:
                insights.append(f"Column '{column['name']}' has {column['missing_percentage']}% missing values, which may affect downstream analysis.")
            if column['classification'] == 'numeric' and 'statistics' in column:
                stats = column['statistics']
                if stats['maximum'] - stats['minimum'] > 0:
                    insights.append(f"Column '{column['name']}' spans from {stats['minimum']} to {stats['maximum']}, indicating a measurable range.")
            if column['classification'] in {'categorical', 'text'} and column.get('top_values'):
                top_value = column['top_values'][0]
                insights.append(f"The most frequent value in '{column['name']}' is '{top_value['value']}' ({top_value['count']} occurrences).")

        if duplicate_rows > 0:
            insights.append(f'The dataset contains {duplicate_rows} duplicate row(s).')
        if not insights:
            insights.append('No significant quality issues or strong patterns were detected in the dataset based on the actual values available.')

        response = DataAnalysisResponse(
            dataset=dataset_info,
            columns=column_entries,
            statistics=statistics_summary,
            data_quality={
                'missing_values': total_missing,
                'duplicate_rows': duplicate_rows,
                'empty_columns': empty_columns,
                'invalid_values': invalid_values,
                'notes': [
                    'Values were treated as blank when they were missing, empty, or null-like.',
                    'Numeric columns are evaluated only when all non-empty values can be parsed as numbers.',
                ],
            },
            insights=insights,
            chart_ready=self._build_chart_ready(column_entries),
            execution_id=context.execution_id if context is not None else None,
            status='completed',
        )
        return response.model_dump(mode='json', exclude_none=True)


_data_analyst_registry = AgentRegistry()
_data_analyst_agent = DataAnalystAgent()

try:
    _data_analyst_registry.register(_data_analyst_agent)
except ValueError:
    pass


def get_data_analyst_registry() -> AgentRegistry:
    return _data_analyst_registry
