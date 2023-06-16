KEY_NAME="eladkey"
KEY_PEM="$KEY_NAME.pem"

echo "create key pair $KEY_PEM to connect to instances and save locally"
aws ec2 create-key-pair --key-name $KEY_NAME \
    | jq -r ".KeyMaterial" > $KEY_PEM


# secure the key pair
chmod 400 $KEY_PEM

SEC_GRP="my-sg-`date +'%N'`"

echo "setup firewall $SEC_GRP"
aws ec2 create-security-group   \
    --group-name $SEC_GRP       \
    --description "Access my instances" 

# figure out my ip
MY_IP=$(curl ipinfo.io/ip)
echo "My IP: $MY_IP"

echo "setup rule allowing SSH access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 22 --protocol tcp \
    --cidr $MY_IP/32

echo "setup rule allowing HTTP (port 5000) access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 5000 --protocol tcp \
    --cidr $MY_IP/32

UBUNTU_22_04_AMI="ami-00aa9d3df94c6c354"

# Get the AWS access key ID and secret access key from the AWS CLI configuration
AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)

# Get the AWS default region from the AWS CLI configuration
AWS_REGION=$(aws configure get region)

NAME="endpoint_node1"
KIND='EndpointNode'
sed -e "s/{{NAME}}/$NAME/" -e "s/{{KIND}}/$KIND/" -e 's|{{AWS_SECRET_ACCESS_KEY}}|'"$AWS_SECRET_ACCESS_KEY"'|' -e "s/{{AWS_ACCESS_KEY_ID}}/$AWS_ACCESS_KEY_ID/" -e "s/{{AWS_REGION}}/$AWS_REGION/" run_node.sh > run_node1.sh

echo "Creating Ubuntu 22.04 instance..."
RUN_INSTANCES=$(aws ec2 run-instances       \
    --image-id $UBUNTU_22_04_AMI            \
    --instance-type t2.micro                \
    --key-name $KEY_NAME                    \
    --security-groups $SEC_GRP              \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME},{Key=Type,Value=$KIND}]" \
    --user-data file://run_node1.sh)

INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
echo "Waiting for instance status..."
aws ec2 wait instance-status-ok --instance-ids $INSTANCE_ID


PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $PUBLIC_IP"

echo "setup production environment"
echo "ssh -i $KEY_PEM -o 'StrictHostKeyChecking=no' -o 'ConnectionAttempts=10' ubuntu@$PUBLIC_IP"

echo "test that it all worked"
curl  --retry-connrefused --retry 10 --retry-delay 60  http://$PUBLIC_IP:5000