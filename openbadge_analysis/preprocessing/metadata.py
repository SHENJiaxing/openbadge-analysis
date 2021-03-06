import pandas as pd
import json
from ..core import mac_address_to_id

def _id_to_member_mapping_fill_gaps(idmap, time_bins_size='1min'):
    """ Fill gaps in a idmap
    Parameters
    ----------
    idmap : id mapping object

    time_bins_size : str
        The size of the time bins used for resampling.  Defaults to '1min'.

    Returns
    -------
    pd.DataFrame :
        idmap, after filling gaps.
    """
    df = idmap.to_frame().reset_index()
    df.set_index('datetime', inplace=True)
    s = df.groupby(['id'])['member'].resample(time_bins_size).fillna(method='ffill')
    s = s.reorder_levels((1,0)).sort_index()
    return s


def id_to_member_mapping(fileobject, time_bins_size='1min', tz='US/Eastern', fill_gaps=True):
    """Creates a mapping from badge id to member, for each time bin, from proximity data file.
    
    Parameters
    ----------
    fileobject : file or iterable list of str
        The proximity data, as an iterable of JSON strings.
    
    time_bins_size : str
        The size of the time bins used for resampling.  Defaults to '1min'.
    
    tz : str
        The time zone used for localization of dates.  Defaults to 'US/Eastern'.

    fill_gaps : boolean
        If True, the code will ensure that a value exists for every time by by filling the gaps
        with the last seen value

    Returns
    -------
    pd.Series :
        A mapping from badge id to member, indexed by datetime and id.
    """
    
    def readfile(fileobject):
        for line in fileobject:
            data = json.loads(line)['data']

            yield (data['timestamp'],
                   mac_address_to_id(data['badge_address']),
                   str(data['member']))
    
    df = pd.DataFrame(readfile(fileobject), columns=['timestamp', 'id', 'member'])
    # Convert the timestamp to a datetime, localized in UTC
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True) \
            .dt.tz_localize('UTC').dt.tz_convert(tz)
    del df['timestamp']

    # Group by id and resample
    df = df.groupby([
        pd.TimeGrouper(time_bins_size, key='datetime'),
        'id'
    ]).first()

    # Extract series
    s = df.sort_index()['member']

    # Fill in gaps, if requested to do so
    if fill_gaps:
        s = _id_to_member_mapping_fill_gaps(s, time_bins_size=time_bins_size)

    return s


def voltages(fileobject, time_bins_size='1min', tz='US/Eastern'):
    """Creates a DataFrame of voltages, for each member and time bin.
    
    Parameters
    ----------
    fileobject : file or iterable list of str
        The proximity data, as an iterable of JSON strings.
    
    time_bins_size : str
        The size of the time bins used for resampling.  Defaults to '1min'.
    
    tz : str
        The time zone used for localization of dates.  Defaults to 'US/Eastern'.
    
    Returns
    -------
    pd.Series :
        Voltages, indexed by datetime and member.
    """
    
    def readfile(fileobject):
        for line in fileobject:
            data = json.loads(line)['data']

            yield (data['timestamp'],
                   str(data['member']),
                   float(data['voltage']))
    
    df = pd.DataFrame(readfile(fileobject), columns=['timestamp', 'member', 'voltage'])

    # Convert the timestamp to a datetime, localized in UTC
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True) \
                       .dt.tz_localize('UTC').dt.tz_convert(tz)
    del df['timestamp']

    # Group by id and resample
    df = df.groupby([
        pd.TimeGrouper(time_bins_size, key='datetime'),
        'member'
    ]).mean()
    
    df.sort_index(inplace=True)
    
    return df['voltage']


def sample_counts(fileobject, tz='US/Eastern', keep_type=False):
    """Creates a DataFrame of sample counts, for each member and raw record

    Parameters
    ----------
    fileobject : file or iterable list of str
        The proximity or audio data, as an iterable of JSON strings.

    tz : str
        The time zone used for localization of dates.  Defaults to 'US/Eastern'.

    keep_type : boolean
        If set to True, the type of the record will be returned as well


    Returns
    -------
    pd.Series :
        Counts, indexed by datetime, type and member.
    """

    def readfile(fileobject):
        for line in fileobject:
            raw_data = json.loads(line)
            data = raw_data['data']
            type = raw_data['type']

            if type == 'proximity received':
                cnt = len(data['rssi_distances'])
            elif type == 'audio received':
                cnt = len(data['samples'])
            else:
                cnt = -1

            yield (data['timestamp'],
                str(type),
                str(data['member']),
                int(cnt))

    df = pd.DataFrame(readfile(fileobject), columns=['timestamp' ,'type', 'member',
                                                     'cnt'])

    # Convert the timestamp to a datetime, localized in UTC
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True) \
        .dt.tz_localize('UTC').dt.tz_convert(tz)
    del df['timestamp']

    if keep_type:
        df.set_index(['datetime','type','member'],inplace=True)
    else:
        del df['type']
        df.set_index(['datetime', 'member'], inplace=True)
    df.sort_index(inplace=True)

    return df
