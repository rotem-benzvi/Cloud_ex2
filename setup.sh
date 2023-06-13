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

NAME="endpoint_node1"
KIND='EndpointNode'
ENDPOINT1=$(sed -e "s/{{NAME}}/$NAME/" -e "s/{{KIND}}/$KIND/" run_node.sh)

echo "Creating Ubuntu 22.04 instance..."
RUN_INSTANCES=$(aws ec2 run-instances       \
    --image-id $UBUNTU_22_04_AMI            \
    --instance-type t2.micro                \
    --key-name $KEY_NAME                    \
    --security-groups $SEC_GRP              \
    --user-data $ENDPOINT1)

INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
aws ec2 wait instance-status-ok --instance-ids $INSTANCE_ID


PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $PUBLIC_IP"

echo "setup production environment"
echo "ssh -i $KEY_PEM -o 'StrictHostKeyChecking=no' -o 'ConnectionAttempts=10' ubuntu@$PUBLIC_IP"
# ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP <<EOF
#     sudo apt update
#     sudo apt install python3-flask -y
#     sudo apt install python3-pip -y
#     sudo pip3 install --upgrade pip
#     sudo pip3 install awscli
#     pip3 install boto3 
#     pip3 install paramiko

#     # Configure AWS CLI with access key ID and secret access key
#     aws configure set aws_access_key_id "KEY_ID"
#     aws configure set aws_secret_access_key "KEY"
#     # Set the AWS default region (optional)
#     aws configure set default.region "eu-west-1"

#     git clone https://github.com/rotem-benzvi/Cloud_ex2.git

#     # run app
#     cd Cloud_ex2/
#     FLASK_APP="app.py"
#     nohup flask run --host=0.0.0.0 --port=5000 &>/dev/null &
#     exit
# EOF

echo "test that it all worked"
curl  --retry-connrefused --retry 10 --retry-delay 60  http://$PUBLIC_IP:5000