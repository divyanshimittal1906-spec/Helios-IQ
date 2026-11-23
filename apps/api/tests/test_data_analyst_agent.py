from __future__ import annotations

import asyncio
import csv
import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ai.agents.base import AgentContext
from app.ai.agents.data_analyst_agent import DataAnalystAgent
from app.ai.agents.service import AgentExecutionService
from app.ai.provider import AIProvider
from app.main import app
from tests.helpers import auth_header


class MockAIProvider(AIProvider):
    def __init__(self) -> None:
        self.last_prompt: str = ''

    def generate(self, prompt: str, **kwargs: object) -> str:
        self.last_prompt = prompt
        return 'The dataset indicates a moderate distribution with no unsupported claims.'


def csv_bytes(rows: list[list[str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8')


def xlsx_bytes(rows: list[list[str]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as workbook:
        shared_strings: list[str] = []
        def add_shared(value: str) -> int:
            if value not in shared_strings:
                shared_strings.append(value)
            return shared_strings.index(value)

        rows_xml = []
        for row in rows:
            cells = []
            for value in row:
                idx = add_shared(str(value))
                cells.append(
                    f'<c r="{chr(65 + len(cells))}1" t="s"><v>{idx}</v></c>'
                )
            rows_xml.append(f'<row r="1">{''.join(cells)}</row>')

        shared_xml = '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="%d" uniqueCount="%d">%s</sst>' % (
            len(shared_strings),
            len(shared_strings),
            ''.join(f'<si><t>{value}</t></si>' for value in shared_strings),
        )
        workbook.writestr('xl/sharedStrings.xml', shared_xml)
        workbook.writestr(
            'xl/worksheets/sheet1.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>%s</sheetData></worksheet>' % ''.join(rows_xml),
        )
        workbook.writestr('xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
        workbook.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>')
        workbook.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        workbook.writestr('xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>')
    return output.getvalue()


def test_valid_csv_analysis() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'sales.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([
                ['region', 'sales', 'month'],
                ['north', '100', '2024-01'],
                ['south', '200', '2024-02'],
                ['north', '150', '2024-03'],
            ]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=1))
    )
    assert result['dataset']['row_count'] == 3
    assert result['dataset']['column_count'] == 3
    assert result['status'] == 'completed'


def test_valid_xlsx_analysis() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'metrics.xlsx',
            'content_type': 'xlsx',
            'workspace_id': 1,
            'file_content': xlsx_bytes([
                ['team', 'score', 'date'],
                ['A', '10', '2024-01-01'],
                ['B', '20', '2024-01-02'],
            ]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=2))
    )
    assert result['dataset']['filename'] == 'metrics.xlsx'
    assert result['columns'][1]['classification'] == 'numeric'


def test_column_type_detection() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'types.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([
                ['name', 'age', 'joined_on'],
                ['alice', '30', '2024-05-01'],
                ['bob', '45', '2024-05-02'],
                ['charlie', '41', '2024-05-03'],
            ]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=3))
    )
    assert any(column['name'] == 'age' and column['classification'] == 'numeric' for column in result['columns'])
    assert any(column['name'] == 'joined_on' and column['classification'] == 'date' for column in result['columns'])


def test_missing_value_analysis() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'missing.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([
                ['name', 'score'],
                ['alice', '10'],
                ['bob', ''],
                ['', '30'],
                ['dave', '40'],
            ]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=4))
    )
    assert result['data_quality']['missing_values'] >= 2
    assert any(column['name'] == 'score' and column['missing_count'] >= 1 for column in result['columns'])


def test_numeric_statistics() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'stats.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([
                ['value'],
                ['10'],
                ['20'],
                ['30'],
            ]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=5))
    )
    stats = result['statistics']['numeric_columns']['value']
    assert stats['count'] == 3
    assert stats['mean'] == 20.0
    assert stats['minimum'] == 10.0
    assert stats['maximum'] == 30.0


def test_categorical_frequency_analysis() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'categorical.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([
                ['segment'],
                ['A'],
                ['A'],
                ['B'],
                ['C'],
            ]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=6))
    )
    segment = next(column for column in result['columns'] if column['name'] == 'segment')
    assert segment['classification'] == 'categorical'
    assert any(item['value'] == 'A' for item in segment['frequencies'])


