"""Simple Report API for generating and printing reports within the terminal."""

import abc
import logging

import pandas

from photon.lib import config_utils
from photon.lib import format_utils
from photon.lib import pandas_utils
from photon.lib import parallel_utils
from photon.lib import time_utils
from photon.report import metric_base

# pylint: disable=unused-import
try:
    from typing import Any
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Set
    from typing import Tuple
    from typing import Union
except ImportError:
    pass

FIELD_INDEX = config_utils.get_field_index()
LOGGER = logging.getLogger(__name__)
META_KEYS = ['Timestamp', 'controller']
METRIC_INDEX = config_utils.get_metric_index()
PIPE = '|'  # PIPE is used as a custom separator to break up table columns.
SETTINGS = config_utils.get_settings()
TABLE_INDEX = config_utils.get_table_index()
TEXT_ALIGNMENTS = {
    'left': format_utils.LEFT_JUSTIFY,
    'right': format_utils.RIGHT_JUSTIFY,
    'center': format_utils.CENTER_JUSTIFY
}


class Report(object):
    """The Report API which generates Tables based upon data points from the FlashArray and other APIs."""

    def __init__(self, flasharray_api):
        # type: (Any) -> None
        """Initialize a Report.

        Arguments:
            flasharray_api: An API from which to request information.
                Note: The API should provides a get_fields method and returns a pandas.DataFrame.
        """
        self.array_api = flasharray_api
        self.dataset = None  # type: Optional[pandas.DataFrame]
        self.freq = self.array_api.timeframe.granularity
        self.fields = set()
        self.metrics = set()
        self.tables = []
        self.table_types = {'csv': CSVTable, 'json': JSONTable, 'html': HTMLTable, 'table': Table}

    def _build_tables_in_parallel(self, jira):
        # type: (bool) -> str
        """Build tables in parallel.

        This will break up the amount of work and assign 10 tasks for each sub-process.
        """
        tasks = []
        task_args = []
        for table in self.tables:
            if isinstance(table, str):
                # CAVEAT: This is a text area... no real processing required, just pass it through.
                yield table
                continue
            tasks.append(table.render_table)
            fields = [field for field in table.required_fields if field in FIELD_INDEX]
            table_frame = self.dataset[['Timestamp', 'controller'] + fields]
            task_args.append([table_frame, self.freq, jira])
        # Building tables doesn't require that much work, break them up into pools of 10.
        workers = int(len(self.tables) / 10)
        with parallel_utils.ProcessPool(processes=workers) as pool:
            pool.parallelize(tasks, task_args)
            for result in pool.get_results(ordered=True):
                yield result

    def _build_tables_in_series(self, jira):
        # type: (bool) -> str
        """Generate tables in series."""
        for table in self.tables:
            if isinstance(table, str):
                # CAVEAT: This is a text area... no real processing required, just pass it through.
                yield table
                continue
            fields = [field for field in table.required_fields if field in FIELD_INDEX]
            table_frame = self.dataset[META_KEYS + fields]
            result = table.render_table(table_frame, self.freq, jira)
            yield result

    def _get_table_fields(self):
        # type: () -> None
        """Get all of the fields needed to render all tables."""
        for table in self.tables:
            if isinstance(table, str):
                # This is a TextArea, skip it.
                continue
            for metric in table.metrics.values():
                for field in _get_required_fields(metric):
                    self.fields.add(field)

    def add_table(self, table_type=None, title=None, timestamp=True, **table_config):
        # type: (str, Optional[str], bool, **dict) -> Table
        """Add a Table to the Report.

        Arguments:
            table_type (str): The type of table to render.
                Choices ('csv', 'json', 'html', 'table')
            title (str): A title to include in the table.
            timestamp (bool): Whether or not to include a timestamp column.

        Keyword Arguments:
            box (bool): Whether to make the box-like structure of the table or not.
            grid (bool): Put a 'grid' around the table columns.  This provides visual breaks between each.
            headers (bool): Whether to include headers in the table or not.
            use_titles (bool): Whether to display titles or not.

        Returns:
            table (Table): A table instance of the requested type.
        """
        # If None is passed in it will override any default that we set for table_type, so just default to None
        # and convert to 'table' if it's None.
        table_type = table_type.lower() if table_type else 'table'
        if table_type not in self.table_types:
            raise ValueError('The requested table_type "{}" does not exist.'.format(table_type))
        table = self.table_types[table_type](title, timestamp, **table_config)
        self.tables.append(table)
        return table

    def add_template(self, template_name, **table_kwargs):
        # type: (str, **Dict[str, Any]) -> None
        """Build a Table based upon the INI template in table_index.ini and keyword argument overrides.

        Arguments:
            template_name (str): The name of the template to use.
            table_kwargs (dict): One or more keyword arguments to apply to the Table instance.

        Returns:
            table (Table): An instance of either Table/CSVTable/JSONTable/HTMLTable, etc.
        """
        if template_name not in TABLE_INDEX:
            msg = 'Requested template "{}" does not exist.'.format(template_name)
            LOGGER.error(msg)
            raise ValueError(msg)

        # Get the default configuration and update it with any manual overrides.
        table_config = TABLE_INDEX[template_name]
        table_config.update(table_kwargs)

        # If there is no title, then use the template_name in a nicer format.
        if table_config.get('title') == '':
            table_config['title'] = format_utils.make_title(template_name)

        # The metrics section is just used here to determine which things to add to the table, don't pass it in.
        metrics = list(table_config['columns'])
        table_type = table_config.get('table_type')
        table_type = self.table_types[table_type.lower() if table_type else 'table']  # type: Table
        del table_config['columns']

        # Build the table object and add the requested metrics and PIPEs (in order).
        table = table_type(**table_config)
        for metric in metrics:
            if metric == PIPE:
                table.add_pipe()
            else:
                table.add_metric(metric)
        return self.tables.append(table)

    def add_text_area(self, text, title=None, width=79, justify='left', box=True):
        # type: (str, Optional[str], int, str, bool) -> None
        """Text area to place warnings, information, or other text content.

        Arguments:
            text (str): The text to be displayed within the text area. (newlines are ignored)
            title (str/None): Title to display above the text area.
            width (int): The max width of the area used to display the text.
            justify (str): Specify text alignment. ('left', 'right', 'center')
            box (bool): Wrap the text in a box.
                Example: +----------------+
                         | Text Area.     |
                         +----------------+
        """
        lines = [title] if title else []
        line = []  # type: List[str]
        # The box needs padding so remove 4 from provided width else just use width.
        text_area_width = (width - 4) if box else width
        borders = '| {} |' if box else '{}'
        text_justify = TEXT_ALIGNMENTS.get(justify, format_utils.LEFT_JUSTIFY)
        LOGGER.info('Building text area for title "{}".'.format(title))
        # TODO: PT-1933 - Add support for newlines in the provided text to maintain readability.
        for word in text.split():
            joined_text = ' '.join(line)
            # Only add new words to the line if we have room.
            if (len(joined_text) + len(word)) < text_area_width:
                line.append(word)
                continue
            text = text_justify.format(joined_text, wid=text_area_width)
            lines.append(borders.format(text) if box else text)
            line = []
        # If line has data it means it still has not been added to lines.
        if line:
            joined_text = ' '.join(line)
            text = text_justify.format(joined_text, wid=text_area_width)
            lines.append(borders.format(text) if box else text)
        if box:
            box_bar = '+{}+'.format('-' * (width - 2))
            lines.insert(0, box_bar)
            lines.append(box_bar)
        # Add a blank line for visual separator.
        lines.append('\n')
        self.tables.append('\n'.join(lines))

    def render_tables(self, jira=True, print_tables=True):
        # type: (bool, bool) -> Optional[str]
        """Render all of the tables that were added to the Report.

        Arguments:
            jira (bool): Add {noformat} tags for JIRA.
                Combined with title=True uses {noformat:title=TITLE}.
            print_tables (bool): Print the tables, don't just return them.

        Return:
            lines (list): Lines to print.
        """
        # Get all of the fields for all of the table metrics.
        self._get_table_fields()
        # There are field names which are just used to reference processed columns and may not exist in the lower API.
        fields = [field for field in self.fields if field in FIELD_INDEX]
        # TODO: PT-2378 - The same DataFrame is also cached in the API, how do we reduce redundancy?
        self.dataset = self.array_api.get_fields(fields)

        # Generate the table structure and printable lines.
        table_lines = []
        # TODO: PT-2369 - Replace this logic with asyncio...
        if SETTINGS['cpu']['serialize'] or int(len(self.tables)) / 10 <= 1:
            # Build the tables in series.
            for result in self._build_tables_in_series(jira):
                table_lines.append(result)
        else:
            # Build the tables in parallel.
            for result in self._build_tables_in_parallel(jira):
                table_lines.append(result)
        if print_tables:
            print('\n'.join(table_lines))
        return '\n'.join(table_lines)


