import datetime
import dateutil
from io import StringIO
import os
import sys
sys.path.extend(['/home/tapis/.local/lib/python3.7/site-packages',
                 '/usr/local/lib/python3.7/site-packages',
                 '/usr/local/lib/python3.7/site-packages/IPython/extensions',
                 '/home/tapis/.ipython'])

import matplotlib.pyplot as plt
import matplotlib.dates as md
import pandas as pd

from agavepy.actors import get_context, get_client, send_bytes_result
from tapipy.tapis import Tapis



# defaults for the username, password, and base_url ----
username = os.environ.get('username', 'testuser2')
password = os.environ.get('password', 'testuser2')
base_url = os.environ.get('base_url', 'https://dev.tapis.io')

# location to write output file -
out = '/home/tapis/output.png'

# create Tapis client and get tokens --
try:
    t = Tapis(base_url=base_url, username=username, password=password)
    t.get_tokens()
except Exception as e:
    print(f"got exception trying to generate tapis client; e: {e}")
    raise e


def get_datetime_range(time):
    """
    Generate start and end datetime from the time of the alert.
    """
    print(f"top of get_datetime_range; time: {time}")
    try:
        end_datetime = dateutil.parser.isoparse(time) + datetime.timedelta(days=1)
    except Exception as e:
        print(f"got exception trying to convert time string to datetime; e: {e}")
        raise e
    # create a range of exactly 1 day:
    start_time = end_datetime - datetime.timedelta(days=1)
    print(f"computed start_time: {start_time}; end_time: {end_datetime}")
    return start_time, end_datetime


def get_measurements(project_id, site_id, inst_id, start_datetime, end_datetime):
    """
    Return csv of measurement data for a given instrument within a project and site across a datetime range.
    """
    print(f"top of get_measurements: {inst_id}; {project_id}; {site_id}; {start_datetime}; {end_datetime}")
    start_time = datetime.datetime.strftime(start_datetime, '%Y-%m-%dT%H:%M:%SZ')
    end_time = datetime.datetime.strftime(end_datetime, '%Y-%m-%dT%H:%M:%SZ')
    try:
        return t.streams.list_measurements(inst_id=inst_id,
                                           project_uuid=project_id,
                                           site_id=site_id,
                                           start_date=start_time,
                                           end_date=end_time,
                                           format='csv')
    except Exception as e:
        print(f"Got exception trying to retrieve measurements; e: {e}")
        raise e


def create_dataframe(csv_data):
    """
    Generate a pandas datafreame from the binary csv data returned from streams.
    """
    inp = StringIO(str(csv_data, 'utf-8'))
    df = pd.read_csv(inp)
    df['datetime']=pd.to_datetime(df['time'])
    df.set_index('datetime',inplace=True)
    return df


def generate_plot_from_df(df):
    """
    Generates a plot using matlab from the pandas dataframe.
    """
    xfmt = md.DateFormatter('%H:%M:%S')
    df.plot(lw=1,
            colormap='jet',
            marker='.',
            markersize=12,
            title='Timeseries Stream Output',
            rot=90).xaxis.set_major_formatter(xfmt)
    plt.tight_layout()
    plt.legend(loc='best')
    plt.savefig(out)

def upload_plot(time):
    """
    Upload the plot to a tapis S3 bucket.
    """
    system_id = os.environ.get('system_id', 'tapis-demo')
    dest_path = os.environ.get('destination_path', f'/plot_{time}.png')
    try:
        t.upload(system_id=system_id, source_file_path=out, dest_file_path=dest_path)
    except Exception as e:
        print(f"got exception trying to upload file: {e}")
        raise e
    print(f'{dest_path} uploaded successfully.')


def main():
    context = get_context()
    d = context['message_dict']
    print("Got JSON: {}".format(d))
    try:
        # message variables --
        project_id = d['project_id']
        site_id = d['site_id']
        inst_id = d['inst_id']
        time = d['time']
    except KeyError as ke:
        print(f"Required field missing: {ke}")
        raise ke
    except Exception as e:
        print(f"Unexpected exception: {e}.")
        raise e
    start_datetime, end_datetime = get_datetime_range(time)
    csv_data = get_measurements(project_id, site_id, inst_id, start_datetime, end_datetime)
    df = create_dataframe(csv_data)
    generate_plot_from_df(df)
    upload_plot(time)


if __name__ == '__main__':
    main()
