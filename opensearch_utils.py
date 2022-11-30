from typing import Dict

import requests
from requests_aws4auth import AWS4Auth
from datetime import datetime


def get_snapshot_status(host: str, awsauth: AWS4Auth, repo_name: str = None, snapshot_name: str = None):
    """
    Retrieves a detailed description of the current state for each shard participating in the snapshot.
    """
    if repo_name and snapshot_name:
        path = f'/_snapshot/{repo_name}/{snapshot_name}/_status'
    elif repo_name:
        path = f'/_snapshot/{repo_name}/_status'
    else:
        path = f'/_snapshot/_status'

    url = host + path
    r = requests.get(url, auth=awsauth)
    print(f"Taking/restoring snapshot in progress: {r.text}")


def list_snapshots_in_repo(host: str, repo_name: str, awsauth: AWS4Auth) -> Dict:
    """
    List all snapshots in a repository
    """
    path = f'/_snapshot/{repo_name}/_all'
    url = host + path

    r = requests.get(url, auth=awsauth)
    snapshots = r.json().get("snapshots", [])
    print(f'Snapshot count = {len(snapshots)}')
    print(r.text)

    return snapshots


def list_all_repositories(host: str, awsauth: AWS4Auth):
    """
    List all repositories
    """
    path = '/_snapshot/_all'
    url = host + path

    r = requests.get(url, auth=awsauth)
    print(f"List of repositories: {r.text}")


def register_repository(host: str, awsauth: AWS4Auth, repo_name: str, bucket_name: str, region: str, role_arn: str):
    """
    Register a snapshot repository
    """
    path = f'/_snapshot/{repo_name}'
    url = host + path

    payload = {
        "type": "s3",
        "settings": {
            "bucket": bucket_name,
            "region": region,
            "role_arn": role_arn
        }
    }
    headers = {"Content-Type": "application/json"}
    r = requests.put(url, auth=awsauth, json=payload, headers=headers)
    print(f"Registering a repo: {repo_name}")
    print(r.text)


def take_snapshot(host: str, awsauth: AWS4Auth, repo_name: str, snapshot_name: str = None) -> str:
    """
    Take a snapshot in a repo. If snapshot_name is omitted, it will use current datetime string as name.
    Return snapshot name.
    """
    if snapshot_name is None:
        # Use current datetime as snapshot name
        now = datetime.now()
        snapshot_name = now.strftime("%Y%m%d-%H%M%S")
    path = f'/_snapshot/{repo_name}/{snapshot_name}'
    url = host + path

    r = requests.put(url, auth=awsauth)
    print(f"Taking a snapshot from repo {repo_name}: {snapshot_name}")
    print(r.text)

    return snapshot_name


def delete_one_snapshot(host: str, awsauth: AWS4Auth, repo_name: str, snapshot_name: str):
    """
    Deletes a snapshot.
    """
    path = f'/_snapshot/{repo_name}/{snapshot_name}'
    url = host + path

    r = requests.delete(url, auth=awsauth)
    print(f"Deleting snapshot: {snapshot_name}")
    print(r.text)


def delete_one_repository(host: str, awsauth: AWS4Auth, repo_name: str):
    """
    Deletes a snapshot.
    """
    path = f'/_snapshot/{repo_name}'
    url = host + path

    r = requests.delete(url, auth=awsauth)
    print(f"Deleting a repository: {repo_name}")
    print(r.text)


def restore_snapshot(host: str, awsauth: AWS4Auth, repo_name: str, snapshot_name: str):
    """
    Restore snapshot (all indexes except Dashboards and fine-grained access control)
    """
    path = f'/_snapshot/{repo_name}/{snapshot_name}/_restore'
    url = host + path

    payload = {
        # "indices": "*,-.kibana*",  # All indices except indices matching .kibana*
        "indices": "*,-.kibana*",  # All indices
        "include_global_state": True,
        "ignore_unavailable": True
    }
    headers = {"Content-Type": "application/json"}
    r = requests.post(url, auth=awsauth, json=payload, headers=headers)
    print(f"Restoring from snapshot: {snapshot_name}")
    print(r.text)


def get_snapshot(host: str, awsauth: AWS4Auth, repo_name: str, snapshot_name: str):
    """
    Return information of a snapshot.
    Sample returned value:
        {
            "snapshot" : "20221130-054427",
            "uuid" : "5tsX98juSyWdPMXgXWSUgA",
            "version_id" : 7100299,
            "version" : "7.10.2",
            "indices" : [ ".kibana_1", "kibana_sample_data_ecommerce" ],
            "data_streams" : [ ],
            "include_global_state" : true,
            "state" : "SUCCESS",
            "start_time" : "2022-11-30T05:44:27.184Z",
            "start_time_in_millis" : 1669787067184,
            "end_time" : "2022-11-30T05:44:28.385Z",
            "end_time_in_millis" : 1669787068385,
            "duration_in_millis" : 1201,
            "failures" : [ ],
            "shards" : {
              "total" : 2,
              "failed" : 0,
              "successful" : 2
            }
        }
    """
    path = f'/_snapshot/{repo_name}/{snapshot_name}'
    url = host + path
    headers = {"Content-Type": "application/json"}
    r = requests.get(url, auth=awsauth, headers=headers)
    snapshots = r.json().get('snapshots', [])

    if len(snapshots) > 0:
        return snapshots[0]


def close_index(host: str, awsauth: AWS4Auth, index_name: str):
    """
    Close an index
    """
    path = f'/{index_name}/_close'
    url = host + path
    headers = {"Content-Type": "application/json"}
    r = requests.post(url, auth=awsauth, json={}, headers=headers)
    print(f"Closing an index: {index_name}")
    print(r.text)


def get_latest_snapshot(host: str, repo_name: str, awsauth: AWS4Auth) -> Dict:
    """
    Get information of the latest snapshot.
    """
    # List all snapshots in all repository
    snapshots = list_snapshots_in_repo(host, repo_name, awsauth)

    # Get the snapshot with the latest start_time
    if len(snapshots) > 0:
        # Sort snapshots by start_time
        sortedlist = sorted(snapshots, key=lambda d: d['start_time'])
        print(f'Found latest snapshot in {repo_name}: {sortedlist[-1].get("snapshot")}')
        return sortedlist[-1]
    else:
        print('No snapshot found.')


def list_indices(host: str, awsauth: AWS4Auth):
    """
    List all indices including docs count in the domain.
    """
    path = f'/_cat/indices?format=json'
    url = host + path
    headers = {"Content-Type": "application/json"}
    r = requests.get(url, auth=awsauth, headers=headers)
    print(f"Indices: {r.text}")

    return r.json()