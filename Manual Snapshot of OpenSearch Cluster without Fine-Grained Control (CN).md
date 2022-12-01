# 手动快照没有精细访问控制的OpenSearch集群

本文演示了如何使用 Lambda 函数为没有启用精细访问控制的 OpenSearch 集群进行手动快照，然后使用快照将数据恢复到另一个域上。



### 1. 在VPC中创建OpenSearch域

1. 为 lambda 函数创建一个安全组，例如 <u>`secgroup-lambda-elasticsearch`</u>。

   * 无需添加入站规则；保留默认的出站规则。
   
2. 为 OpenSearch 域创建一个安全组，例如 <u>`secgroup-elasticsearch-default`</u>。

   * 添加一则入站规则：TCP，端口443，源来自安全组<u>`secgroup-lambda-elasticsearch`</u>。
   * 保留默认的出站规则。

3. 创建一个新的 OpenSeach 集群，例如 <u>`mydomain`</u>。 创建过程需要几分钟的时间。更改以下设置，保留其他设置为默认值。

   * 如果是<u>测试目的</u>，可以选择以下最少的资源以节省成本。

     * Development type = **Development and testing**.

     * **Auto-Tune** = Disable

     * Availbility Zones = **1-AZ** 

     * Instance Type = **t3.small.search**

     * Number of nodes = 1
   * 将网络设置为**VCP access**
     * 选择 VPC和子网，以及新创建的安全组 <u>`secgroup-elasticsearch-default`</u>
   * **不要**启用精细访问控制。
   * 对于访问策略（Access policy），选择 "<u>Configure domain level access policy</u>"
     * 以 JSON格式查看策略，将Effect从“Deny”改为“Allow”。
     * 忽略警告信息。
   
```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "AWS": "*"
         },
         "Action": "es:*",
         "Resource": "arn:aws:es:ap-southeast-1:460453255610:domain/mydomain/*"
       }
     ]
   }
```

### 2. 部署 Lambda 函数

1. 创建一个 S3 存储桶来存储 OpenSearch 快照。

2. 创建一个 IAM 策略 <u>`elasticsearch-snapshot-policy`</u>。这个策略将被附加到一个 IAM 角色，例如`ElasticSearchSnapshotLambdaRole`, 以便让lambda函数使用OpenSearch服务。

   * 相应地替换 ACCOUNT_ID、IAM_ROLE_NAME、BUCKET_NAME。
   * 桶名BUKET_NAME可以用*符来匹配多个S3桶。

   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Sid": "VisualEditor0",
               "Effect": "Allow",
               "Action": [
                   "iam:PassRole"
               ],
               "Resource": [
                   "arn:aws:iam::ACCOUNT_ID:role/IAM_ROLE_NAME"
               ]
           },
           {
               "Sid": "VisualEditor1",
               "Effect": "Allow",
               "Action": [
                   "s3:ListBucket"
               ],
               "Resource": [
                   "arn:aws:s3:::BUCKET_NAME_*"
               ]
           },
           {
               "Sid": "VisualEditor2",
               "Effect": "Allow",
               "Action": [
                   "s3:PutObject",
                   "s3:GetObject",
                   "s3:DeleteObject"
               ],
               "Resource": [
                 "arn:aws:s3:::BUCKET_NAME_*/*"
               ]
           },
           {
               "Sid": "VisualEditor3",
               "Effect": "Allow",
               "Action": [
                   "es:ESHttpPut",
                   "es:ESHttpGet",
                   "es:ESHttpPost",
                 	"es:ESHttpDelete"
               ],
               "Resource": [
                   "arn:aws:es:REGION:ACCOUNT_ID:domain/*"
               ]
           }
       ]
   }
   ```

3. 创建具有以下信任关系的 IAM 角色<u>`ElasticSearchSnapshotLambdaRole`</u>。

   * 将新建的策略<u>`elasticsearch-snapshot-policy`</u>和 AWS托管策略<u>`AWSLambdaVPCAccessExecutionRole`</u>添加到到角色。

   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Principal": {
                   "Service": [
                       "lambda.amazonaws.com",
                       "ssm.amazonaws.com",
                       "es.amazonaws.com"
                   ]
               },
               "Action": "sts:AssumeRole"
           }
       ]
   }
   ```

   <img src="./Manual%20Snapshot%20of%20OpenSearch%20Cluster%20without%20Fine-Grained%20Control%20(CN).assets/image-20221129161838479.png" alt="image-20221129161838479" style="zoom:80%;" />

