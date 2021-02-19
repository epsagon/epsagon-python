"""
DB Utilities for Epsagon module.
"""

import re
import sqlparse
from epsagon.utils import print_debug
from epsagon.constants import OBFUSCATION_MASK

try:
    from psycopg2.errors import SyntaxError as PsycopSyntaxError
except ImportError:
    class PsycopSyntaxError(Exception):
        pass

try:
    from sqlalchemy.exc import SqlProgrammingError
except ImportError:
    class SqlProgrammingError(Exception):
        pass


def database_connection_type(hostname, default_type):
    """
    returns known DB types based on the hostname
    :param hostname: hostname from the URL
    :return: string type, or default type
    """
    if 'rds.amazonaws' in hostname:
        return 'rds'
    if 'redshift.amazonaws' in hostname:
        return 'redshift'
    return default_type


def build_split_string(options):
    """
    Returns regex string to split on option(s)
    :param options: Union[str: 1 option, list[str]: multiple options]
    :param options: options to split string on
    :return: string type, compatible for multiple options of regex split
    """
    if isinstance(options, list):
        options = '|'.join(map(re.escape, options))

    # if options is not a string by now param was invalid
    if not options or not isinstance(options, str):
        return ''

    return '({options})'.format(options=options)


def clean(x):
    """
    Removes extraneous whitespace from strings
    :param x: string to clean
    :return: string with extraneous whitespace removed
    """
    return ' '.join(str(x).split())


def queries_eq(*queries):
    """
    Boolean validator whether queries are equal
    :param queries: queries to validate
    :return: boolean signaling equality
    """
    return all(clean(q) == clean(queries[0]) for q in queries)


def get_sql_bounds():
    """
    Bounds used for determining sql parsing
    :return: dict of bounds by operation
    """
    return {
        'select': {
            'token_type': sqlparse.sql.Where,
            'left_bound': 'WHERE ',
            'right_bound': None,
            'separators': [')', ' AND ', ' OR '],
            'operators': ['>=', '<=', '>', '<', '=', '<>']
        },
        'insert': {
            'token_type': sqlparse.sql.Values,
            'left_bound': 'VALUES (',
            'right_bound': ')',
            'separators': ', ',
            'operators': None,
        },
    }


def get_query_values(token, operation):
    """
    Gets list of hardcoded values in array
    :param token: SQL token to parse
    :param operation: DB operation
    :return: values - list of values split by separators
    :return: positions - indices of values in token string
    """

    t = str(token)
    bounds = get_sql_bounds().get(operation, {})
    left_bound = bounds.get('left_bound')
    right_bound = bounds.get('right_bound')
    separators = bounds.get('separators')

    separators = build_split_string(separators)

    positions = (
        t.upper().find(left_bound) + len(left_bound) if left_bound else -1,
        t.upper().find(right_bound) if right_bound else len(t) - 1
    )

    if -1 in positions or positions[0] > positions[1]:
        print_debug('could not obfuscate clause: {clause}'
                    .format(clause=type(token)))
        return t, positions

    values = t[positions[0]:positions[1]]
    values = re.split(separators, values, flags=re.IGNORECASE) or []

    return values, positions


def mask_values(values, operation):
    """
    Obfuscates list of values with Mask, depending on Operations allowed
    :param values: list of values in query
    :param operation: DB operation
    :return: list of obfuscated/masked values
    """
    ops = get_sql_bounds().get(operation, {}).get('operators')
    ops = build_split_string(ops)

    for i, v in enumerate(values[::2]):
        i *= 2

        if ops:
            v = re.split(ops, v, flags=re.IGNORECASE)
            if len(v) != 3:
                continue

            v[0] = v[0].strip()
            v[2] = OBFUSCATION_MASK
            v = ''.join(v)
        else:
            v = OBFUSCATION_MASK

        values[i] = v

    return ''.join(values)


def _obfuscate_query(tokens, operation):
    """
    Inner Method for each obfuscating individual query
    :param tokens: list of tokens in 1 query
    :param operation: DB operation
    :return: string of obfuscated query
    """
    token_type = get_sql_bounds().get(operation, {}).get('token_type')
    query = []

    for token in tokens:
        t = str(token)

        if isinstance(token, token_type):

            values, pos = get_query_values(token, operation)

            if not values or not isinstance(values, list):
                continue

            values = mask_values(values, operation)

            t = t[:pos[0]] \
                + values \
                + t[pos[1]:]

        query.append(t)
    return ''.join(query)


def obfuscate_sql_query(query, operation):
    """
    Obfuscate SQL queries to protect sensitive ops
    :param query: The SQL query string to obfuscate
    :param operation: Operation in DB
    :return: string of obfuscated queries
    """

    original_query = query

    try:
        if isinstance(query, bytes):
            query = query.decode('UTF-8')

        if isinstance(operation, bytes):
            operation = operation.decode('UTFå-8')

        if operation not in get_sql_bounds().keys():
            return original_query

        parsed_query = sqlparse.parse(query)
        obfuscated_query = []

        for q in parsed_query:
            obfuscated = _obfuscate_query(q.tokens, operation)
            obfuscated_query.append(obfuscated)

        obfuscated_query = ''.join(obfuscated_query)

    except (PsycopSyntaxError, SqlProgrammingError, ValueError) as err:
        print_debug('Err while obfuscating: {err}'.format(err=err))
        return original_query

    return obfuscated_query
