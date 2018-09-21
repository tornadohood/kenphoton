"""Unit tests for the ReportAPI."""

import textwrap

import numpy
import pandas
import pytest
import ujson

from photon.lib import config_utils
from photon.lib import time_utils
from photon.report import report_api

DATASET = pandas.DataFrame({
    'Timestamp': [
        time_utils.Timestamp('Jan 1 2018 10:00:01'),
        time_utils.Timestamp('Jan 1 2018 10:00:01'),
        time_utils.Timestamp('Jan 1 2018 10:00:01'),
        time_utils.Timestamp('Jan 1 2018 11:00:05'),
        time_utils.Timestamp('Jan 1 2018 11:00:05'),
    ],
    'array_name': [None, 'my_cool_array', 'my_cool_array', 'my_cool_array', 'my_cool_array'],
    'capacity': [None, 80, 80, 81, 82],
    'sel_critical_events': [
        'dd | 06/02/2018 | 20:16:33 | Memory #0x08 | Correctable ECC logging limit reached | Asserted   |',
        None, None, None, None],
    'controller': ['CT0', 'CT1', 'CT0', 'CT1', 'CT0'],
    'physical_space': [None, 10, 11, 22, 23],
    'purity_version': [None, '5.0.1', '5.0.1', '5.0.1', '5.0.1'],
    'reclaimable_space': [None, 0, 1, 7, 4],
    'reported_pyramid': [None, 1, 1, 3, 3],
    'ssd_capacity': [None, 100, 100, 101, 102],
    'ssd_mapped': [None, 10, 10, numpy.nan, 11],
    'volume_name': [None, {'my_volume': 'my_volume'},{'my_volume': 'my_volume'}, {'my_volume': 'my_volume'},
                    {'my_volume': 'my_volume'}],
    'volume_read_latency': [None, {'my_volume': 3}, {'my_volume': 3}, {'my_volume': 4}, {'my_volume': 4}],
    'unreported_space': [None, 4, 7, 5, 6],
})
METRIC_INDEX = config_utils.get_metric_index()
TABLE_TYPES = ('Table', 'CSVTable', 'JSONTable', 'HTMLTable')
TEST_CASES = {
    'controller_specific': {
        'expected_fields': ['array_name', 'purity_version'],
        'expected_lines': {
            'Table': """
            {noformat}
            ================================================================
            |  Timestamp            |  CT0 Array Name  CT1 Purity Version  |
            +-----------------------+--------------------------------------+
            |  2018-01-01 10:00:00  |  my_cool_array   5.0.1               |
            |  2018-01-01 11:00:00  |  my_cool_array   5.0.1               |
            ================================================================
            {noformat}

        """,
            'CSVTable': """
            Timestamp,CT0 Array Name,CT1 Purity Version
            2018-01-01 10:00:00,my_cool_array,5.0.1
            2018-01-01 11:00:00,my_cool_array,5.0.1

        """,
            'JSONTable': """
            {"schema": {"fields":[{"name":"index","type":"integer"},{"name":"Timestamp","type":"datetime"},{"name":"CT0 Array Name","type":"string"},{"name":"CT1 Purity Version","type":"string"}],"primaryKey":["index"],"pandas_version":"0.20.0"}, "data": [{"index":0,"Timestamp":"2018-01-01T10:00:00.000Z","CT0 Array Name":"my_cool_array","CT1 Purity Version":"5.0.1"},{"index":2,"Timestamp":"2018-01-01T11:00:00.000Z","CT0 Array Name":"my_cool_array","CT1 Purity Version":"5.0.1"}]}
            """,
            'HTMLTable': """
            <table border="1" class="dataframe">
              <thead>
                <tr style="text-align: right;">
                  <th></th>
                  <th>Timestamp</th>
                  <th>CT0 Array Name</th>
                  <th>CT1 Purity Version</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th>0</th>
                  <td>2018-01-01 10:00:00</td>
                  <td>my_cool_array</td>
                  <td>5.0.1</td>
                </tr>
                <tr>
                  <th>2</th>
                  <td>2018-01-01 11:00:00</td>
                  <td>my_cool_array</td>
                  <td>5.0.1</td>
                </tr>
              </tbody>
            </table>
        """
        },
        'expected_metrics': ['CT0 Array Name', 'CT1 Purity Version'],
        'expected_tables': 1,
        'metrics': {
            'array_name': {'controller': 'CT0'},
            'purity_version': {'controller': 'CT1'},
        },
        'render_config': {'frequency': '1h'},
        'table_config': {},
    },
    'dependent_metrics': {
        'expected_fields': ['reclaimable_space', 'reported_pyramid', 'ssd_capacity', 'unreported_space'],
        'expected_lines': {
            'Table': """
            {noformat}
            ===================================================
            |  Timestamp            |  Unaccounted Space PCT  |
            +-----------------------+-------------------------+
            |  2018-01-01 10:00:00  |                  5.00%  |
            |  2018-01-01 11:00:00  |                  0.00%  |
            ===================================================
            {noformat}

            """,
            'CSVTable': """
            Timestamp,Unaccounted Space PCT
            2018-01-01 10:00:00,5.0
            2018-01-01 11:00:00,0.0

            """,
            'JSONTable': """
            {"schema": {"fields":[{"name":"index","type":"integer"},{"name":"Timestamp","type":"datetime"},{"name":"Unaccounted Space PCT","type":"string"}],"primaryKey":["index"],"pandas_version":"0.20.0"}, "data": [{"index":0,"Timestamp":"2018-01-01T10:00:00.000Z","Unaccounted Space PCT":"5.00%"},{"index":1,"Timestamp":"2018-01-01T11:00:00.000Z","Unaccounted Space PCT":"0.00%"}]}
            """,
            'HTMLTable': """
            <table border="1" class="dataframe">
              <thead>
                <tr style="text-align: right;">
                  <th></th>
                  <th>Timestamp</th>
                  <th>Unaccounted Space PCT</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th>0</th>
                  <td>2018-01-01 10:00:00</td>
                  <td>5.00%</td>
                </tr>
                <tr>
                  <th>1</th>
                  <td>2018-01-01 11:00:00</td>
                  <td>0.00%</td>
                </tr>
              </tbody>
            </table>
            """
        },
        'expected_metrics': ['Unaccounted Space PCT'],
        'expected_tables': 1,
        'metrics': {
            'unaccounted_space_pct': {},
        },
        'render_config': {'frequency': '1h'},
        'table_config': {},
    },
    'simple_metrics': {
        'expected_fields': ['array_name', 'purity_version'],
        'expected_lines': {
            'Table': """
        {noformat}
        ===========================================================
        |  Timestamp            |  Array Name     Purity Version  |
        +-----------------------+---------------------------------+
        |  2018-01-01 10:00:00  |  my_cool_array  5.0.1           |
        |  2018-01-01 11:00:00  |  my_cool_array  5.0.1           |
        ===========================================================
        {noformat}

        """,
            'CSVTable': """
        Timestamp,Array Name,Purity Version
        2018-01-01 10:00:00,my_cool_array,5.0.1
        2018-01-01 11:00:00,my_cool_array,5.0.1

        """,
            'JSONTable': """
        {"schema": {"fields":[{"name":"index","type":"integer"},{"name":"Timestamp","type":"datetime"},{"name":"Array Name","type":"string"},{"name":"Purity Version","type":"string"}],"primaryKey":["index"],"pandas_version":"0.20.0"}, "data": [{"index":0,"Timestamp":"2018-01-01T10:00:00.000Z","Array Name":"my_cool_array","Purity Version":"5.0.1"},{"index":1,"Timestamp":"2018-01-01T11:00:00.000Z","Array Name":"my_cool_array","Purity Version":"5.0.1"}]}
        """,
            'HTMLTable': """
        <table border="1" class="dataframe">
          <thead>
            <tr style="text-align: right;">
              <th></th>
              <th>Timestamp</th>
              <th>Array Name</th>
              <th>Purity Version</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th>0</th>
              <td>2018-01-01 10:00:00</td>
              <td>my_cool_array</td>
              <td>5.0.1</td>
            </tr>
            <tr>
              <th>1</th>
              <td>2018-01-01 11:00:00</td>
              <td>my_cool_array</td>
              <td>5.0.1</td>
            </tr>
          </tbody>
        </table>
        """
        },
        'expected_metrics': ['Array Name', 'Purity Version'],
        'expected_tables': 1,
        'metrics': {
            'array_name': {'controller': None},
            'purity_version': {'controller': None},
        },
        'render_config': {'frequency': '1h'},
        'table_config': {},
    },
}
TEMPLATES = config_utils.get_table_index()


