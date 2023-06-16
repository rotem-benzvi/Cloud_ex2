import boto3
import json
import argparse
import os
import sys

def create_instance(key_name, security_group, node_name, node_kind):
    UBUNTU_22_04_AMI = "ami-00aa9d3df94c6c354"

    # Get the AWS access key ID and secret access key from the AWS CLI configuration
    aws_secret_access_key = boto3.Session().get_credentials().secret_key
    aws_access_key_id = boto3.Session().get_credentials().access_key

    # Get the AWS default region from the AWS CLI configuration
    aws_region = boto3.Session().region_name

    # Replace placeholders in the run_node.sh script and save it to run_node1.sh
    with open("run_node.sh", "r") as f:
        script_content = f.read()
        script_content = script_content.replace("{{NAME}}", node_name)
        script_content = script_content.replace("{{KIND}}", node_kind)
        script_content = script_content.replace("{{AWS_SECRET_ACCESS_KEY}}", aws_secret_access_key)
        script_content = script_content.replace("{{AWS_ACCESS_KEY_ID}}", aws_access_key_id)
        script_content = script_content.replace("{{AWS_REGION}}", aws_region)

    #print(script_content)
    # with open("run_node1.sh", "w") as f:
    #     f.write(script_content)

    instance_initiated_shutdown_behavior = "stop"
    if(node_kind == "WorkerNode"):
        instance_initiated_shutdown_behavior = "terminate"

    print("create_instance: instance_initiated_shutdown_behavior = " + instance_initiated_shutdown_behavior)

    print("Creating Ubuntu 22.04 instance...")
    ec2_client = boto3.client("ec2", region_name=aws_region)

    run_instances_response = ec2_client.run_instances(
        ImageId=UBUNTU_22_04_AMI,
        InstanceType="t2.micro",
        MinCount=1,
        MaxCount=1,
        KeyName=key_name,
        InstanceInitiatedShutdownBehavior=instance_initiated_shutdown_behavior,
        SecurityGroups=[security_group],
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": node_name},
                    {"Key": "Type", "Value": node_kind}
                ]
            }
        ],
        UserData=script_content
    )

    instance_id = run_instances_response["Instances"][0]["InstanceId"]

    print("create_instance: Waiting for instance creation...")
    ec2_client.get_waiter("instance_running").wait(InstanceIds=[instance_id])

    print("create_instance: Waiting for instance status...")
    ec2_client.get_waiter("instance_status_ok").wait(InstanceIds=[instance_id])

    describe_instances_response = ec2_client.describe_instances(InstanceIds=[instance_id])
    public_ip = describe_instances_response["Reservations"][0]["Instances"][0]["PublicIpAddress"]

    return public_ip, instance_id

# Example usage

if __name__ == '__main__':
    # Disable print statements
    sys.stdout = open(os.devnull, 'w')

    parser = argparse.ArgumentParser()
    parser.add_argument('-kind', help='Specify the kind')
    parser.add_argument('-name', help='Specify the name')
    parser.add_argument('-key_name', help='Specify the key name')
    parser.add_argument('-security_group', help='Specify the security group name')
    args = parser.parse_args()

    # Access the value of the 'kind' argument
    key_name = args.key_name
    security_group = args.security_group
    node_name = args.name   
    node_kind = args.kind

    public_ip, instance_id = create_instance(key_name, security_group, node_name, node_kind)

    # Enable print statements
    sys.stdout = sys.__stdout__  # Restore the standard output
    print(public_ip +","+ instance_id)