4. 创建一个 Lambda 函数，例如<u>`SnapshotElasticSearch`</u>。

   * Choose Python 3.9+ as Runtime.
   * Choose same VPC, Subnet as the OpenSearch domain. 
   * Use the Security Group `secgroup-lambda-elasticsearch` which is created in section 1. 
   * Use the newly created IAM role `ElasticSearchSnapshotLambdaRole`. 

5. 上传以下Python脚本。

   * lambda_function.py
   * opensearch_utils.py

6. 修改 `main.py` 文档内的 <DOMAIN_ENDPOINT_WITH_HTTPS>、<BUCKET_NAME>、<AWS_REGION>、<ARN_OF_IAM_ROLE_LAMBDA> 和 <REPOSITORY_NAME>。

   * 你可以添加多个源域。每个源域可以有自定义的REPOSITORY_NAME，以及自己的S3桶。

   ```python
   # Settings
   host_sources = [('<DOMAIN_ENDPOINT_WITH_HTTPS>','<REPOSITORY_NAME>','<S3_BUCKET_NAME>')]  # 源头域终端节点
   host_targets = [('<DOMAIN_ENDPOINT_WITH_HTTPS>','<REPOSITORY_NAME>','<S3_BUCKET_NAME>')]   # 目标域终端节点
   region = '<AWS_REGION>'  # S3桶的区域
   role_arn = '<ARN_OF_IAM_ROLE_LAMBDA>'  # Lambda函数的角色ARN
   ```

7. 这个函数需要用到以下的库。建一个包含以下库的压缩包。用这个压缩包建一个函数层，比如`requests_aws4auth`.

   * 可以使用这个脚本建函数层的包。https://github.com/qinjie/aws-create-lambda-layer

   ```ini
   requests==2.28.1
   requests_aws4auth==1.1.2
   ```

8. 添加函数层。

   <img src="./Manual%20Snapshot%20of%20OpenSearch%20Cluster%20without%20Fine-Grained%20Control%20(CN).assets/image-20221129162416745.png" alt="image-20221129162416745" style="zoom: 67%;" />

9. 将函数的超时延长至30秒。

   <img src="./Manual%20Snapshot%20of%20OpenSearch%20Cluster%20without%20Fine-Grained%20Control%20(CN).assets/image-20221129163412821.png" alt="image-20221129163412821" style="zoom:80%;" />

10. 点击Deploy，然后再点Test。

   * 给事件一个名字，不需要修改事件JSON和其他设置。

   <img src="./Manual%20Snapshot%20of%20OpenSearch%20Cluster%20without%20Fine-Grained%20Control%20(CN).assets/image-20221129163234278.png" alt="image-20221129163234278" style="zoom:80%;" />




### 3. 测试 Lambda 函数

我们先运行 lambda 函数来在源域和目标域上注册快照存储库，然后修改函数进行拍摄快照，再修改函数复原快照。

1. 修改 `lambda_handler()` 函数并部署。

   ```python
   def lambda_handler(event, context):
       # Registeration repo for source domains 源域
       for host, repo, bucket in host_sources:
           register_a_repo(host, repo, bucket)
       # Register repo for target domains 目标域
       for host, repo, bucket in host_targets:
           register_a_repo(host, repo, bucket)
   
       # # Take snapshot of source domains 源域
       # for host, repo, _ in host_sources:
       #     take_a_snapshot(host, repo)
       #
       # # Restore last snapshot to target domains
       # for host, repo, _ in host_sources:
       #     snapshot_name = restore_latest_snapshot(host, repo)
       #
       # # List indices in source domains
       # for host, _, _ in host_sources:
       #     list_indices(host, awsauth)
       # # List indices in target domain
       # for host, _, _ in host_sources:
       #     list_indices(host, awsauth)
   
       return {
           'statusCode': 200
       }
   ```

2. 运行 lambda 以注册快照存储库。确保执行输出中没有错误/警告。

   ![image-20221130163038031](./Manual%20Snapshot%20of%20OpenSearch%20Cluster%20without%20Fine-Grained%20Control%20(CN).assets/image-20221130163038031.png)