class SimpleAPI(object):
    """Helper to simplify testing, i.e. simplify the FlashArray API behavior."""

    def __init__(self, dataset):
        self.dataset = dataset
        self.timeframe = time_utils.Timeframe('Jan 1 2018 10:00', 'Jan 1 2018 11:00')

    def get_fields(self, fields):
        """Helper to get the requested fields from the dataset."""
        return self.dataset[['Timestamp', 'controller'] + fields]


@pytest.fixture()
def make_simple_api():
    """Build a SimpleAPI instance with the default dataset."""
    api = SimpleAPI(DATASET)
    return api


@pytest.fixture()
def make_report():
    """Build a Report instance using the SimpleAPI."""
    api = make_simple_api()
    return report_api.Report(api)


@pytest.fixture()
def make_table(table_type, table_kwargs):
    """Build a Table instance."""
    table = getattr(report_api, table_type)(**table_kwargs)
    return table


# Unit tests for Report:
@pytest.mark.parametrize('table_type', ('table', 'csv', 'json', 'html'))
@pytest.mark.parametrize('test_case', list(TEST_CASES.values()), ids=list(TEST_CASES.keys()))
def test_add_table(test_case, table_type):
    """Unit tests for Report.add_table."""
    report = make_report()
    table = report.add_table(table_type, **test_case['table_config'])
    for metric_name, metric_config in sorted(test_case['metrics'].items()):
        table.add_metric(metric_name, **metric_config)

    # Ensure that we have the correct number of tables.
    num_tables = len(report.tables)
    assert num_tables == test_case['expected_tables']

    # Ensure that we have the correct fields.
    report._get_table_fields()
    fields = sorted(report.fields)
    assert fields == test_case['expected_fields']

    # Ensure that we have the correct metrics.
    metric_names = set()
    for table in report.tables:
        for metric_name in sorted(table.metrics.keys()):
            metric_names.add(metric_name)
    assert sorted(list(metric_names)) == test_case['expected_metrics']


