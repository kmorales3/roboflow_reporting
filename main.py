from datetime import datetime

import pandas
import requests
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from roboflow import Roboflow


def revised_worksplace_annot_totals(api_key, workspace):

    hl_summary_ls = []
    detail_summary_ls = []
    job_summary_ls = []

    rf = Roboflow(api_key)
    projects = rf.workspace(workspace).project_list

    for project in projects:

        # job status detail in the format: [0]total images, [1]approved images, [2]rejected images, [3]annotated images,
        #   [4]unannotated images, [5]job count, [6]labeler list
        assigned_summary_detail = [0, 0, 0, 0, 0, 0, []]
        review_summary_detail = [0, 0, 0, 0, 0, 0, []]
        complete_summary_detail = [0, 0, 0, 0, 0, 0, []]

        api_url = f'https://api.roboflow.com/{project["id"]}/jobs?api_key={api_key}'
        response = requests.get(api_url)
        data = response.json()

        for job in data['jobs']:
            try:
                job_summary_ls.append([project['name'], job['status'], job['name'], job['id'],
                                       f"{job['labeler'].split('.')[0].title()} "
                                       f"{job['labeler'].split('@')[0].split('.')[1].title()}",
                                       f"{job['reviewer'].split('.')[0].title()} "
                                       f"{job['reviewer'].split('@')[0].split('.')[1].title()}", job['numImages'],
                                       job['approved'], job['rejected'], job['annotated'], job['unannotated']])
            except IndexError:
                if job['labeler'] == 'AUTOLABEL':
                    continue
                else:
                    print(f'Error at job: {job["name"]}')
                    for item in job:
                        print(item)

            if job['status'] == 'assigned':
                assigned_summary_detail[0] += job['numImages']
                assigned_summary_detail[1] += job['approved']
                assigned_summary_detail[2] += job['rejected']
                assigned_summary_detail[3] += job['annotated']
                assigned_summary_detail[4] += job['unannotated']
                assigned_summary_detail[5] += 1
                if job['labeler'] not in assigned_summary_detail[6]:
                    assigned_summary_detail[6].append(job['labeler'])
            if job['status'] == 'assigned':
                review_summary_detail[0] += job['numImages']
                review_summary_detail[1] += job['approved']
                review_summary_detail[2] += job['rejected']
                review_summary_detail[3] += job['annotated']
                review_summary_detail[4] += job['unannotated']
                review_summary_detail[5] += 1
                if job['labeler'] not in review_summary_detail[6]:
                    review_summary_detail[6].append(job['labeler'])
            elif job['status'] == 'complete':
                complete_summary_detail[0] += job['numImages']
                complete_summary_detail[1] += job['approved']
                complete_summary_detail[2] += job['rejected']
                complete_summary_detail[3] += job['annotated']
                complete_summary_detail[4] += job['unannotated']
                complete_summary_detail[5] += 1
                if job['labeler'] not in complete_summary_detail[6]:
                    complete_summary_detail[6].append(job['labeler'])

        hl_summary_ls.append([project['name'], 'assigned (Annotating)', assigned_summary_detail[5],
                              assigned_summary_detail[0], len(assigned_summary_detail[6])])
        hl_summary_ls.append([project['name'], 'review', review_summary_detail[5],
                              review_summary_detail[0], len(review_summary_detail[6])])
        hl_summary_ls.append([project['name'], 'complete (Dataset)', complete_summary_detail[5],
                              complete_summary_detail[0], len(complete_summary_detail[6])])

        detail_summary_ls.append([project['name'], 'assigned (Annotating)', assigned_summary_detail[0],
                                  assigned_summary_detail[1], assigned_summary_detail[2],
                                  assigned_summary_detail[3], assigned_summary_detail[4]])
        detail_summary_ls.append([project['name'], 'review', review_summary_detail[0],
                                  review_summary_detail[1], review_summary_detail[2],
                                  review_summary_detail[3], review_summary_detail[4]])
        detail_summary_ls.append([project['name'], 'complete (Dataset)', complete_summary_detail[0],
                                  complete_summary_detail[1], complete_summary_detail[2],
                                  complete_summary_detail[3], complete_summary_detail[4]])

    dfs_for_upload = []

    hl_summary_df = pandas.DataFrame(hl_summary_ls, columns=['project', 'job_status', 'job_count', 'image_count',
                                                             'labeler_count']).sort_values(by=['project', 'job_status'])
    detail_summary_df = pandas.DataFrame(detail_summary_ls, columns=['project', 'job_status', 'image_count', 'approved',
                                                                     'rejected', 'annotated',
                                                                     'unannotated']).sort_values(by=['project',
                                                                                                     'job_status'])
    job_summary_df = pandas.DataFrame(job_summary_ls, columns=['project', 'job_status', 'job_name', 'job_id', 'labeler',
                                                               'reviewer', 'image_count', 'approved', 'rejected',
                                                               'annotated', 'unannotated']).sort_values(by=['project',
                                                                                                            'job_status'])

    dfs_for_upload.append([hl_summary_df, 'hl_summary_df'])
    dfs_for_upload.append([detail_summary_df, 'detail_summary_df'])
    dfs_for_upload.append([job_summary_df, 'job_summary_df'])

    return dfs_for_upload


def save_to_blob(df_list, account_url, container_name):

    try:
        print('Azure Blob Storage testing')

        default_credential = DefaultAzureCredential()

        blob_service_client = BlobServiceClient(account_url, credential=default_credential)

        f_name_date = str(datetime.now().date())
        f_name_hour = str(datetime.now().time().hour)

        blob_container = blob_service_client.get_container_client(container=container_name)

        if not blob_container.exists():
            blob_service_client.create_container(container_name)

        f_name_prefix = f'{f_name_date}_{f_name_hour}'

        for df in df_list:
            local_file_name = f'{f_name_prefix}_{df[1]}.csv'
            new_blob = blob_service_client.get_blob_client(container=container_name, blob=local_file_name)
            upload_data = df[0].to_csv(index=False)
            new_blob.upload_blob(upload_data, blob_type='BlockBlob')

    except Exception as ex:
        print(f'Exception: {ex}')