class Table(object):
    """A collection of Metrics in tabular format for easy printing."""

    def __init__(self, title=None, timestamp=True, **kwargs):
        # type: (Optional[str], bool, **Dict[str, Any]) -> None
        """
        Arguments:
            title (str): A title to apply to the JIRA formatting header.
            timestamp (bool): Whether to include a timestamp column or not.

        Optional Keyword Arguments:
            box (bool): Whether to make the box-like structure of the table or not.
            grid (bool): Put a 'grid' around the table columns.  This provides visual breaks between each.
            headers (bool): Whether to include headers in the table or not.
            use_titles (bool): Whether to display titles or not.
        """
        self.box = kwargs.get('box', True)
        # Add '| Timestamp |' if we have requested a timestamp.
        self.columns = [PIPE, 'Timestamp', PIPE] if timestamp else [PIPE]
        self.dataset = pandas.DataFrame()
        self.metric_data = pandas.DataFrame()
        self.grid = kwargs.get('grid', False)
        self.headers = kwargs.get('headers', True)
        self.metrics = {}  # type: Dict[str, metric_base.Metric]
        self.required_fields = set()
        self.timestamp = timestamp
        self.title = title or ''
        self.use_titles = kwargs.get('use_titles', True)

    def add_metric(self, metric_name, **metric_kwargs):
        # type: (Union[str, metric_base.Metric], **Dict[str, Any]) -> None
        """Build and add a Metric to the table columns."""
        metric = metric_base.build_metric(metric_name, **metric_kwargs)
        self.metrics[metric.nice_name] = metric
        self.columns.append(metric.nice_name)
        # Add all fields that are required by the metric.
        for field in _get_required_fields(metric):
            self.required_fields.add(field)
        LOGGER.debug('Successfully added metric "{}" to table.'.format(metric_name))

    def add_pipe(self):
        # type: () -> None
        """Add a PIPE (visual separator) to the table columns."""
        if self.columns and self.columns[-1] != PIPE:
            # We don't want pipes back to back.
            self.columns.append(PIPE)
        else:
            self.columns.append(PIPE)

    @abc.abstractmethod
    def render_table(self, data_frame, frequency, jira_format=True):
        # type: (pandas.DataFrame, str, bool) -> str
        """Render the table with the given metrics and data_frame at a requested frequency."""
        table_lines = []

        self.dataset = data_frame

        # Drop rows where all required_fields values are empty.
        fields = [field for field in self.required_fields if field in FIELD_INDEX]
        self.dataset.dropna(how='all', subset=fields, inplace=True)

        # Process each of the metrics used in the Table(s).
        self._process_metrics(frequency)

        # If there isn't a trailing PIPE, add one.
        if self.columns[-1] != PIPE:
            self.columns.append(PIPE)

        # Apply header formatting:
        if jira_format:
            if self.use_titles and self.title:
                table_lines.append('{{noformat:title={}}}'.format(self.title))
            else:
                table_lines.append('{noformat}')
        elif self.use_titles and self.title:
            table_lines.append(self.title)

        # Render the table lines and table structure.
        # TODO: PT-2366 - Migrate and/or merge this logic with report_utils.
        table_lines.extend(self._build_table_structure())

        # Apply tail formatting:
        if jira_format:
            table_lines.append('{noformat}')

        # Add a final empty line for a visual break.
        table_lines.append('')
        return '\n'.join(table_lines)

    def _build_table_header(self, max_col_widths):
        # type: (List[int]) -> Tuple[List[str], str]
        """Build the table header based upon column names and lengths."""
        bar_separator = []
        header = []
        for index, column_name in enumerate(self.columns):
            if column_name == PIPE:
                # Just add the PIPE as a visual break.
                header.append(column_name)
                bar_separator.append('+--')
            else:
                column_width = max_col_widths[index]
                if column_width is None:
                    # This column is empty, so just use the width of the header itself.
                    column_width = len(column_name)
                bar_line = '-' * (column_width + 2)
                # Clean up composite names.
                column_name = column_name.split(',')[0]
                # Align the text.
                header.append(format_utils.auto_align_text(column_name, column_width))
                # Add the horizontal break.
                bar_separator.append(bar_line)

        # Merge all of the horizontal break segments together.
        # The bar_separator has 2 extra dashes at the end, so these are removed.
        # Example: ['+--', '+--', '+--'] -> '+--+--+'
        line_bar = ''.join(bar_separator)[:-2]
        return header, line_bar

    def _build_box_structure(self, max_col_widths):
        # type: (List[int]) -> List[str]
        """Build the box-like structure for the table."""
        lines = []
        # Padding is used between cells/columns.
        padding = ' ' * 2
        header, line_bar = self._build_table_header(max_col_widths)

        # Add the header if we have requested it.
        if self.headers:
            lines.append(padding.join(header))
            lines.append(line_bar)

        # For each row, build a string representation of the values and table-structure.
        for _, row in self.metric_data.iterrows():
            line = []
            for col_index, column in enumerate(self.columns):
                if column == PIPE:
                    line.append(PIPE)
                    continue
                if column in self.metrics:
                    alignment = self.metrics[column].alignment
                else:
                    alignment = 'auto'
                column_width = max_col_widths[col_index]
                # Convert the value to a string and justify/align it.
                value = _justify_text(str(row[column]), alignment, column_width)
                line.append(value)

            # Join the line together with appropriate padding.
            lines.append(padding.join(line))

        lines = _get_boxed_lines(lines, line_bar, self.box)
        return lines

    def _build_table_structure(self):
        # type: () -> List[str]
        """Build the overall table structure, based upon the requested columns."""
        if self.grid:
            # Grid separates every column with a PIPE.
            self.columns = _get_grid_layout(self.columns)
        max_col_widths = self._get_maximum_column_lengths()
        table_lines = self._build_box_structure(max_col_widths)
        return table_lines

    def _get_maximum_column_lengths(self):
        # type: () -> List[int]
        """Determine the maximum string length for each column."""
        table_structure = []
        for column_name in self.columns:
            if column_name == PIPE:
                table_structure.append(1)
                continue
            if column_name not in self.metric_data or self.metric_data[column_name].empty:
                # This can only happen if the table is completely empty.
                # Avoid crashing here and return None, so that we'll just use the length of the column name later on.
                table_structure.append(None)
                continue
            # Measure the length of the nice_name without the composite suffix.
            clean_name = column_name.split(',')[0]
            name_length = len(clean_name)
            # Get the maximum string length of all values within the column.
            max_value_length = self.metric_data[column_name].astype('str').str.len().max()
            # Get the maximum string length between the header and the values.
            table_structure.append(max([name_length, max_value_length]))
        return table_structure

    def _post_process(self):
        # type: () -> None
        """Post processing to ensure that all rows have placeholders or valid data."""
        self.metric_data.sort_values(by='Timestamp', inplace=True)
        # Drop empty rows and only fill the ones that make sense as per out Metrics an not fields:
        self.metric_data.dropna(how='all', subset=self.metrics.keys(), inplace=True)

        # Because we have now joined together values with various timestamps,
        # we need to fill in gaps where we didn't need a value before.
        for nice_name, metric in self.metrics.items():
            ser = self.metric_data[nice_name]
            if metric.fill:
                # Forward and backward fill most nearest values.
                # Forward fill should always be done first.  Otherwise we will end up with values before they existed.
                self.metric_data[nice_name] = ser.ffill().bfill()
            else:
                # Otherwise put the placeholder in the missing locations.
                ser.fillna(metric.placeholder, inplace=True)
            self.metric_data[nice_name] = ser

        # Drop any rows where we have exact duplicates across the processed Metrics within a timestamp.
        self.metric_data.dropna(how='all', subset=self.metrics.keys(), inplace=True)
        needed_keys = ['Timestamp'] + list(self.metrics.keys())
        # Drop duplicates based upon non-unique metrics.  i.e. anything that is not expected to have a duplicate.
        non_unique_metrics = ['Timestamp'] + [nice_name for nice_name, metric in self.metrics.items()
                                              if not isinstance(metric, metric_base.EventMetric)]
        self.metric_data.drop_duplicates(subset=non_unique_metrics, keep='first', inplace=True)
        self.metric_data = self.metric_data[needed_keys]

        # Fill any remaining NaNs with the correct placeholders.
        for metric in self.metrics.values():
            self.metric_data[metric.nice_name].fillna(metric.placeholder, inplace=True)

    def _process_metrics(self, frequency):
        # type: (str) -> None
        """Process all of the metrics, and their dependencies."""
        # TODO: PT-2369 - Run this in parallel via asyncio.
        for nice_name, metric in self.metrics.items():
            if nice_name in self.metric_data:
                continue
            self._process_metric(metric, frequency)

        # Post Processing in order to fill gaps for unique timestamps.
        if not self.metric_data.empty:
            self._post_process()

    def _process_metric(self, metric, frequency):
        # type: (metric_base.Metric, str) -> None
        """Process a single metric and process any metrics it is dependent upon."""
        needed_fields = [field for field in metric.required_fields if field in self.dataset]

        # If the metric is not already processed, then process it.
        if metric.nice_name not in self.metric_data:
            # Use the nice_name for required_metrics once they are processed!!!
            nice_name_required_metrics = []
            # If there are any metric dependencies, process those metrics first.
            for sub_metric_name in metric.required_metrics:
                sub_metric = metric_base.build_metric(sub_metric_name)

                # Update the names for required_metrics, numerators, denominators, etc.
                nice_name_required_metrics.append(sub_metric.nice_name)

                if sub_metric.nice_name not in self.metric_data:
                    # This metric needs to be processed; see if has already been instantiated.
                    if sub_metric.nice_name in self.metrics:
                        sub_metric = self.metrics[sub_metric.nice_name]
                    self._process_metric(sub_metric, frequency)

                if hasattr(metric, 'numerator') and sub_metric.field == metric.numerator:
                    metric.numerator = sub_metric.nice_name
                if hasattr(metric, 'denominator') and sub_metric.field == metric.denominator:
                    metric.denominator = sub_metric.nice_name

            # Update the required_metrics to use the nice_names.
            metric.required_metrics = nice_name_required_metrics
            # Process the metric with the fields/metrics it requires.
            needed_fields = META_KEYS + needed_fields
            if metric.required_metrics:
                needed_metrics = META_KEYS + metric.required_metrics
            else:
                needed_metrics = []
            metric_frame = pandas.concat([self.dataset[needed_fields],
                                          self.metric_data[needed_metrics]], keys='Timestamp', copy=False)
            # If there are no metrics then we end up adding empty rows, remove them and organize things.
            metric_frame.dropna(how='all', inplace=True)
            metric_frame.sort_values(by='Timestamp', inplace=True)
            metric_frame.reset_index(inplace=True, drop=True)

            # Add a placeholder if we have no data, otherwise process the Metric with the data subset.
            if metric_frame.empty:
                LOGGER.warning('The metric "{}" has no data.'.format(metric.nice_name))
            else:
                metric_frame = metric.process(metric_frame, frequency)

            # Merge in newly created metric data.
            if metric_frame.empty and self.metric_data.empty:
                # We will need placeholders for Timestamp, and controller.
                self.metric_data[metric.nice_name] = [metric.placeholder]
                # Include a 1-dimensional placeholder so we actually have a value.
                self.metric_data['Timestamp'] = None
                self.metric_data['controller'] = None
            elif metric_frame.empty:
                # We need to add a placeholder for the metric, we should already have Timestamp/controller.
                self.metric_data[metric.nice_name] = None
            elif self.metric_data.empty:
                # No need to merge with an empty frame, grab any placeholder columns and assign them to metric_frame.
                for key in self.metric_data.keys():
                    if key not in ('Timestamp', 'controller'):
                        metric_frame[key] = self.metric_data[key]
                self.metric_data = metric_frame
            else:
                # We need to merge on Timestamp and controller, as we may have unique data on both controllers.
                self.metric_data = pandas_utils.merge_on_timestamp([self.metric_data, metric_frame], META_KEYS)