3. 修改 `lambda_handler()` 函数并部署。

   ```python
   def lambda_handler(event, context):
       # # Registeration repo for source domains 源域
       # for host, repo, bucket in host_sources:
       #     register_a_repo(host, repo, bucket)
       # # Register repo for target domains 目标域
       # for host, repo, bucket in host_targets:
       #     register_a_repo(host, repo, bucket)
   
       # Take snapshot of source domains 源域
       for host, repo, _ in host_sources:
           take_a_snapshot(host, repo)
   
       # # Restore last snapshot to target domains
       # for host, repo, _ in host_sources:
       #     snapshot_name = restore_latest_snapshot(host, repo)
       #
       # # List indices in source domains
       # for host, _, _ in host_sources:
       #     list_indices(host, awsauth)
       # # List indices in target domain
       # for host, _, _ in host_sources:
       #     list_indices(host, awsauth)
   
       return {
           'statusCode': 200
       }
   ```

4. 运行 lambda 函数对源域进行快照。确保输出中没有错误/警告消息。

   ![image-20221130163253077](./Manual%20Snapshot%20of%20OpenSearch%20Cluster%20without%20Fine-Grained%20Control%20(CN).assets/image-20221130163253077.png)

5. 检查 S3 存储桶中生成的文件。

6. 修改 `lambda_handler()` 函数并部署。

   ```python
   def lambda_handler(event, context):
       # # Registeration repo for source domains 源域
       # for host, repo, bucket in host_sources:
       #     register_a_repo(host, repo, bucket)
       # # Register repo for target domains 目标域
       # for host, repo, bucket in host_targets:
       #     register_a_repo(host, repo, bucket)
   
       # # Take snapshot of source domains 源域
       # for host, repo, _ in host_sources:
       #     take_a_snapshot(host, repo)
   
       # Restore last snapshot to target domains
       for host, repo, _ in host_sources:
           snapshot_name = restore_latest_snapshot(host, repo)
   
       # # List indices in source domains
       # for host, _, _ in host_sources:
       #     list_indices(host, awsauth)
       # # List indices in target domain
       # for host, _, _ in host_sources:
       #     list_indices(host, awsauth)
   
       return {
           'statusCode': 200
       }
   ```

7. 运行 lambda 函数将最新的快照复原到目标域上。确保输出中没有错误/警告消息。

   ![image-20221130163457347](./Manual%20Snapshot%20of%20OpenSearch%20Cluster%20without%20Fine-Grained%20Control%20(CN).assets/image-20221130163457347.png)

8. 修改 `lambda_handler()` 函数并部署。

   ```python
   def lambda_handler(event, context):
       # # Registeration repo for source domains 源域
       # for host, repo, bucket in host_sources:
       #     register_a_repo(host, repo, bucket)
       # # Register repo for target domains 目标域
       # for host, repo, bucket in host_targets:
       #     register_a_repo(host, repo, bucket)
   
       # # Take snapshot of source domains 源域
       # for host, repo, _ in host_sources:
       #     take_a_snapshot(host, repo)
   
       # # Restore last snapshot to target domains
       # for host, repo, _ in host_sources:
       #     snapshot_name = restore_latest_snapshot(host, repo)
   
       # List indices in source domains
       for host, _, _ in host_sources:
           list_indices(host, awsauth)
       # List indices in target domain
       for host, _, _ in host_sources:
           list_indices(host, awsauth)
   
       return {
           'statusCode': 200
       }
   ```

9. 稍等一会儿。运行 lambda 函数查看源域和目标域的Index。确保输出中没有错误/警告消息。比较它们列出的Index和Document数目。

   ![image-20221130164554723](./Manual%20Snapshot%20of%20OpenSearch%20Cluster%20without%20Fine-Grained%20Control%20(CN).assets/image-20221130164554723.png)

10. 可以在源域上添加或者删除document。重复以上的步骤，查看目标域上的文档是否回复。



### 4. 添加 EventBridge 触发器

我们使用 EventBridge 设置每日计划来运行 Lambda 函数。

1. 打开 Lambda 函数，来到 配置 > 触发器 > 添加触发器。
2. 选择 **EventBridge (CloudWatch Events)**
   * 创建新规则
   * 选择规则类型 = 计划表达式
   * 将表达式设置为 cron 表达式，例如 半夜（+8时区）: cron(0 16 * * ? *）




### Reference

* https://docs.aws.amazon.com/opensearch-service/latest/developerguide/vpc.html#vpc-security

