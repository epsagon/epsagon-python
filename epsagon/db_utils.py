
import sys
import re
import sqlparse
from epsagon.utils import print_debug
from epsagon.constants import OBFUSCATION_MASK


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
    returns regex string to split on option(s)
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


def get_sql_bounds():
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

    :param token:
    :param config: left bound is
    :return:
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

    token_type = get_sql_bounds().get(operation, {}).get('token_type')
    query = []

    for token in tokens:
        t = str(token)

        if isinstance(token, token_type):

            values, pos = get_query_values(token, operation)

            if not isinstance(values, list):
                continue

            values = mask_values(values, operation)

            t = t[:pos[0]] \
                + values \
                + t[pos[1]:]

        query.append(t)
    return ''.join(query)


def obfuscate_sql_query(query, operation):
    """
    Obfuscate SQL queries to protect sensitive uploads
    :param query: The SQL query string
    :param operation: Operation in DB
    :return: the obfuscated query (string)
    :var bounds: specifier for locating values based upon operation
    :var bounds: token_type is sqlparse type
    :var bounds: leftmost bound and rightmost bound are absolute limits
    :var bounds: separator is the symbol(s) between values
    :var bounds: signal is a preceding identifier for each value
    """


    if isinstance(query, bytes):
        query = query.decode('UTF-8')

    if isinstance(operation, bytes):
        operation = operation.decode('UTFå-8')

    if operation not in get_sql_bounds().keys():
        return query

    parsed_query = sqlparse.parse(query)
    obfuscated_query = []

    for q in parsed_query:
        obfuscated = _obfuscate_query(q.tokens, operation)
        obfuscated_query.append(obfuscated)

    obfuscated_query = ''.join(obfuscated_query)

    print_debug('obfuscated:')
    print_debug(obfuscated_query)

    return obfuscated_query