class CSVTable(Table):
    """A CSV Formatted table."""

    def _post_process(self):
        # type: () -> None
        """Post processing to convert units back to raw."""
        for metric in self.metrics.values():
            # Convert units back to raw based upon the metric_type and scale unit.
            if isinstance(metric, metric_base.ScaledUnitsMetric):
                action = format_utils.to_raw
            elif isinstance(metric, metric_base.LatencyMetric):
                action = time_utils.to_raw_latency
            elif isinstance(metric, metric_base.PercentageMetric):
                action = lambda val: float(val.replace('%', ''))
            else:
                action = None
            if action:
                self.metric_data[metric.nice_name] = self.metric_data[metric.nice_name].apply(action)
        # Also run the default post-processing.
        super(CSVTable, self)._post_process()

    def render_table(self, data_frame, frequency, title=None):
        # type: (pandas.DataFrame, str, Optional[str]) -> str
        """Render the table with the given metrics and data_frame at a requested frequency."""
        # Use the new data_frame to generate and process the dataset via the requested Metrics.
        self.dataset = data_frame
        self._process_metrics(frequency)
        self.columns = [col for col in self.columns if col != PIPE]
        table_lines = self.metric_data[self.columns].to_csv(index=False)
        return table_lines


class HTMLTable(Table):
    """A HTML Formatted table."""

    def render_table(self, data_frame, frequency, title=None):
        # type: (pandas.DataFrame, str, Optional[str]) -> str
        """Render the table with the given metrics and data_frame at a requested frequency."""
        # Use the new data_frame to generate and process the dataset via the requested Metrics.
        self.dataset = data_frame
        self._process_metrics(frequency)
        self.columns = [col for col in self.columns if col != PIPE]
        # TODO: PT-2377 - Do something useful here with pandas.DataFrame.to_html(classes=) -> CSS classes
        # TODO: PT-2377 - Use the title as the table_id, this requires a newer version of pandas.
        # We can make the tables dynamic and prettier by applying CSS...
        table_lines = self.metric_data[self.columns].to_html()
        return table_lines