@pytest.mark.parametrize('template_name', list(TEMPLATES.keys()), ids=list(TEMPLATES.keys()))
def test_add_template(template_name):
    """Unit tests for Report.add_template."""
    report = make_report()
    report.add_template(template_name)
    assert len(report.tables) == 1


# Unit tests for Table objects:
@pytest.mark.parametrize('table_type', TABLE_TYPES)
@pytest.mark.parametrize('metric', list(METRIC_INDEX.keys()), ids=list(METRIC_INDEX.keys()))
def test_add_metric(metric, table_type):
    """Unit test for Table.add_metric."""
    table = make_table(table_type, {})
    table.add_metric(metric)
    assert len(table.metrics) == 1


@pytest.mark.parametrize('table_type', TABLE_TYPES)
def test_add_pipe(table_type):
    """Unit test for Table.add_pipe."""
    table = make_table(table_type, {})
    table.add_pipe()
    # This should not add any metrics.
    assert len(table.metrics) == 0
    # With timestamp as True (default), we should just add another pipe to columns.
    assert table.columns == ['|', 'Timestamp', '|', '|']


@pytest.mark.parametrize('table_type', TABLE_TYPES)
@pytest.mark.parametrize('test_case', list(TEST_CASES.values()), ids=list(TEST_CASES.keys()))
def test_render_table(test_case, table_type):
    """Unit test for Table.render_table."""
    table = make_table(table_type, test_case['table_config'])
    for metric, metric_config in sorted(test_case['metrics'].items()):
        table.add_metric(metric, **metric_config)
    table_lines = table.render_table(DATASET, **test_case['render_config'])
    result = '\n' + table_lines + '\n'
    expected = textwrap.dedent(test_case['expected_lines'][table_type])
    if table_type == 'JSONTable':
        result = ujson.loads(result)
        expected = ujson.loads(expected)
    assert result == expected
