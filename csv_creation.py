import os
import re
from datetime import datetime

import pandas
from dateutil import tz


# Helper function to extract date and hour from the file name
def extract_date_hour(file_name):
    match = re.search(r'\d{4}-\d{2}-\d{2}_\d{1,2}', file_name)
    if match:
        datetime_str = match.group()
        return datetime_str
    return None


def compare_job_dfs():
    master_csv_loc = r'C:\Users\c883206\OneDrive - BNSF Railway\image_utils\image_utils\by_job.csv'
    hourly_csv_loc = r'C:\Users\c883206\OneDrive - BNSF Railway\Annotation Dashboard and Reporting\annot_stats_testing'

    if os.path.exists(master_csv_loc):
        full_df = pandas.read_csv(master_csv_loc)
        full_df['date_tm_comb'] = full_df["date"] + '_' + full_df["hour"].astype(str)
    else:
        full_df = pandas.DataFrame(columns=['date', 'hour', 'project', 'job_status', 'job_name', 'job_id', 'labeler',
                                        'reviewer', 'image_count', 'approved', 'rejected', 'annotated', 'unannotated',
                                        'date_tm_comb'])

    job_df_diff_list = []
    new_data_df = pandas.DataFrame()

    for file in os.listdir(hourly_csv_loc):
        if 'job_summary' in file and file.endswith('.csv'):
            # get and convert date and time of reporting csv from csv filename
            date_tm = extract_date_hour(file)
            date_time_for_tz = datetime.strptime(f'{date_tm}:00:00', '%Y-%m-%d_%H:%M:%S').replace(
                tzinfo=tz.gettz('UTC'))
            tx_datetime = date_time_for_tz.astimezone(tz.gettz('America/Chicago')).strftime('%Y-%m-%d_%H')
            tx_dt_parts = tx_datetime.split('_')
            frmt_tx_dt = tx_dt_parts[0] + '_' + str(int(tx_dt_parts[1]))
            if frmt_tx_dt not in full_df['date_tm_comb'].values:
                temp_df = pandas.read_csv(os.path.join(hourly_csv_loc, file))
                temp_df['date'] = tx_datetime.split('_')[0]
                temp_df['hour'] = int(tx_datetime.split('_')[1])
                temp_df['date_tm_comb'] = temp_df['date'] + "_" + temp_df['hour'].astype(str)
                new_data_df = pandas.concat([new_data_df, temp_df])

    # full_df.to_csv('full_df.csv')
    if not new_data_df.empty:
        labeler_df_list = [df for _, df in new_data_df.groupby('labeler')]

        for listed_labeler in labeler_df_list:
            job_df_list = [df for _, df in listed_labeler.groupby('job_id')]

            for listed_job in job_df_list:
                listed_job = listed_job.sort_values(by=['date', 'hour'])
                temp_diff_df = listed_job[['image_count', 'approved', 'rejected', 'annotated', 'unannotated']].diff()
                if not (temp_diff_df == 0).all(axis=None):
                    temp_diff_df.iloc[0] = listed_job.iloc[0][['image_count', 'approved', 'rejected', 'annotated',
                                                               'unannotated']]
                    temp_diff_df.iloc[0]['unannotated'] = 0
                    temp_diff_df = temp_diff_df.fillna(int(0))
                    temp_diff_df = temp_diff_df.clip(0)
                    job_df_diff_list.append(pandas.concat([listed_job[['date_tm_comb', 'date', 'hour', 'project',
                                                                   'job_status', 'job_name', 'job_id', 'labeler',
                                                                   'reviewer']], temp_diff_df], axis=1))

        combined_job_diff_df = pandas.concat(job_df_diff_list).sort_values(by=['date', 'hour', 'labeler'])

        combined_job_diff_df['labeler'] = combined_job_diff_df['labeler'].str.replace(r'\d', '', regex=True)
        combined_job_diff_df['workspace'] = 'Ground AYC'

        combined_job_diff_df.to_csv('by_job.csv', index=False)

compare_job_dfs()  
