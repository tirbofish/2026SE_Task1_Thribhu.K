from flask import request


def parse_log_filters():
    """Parse query parameters for filtering log entries.
    
    Supported filters:
    - start_time_gt, start_time_gte, start_time_lt, start_time_lte
    - end_time_gt, end_time_gte, end_time_lt, end_time_lte
    - time_worked_min, time_worked_max
    - log_timestamp_after, log_timestamp_before
    - username (exact match)
    - notes_contains (partial match in developer_notes)
    
    Returns:
        dict: Parsed filters with None values removed
    """
    filters = {
        'start_time_gt': request.args.get('start_time_gt'),
        'start_time_gte': request.args.get('start_time_gte'),
        'start_time_lt': request.args.get('start_time_lt'),
        'start_time_lte': request.args.get('start_time_lte'),
        
        'end_time_gt': request.args.get('end_time_gt'),
        'end_time_gte': request.args.get('end_time_gte'),
        'end_time_lt': request.args.get('end_time_lt'),
        'end_time_lte': request.args.get('end_time_lte'),
        
        'time_worked_min': request.args.get('time_worked_min'),
        'time_worked_max': request.args.get('time_worked_max'),
        
        'log_timestamp_after': request.args.get('log_timestamp_after'),
        'log_timestamp_before': request.args.get('log_timestamp_before'),
        
        'username': request.args.get('username'),
        'notes_contains': request.args.get('notes_contains'),
    }
    
    return {k: v for k, v in filters.items() if v is not None}


def apply_filters_to_query(query, conditions, params, filters):
    """Apply filters to SQL query.
    
    Args:
        query (str): Base SQL query
        conditions (list): List of WHERE conditions
        params (list): List of query parameters
        filters (dict): Dictionary of filter key-value pairs
    
    Returns:
        tuple: (updated_query, updated_conditions, updated_params)
    """
    if not filters:
        return query, conditions, params
    
    if 'start_time_gt' in filters:
        conditions.append("l.start_time > ?")
        params.append(filters['start_time_gt'])
    
    if 'start_time_gte' in filters:
        conditions.append("l.start_time >= ?")
        params.append(filters['start_time_gte'])
    
    if 'start_time_lt' in filters:
        conditions.append("l.start_time < ?")
        params.append(filters['start_time_lt'])
    
    if 'start_time_lte' in filters:
        conditions.append("l.start_time <= ?")
        params.append(filters['start_time_lte'])
    
    if 'end_time_gt' in filters:
        conditions.append("l.end_time > ?")
        params.append(filters['end_time_gt'])
    
    if 'end_time_gte' in filters:
        conditions.append("l.end_time >= ?")
        params.append(filters['end_time_gte'])
    
    if 'end_time_lt' in filters:
        conditions.append("l.end_time < ?")
        params.append(filters['end_time_lt'])
    
    if 'end_time_lte' in filters:
        conditions.append("l.end_time <= ?")
        params.append(filters['end_time_lte'])
    
    if 'time_worked_min' in filters:
        conditions.append("l.time_worked_minutes >= ?")
        params.append(int(filters['time_worked_min']))
    
    if 'time_worked_max' in filters:
        conditions.append("l.time_worked_minutes <= ?")
        params.append(int(filters['time_worked_max']))
    
    if 'log_timestamp_after' in filters:
        conditions.append("l.log_timestamp >= ?")
        params.append(filters['log_timestamp_after'])
    
    if 'log_timestamp_before' in filters:
        conditions.append("l.log_timestamp <= ?")
        params.append(filters['log_timestamp_before'])
    
    if 'username' in filters:
        conditions.append("u.username = ?")
        params.append(filters['username'])
    
    if 'notes_contains' in filters:
        conditions.append("l.developer_notes LIKE ?")
        params.append(f"%{filters['notes_contains']}%")
    
    return query, conditions, params