def test_duplicate_detection() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'dupes.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([
                ['id', 'value'],
                ['1', 'x'],
                ['1', 'x'],
                ['2', 'y'],
            ]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=7))
    )
    assert result['data_quality']['duplicate_rows'] >= 1


def test_data_quality_analysis() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'quality.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([
                ['id', 'value'],
                ['1', 'x'],
                ['2', ''],
                ['3', 'y'],
            ]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=8))
    )
    assert result['data_quality']['missing_values'] >= 1
    assert 'notes' in result['data_quality']


def test_deterministic_insight_generation() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'insights.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([
                ['score'],
                ['10'],
                ['20'],
                ['30'],
                ['40'],
            ]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=9))
    )
    assert len(result['insights']) >= 1
    assert 'score' in ' '.join(result['insights'])


def test_unsupported_file_type_rejection() -> None:
    with pytest.raises(ValueError):
        DataAnalystAgent()._parse_dataset(b'abc', 'txt', 'data.txt')


def test_malformed_csv_handling() -> None:
    agent = DataAnalystAgent()
    with pytest.raises(ValueError):
        asyncio.run(
            agent.execute({
                'filename': 'bad.csv',
                'content_type': 'csv',
                'workspace_id': 1,
                'file_content': b'\x00\x01\x02',
            }, context=AgentContext(user_id=1, workspace_id=1, execution_id=10))
        )


def test_malformed_xlsx_handling() -> None:
    with pytest.raises(ValueError):
        DataAnalystAgent()._parse_dataset(b'not-a-valid-xlsx', 'xlsx', 'broken.xlsx')


def test_empty_dataset_handling() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'empty.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': b'',
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=11))
    )
    assert result['dataset']['row_count'] == 0
    assert 'contains no rows' in ' '.join(result['insights']).lower()


def test_workspace_isolation() -> None:
    agent = DataAnalystAgent()
    with pytest.raises(PermissionError):
        asyncio.run(
            agent.execute({
                'filename': 'safe.csv',
                'content_type': 'csv',
                'workspace_id': 99,
                'file_content': csv_bytes([['value'], ['10']]),
            }, context=AgentContext(user_id=1, workspace_id=1, execution_id=12))
        )


def test_execution_tracking() -> None:
    agent = DataAnalystAgent()
    context = AgentContext(user_id=1, workspace_id=1, execution_id=13)
    result = asyncio.run(
        agent.execute({
            'filename': 'tracked.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([['value'], ['10'], ['20']]),
        }, context=context)
    )
    assert result['execution_id'] == 13
    assert result['status'] == 'completed'


def test_provider_failure_handling() -> None:
    class FailingProvider(AIProvider):
        def generate(self, prompt: str, **kwargs: object) -> str:
            raise RuntimeError('provider down')

    agent = DataAnalystAgent(ai_provider=FailingProvider())
    result = asyncio.run(
        agent.execute({
            'filename': 'provider.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([['value'], ['10'], ['20']]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=14))
    )
    assert result['status'] == 'completed'


def test_no_fabricated_statistics() -> None:
    agent = DataAnalystAgent()
    result = asyncio.run(
        agent.execute({
            'filename': 'no_fabrication.csv',
            'content_type': 'csv',
            'workspace_id': 1,
            'file_content': csv_bytes([
                ['value'],
                ['5'],
                ['10'],
                ['15'],
            ]),
        }, context=AgentContext(user_id=1, workspace_id=1, execution_id=15))
    )
    stats = result['statistics']['numeric_columns']['value']
    assert stats['mean'] == 10.0
    assert stats['minimum'] == 5.0
    assert stats['maximum'] == 15.0
    assert 'Column \'value\' spans from 5.0 to 15.0, indicating a measurable range.' in result['insights']
    assert '5.0' in ' '.join(result['insights'])
    assert '15.0' in ' '.join(result['insights'])


def test_api_route_analyze() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/data/analyze?workspace_id=1',
        files={'file': ('sample.csv', b'name,value\nalice,10\nbob,20\n', 'text/csv')},
        headers=auth_header(1, 'user@example.com'),
    )
    assert response.status_code == 200
    data = response.json()
    assert data['dataset']['row_count'] == 2
    assert data['status'] == 'completed'
    assert data['statistics']['numeric_columns']['value']['mean'] == 15.0
