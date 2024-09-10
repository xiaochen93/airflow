def get_datetime_from_now(days=0, hours=1):
    from datetime import datetime
    today = datetime.now().replace(microsecond=0)
    import datetime
    one_day = datetime.timedelta(days=days)
    one_hour = datetime.timedelta(hours=hours)
    last24hours = today - one_day - one_hour
    return today, last24hours