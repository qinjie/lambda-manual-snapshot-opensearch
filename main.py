import boto3
from requests_aws4auth import AWS4Auth

from opensearch_utils import register_repository, list_all_repositories, list_snapshots_in_repo, get_snapshot_status, \
    take_snapshot, restore_snapshot, delete_one_repository, delete_one_snapshot, get_snapshot, close_index, \
    get_latest_snapshot, list_indices

# # Settings
# host_source = '<DOMAIN_ENDPOINT_WITH_HTTPS>'  # 源头域终端节点
# host_target = '<DOMAIN_ENDPOINT_WITH_HTTPS>'  # 目标域终端节点
# bucket_name = '<BUCKET_NAME>'  # S3桶名
# region = '<AWS_REGION>'  # S3桶的区域
# role_arn = '<ARN_OF_IAM_ROLE_LAMBDA>'  # Lambda函数的角色ARN
# repo_name = '<REPOSITORY_NAME>'  # 自定义

# Settings
host_source = 'https://vpc-mydomain-su6vi7ww5kwtqkojjfd5uw3xly.ap-southeast-1.es.amazonaws.com'  # mydomain
host_target = 'https://vpc-mydomain-2-wqolsf5ku4j5e3ubmpdkep4jxm.ap-southeast-1.es.amazonaws.com'  # mydomain-2
bucket_name = 'elasticsearch-snapshots-460453255610'
region = 'ap-southeast-1'
role_arn = 'arn:aws:iam::460453255610:role/ElasticSearchSnapshotLambdaRole'
repo_name = 'my-repo'

# Get region and credential
service = 'es'
session = boto3.session.Session()
credentials = session.get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, session.region_name, service,
                   session_token=credentials.token)


def lambda_handler(event, context):
    # register_a_repo(host_source)
    # register_a_repo(host_target)

    # take_a_snapshot()
    # snapshot_name = restore_latest_snapshot()

    list_indices(host_source, awsauth)
    list_indices(host_target, awsauth)

    return {
        'statusCode': 200
    }


def register_a_repo(host: str):
    # Register a repository
    register_repository(host, awsauth, repo_name, bucket_name, region, role_arn)

    # List all repositories
    list_all_repositories(host, awsauth)


def delete_a_repo():
    # Delete a repository
    delete_one_repository(host_source, awsauth, repo_name)


def take_a_snapshot():
    # Create a snapshot
    snapshot_name = take_snapshot(host_source, awsauth, repo_name)
    print(snapshot_name)

    # List all snapshots in all repository
    list_snapshots_in_repo(host_source, repo_name, awsauth)

    # Get snapshot in-progress
    get_snapshot_status(host_source, awsauth, repo_name=repo_name, snapshot_name=snapshot_name)

    return snapshot_name


def delete_latest_snapshot():
    latest_snapshot = get_latest_snapshot(host_target, repo_name, awsauth)
    if latest_snapshot:
        snapshot_name = latest_snapshot.get('snapshot')
        delete_one_snapshot(host_source, awsauth, repo_name, snapshot_name=snapshot_name)


def restore_latest_snapshot():
    latest_snapshot = get_latest_snapshot(host_target, repo_name, awsauth)
    if latest_snapshot:
        snapshot_name = latest_snapshot.get('snapshot')
        # Get indices of the snapshot
        snapshot = get_snapshot(host_target, awsauth, repo_name, snapshot_name)
        # Close all indices in the snapshot before restore
        for index in snapshot['indices']:
            close_index(host_target, awsauth, index)

        # Restore the snapshot
        restore_snapshot(host_target, awsauth, repo_name, snapshot_name)

        # Get snapshot in-progress
        get_snapshot_status(host_source, awsauth, repo_name=repo_name, snapshot_name=snapshot_name)

        return snapshot_name