class JSONTable(Table):
    """A JSON Formatted table."""

    def render_table(self, data_frame, frequency, title=None):
        # type: (pandas.DataFrame, str, Optional[str]) -> str
        """Render the table with the given metrics and data_frame at a requested frequency."""
        # Use the new data_frame to generate and process the dataset via the requested Metrics.
        self.dataset = data_frame
        self._process_metrics(frequency)
        self.columns = [col for col in self.columns if col != PIPE]
        # We can make the tables dynamic and prettier by applying CSS...
        # TODO: Add index=False, if we update pandas to >=0.23.
        table_lines = self.metric_data[self.columns].to_json(orient='table')
        return table_lines


def _get_boxed_lines(lines, line_bar, box):
    # type: (List[str], Optional[str], bool) -> List[str]
    """Add a horizontal bars to the top and bottom of the table."""
    if box:
        # Adding the box around the table if requested.
        box_width = len(lines[0])
        box_line = '=' * box_width
        lines.insert(0, box_line)
        # If the last line of the box is line_bar then grid was used and we do not use the box tail.
        if lines[-1] != line_bar:
            lines.append(box_line)
    return lines


def _get_grid_layout(fields):
    # type: (List[str]) -> List[str]
    """Place grid columns into fields if a grid is required."""
    # Transform this: ['Name1', 'Name2']
    # into: ['|', 'Name1', '|', 'Name2', '|']
    new_fields = []
    # Removing any custom PIPEs so we do not have to setup special logic to add them later on.
    fields = [field for field in fields if field is not PIPE]
    for index, value in enumerate(fields):
        # Add PIPEs around all even numbered fields.
        if index % 2 == 0:
            new_fields.extend([PIPE, value, PIPE])
        else:
            new_fields.append(value)
    if new_fields[-1] is not PIPE:
        new_fields.append(PIPE)
    return new_fields


def _get_required_fields(metric):
    # type: (metric_base.Metric) -> List[str]
    """Get all of the required metrics related to the metric."""
    fields = []
    # There are field names which are just used to reference processed columns and may not exist in the lower API.
    fields.extend([field for field in metric.required_fields if field in FIELD_INDEX])
    for sub_metric in metric.required_metrics:
        if isinstance(sub_metric, str):
            sub_metric = metric_base.build_metric(sub_metric)
        fields.extend(_get_required_fields(sub_metric))
    return fields


def _justify_text(text, alignment, padding_width):
    # type: (str, str, int) -> str
    """Justify the text based upon requested alignment and padding width."""
    alignment = alignment or 'center'
    padding_width = padding_width if padding_width is not None else 2
    if alignment in TEXT_ALIGNMENTS:
        aligned = TEXT_ALIGNMENTS[alignment].format(text, wid=padding_width)
    else:
        aligned = format_utils.auto_align_text(text, padding_width)
    return aligned
