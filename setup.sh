#install all requrments

# Install Python 3
apt-get update
apt-get install -y python3

# Install pip3
apt-get install -y python3-pip

# Install boto3 library
pip3 install boto3


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


KIND='EndpointNode'

# create node 1
NAME="endpoint_node_1"

echo "Creating $KIND with parameters: -name $NAME -name $NAME -kind $KIND -key_name $KEY_NAME -security_group $SEC_GRP"
NODE1_OUTPUT=$(python3 create_node.py -name $NAME -kind $KIND -key_name $KEY_NAME -security_group $SEC_GRP)

IFS=',' read -r NODE1_PUBLIC_IP NODE1_INSTANCE_ID <<< "$NODE1_OUTPUT"

echo "New instance $KIND ($NAME) : $NODE1_INSTANCE_ID @ $NODE1_PUBLIC_IP"

echo "to connect to node 1:"
echo "ssh -i $KEY_PEM -o 'StrictHostKeyChecking=no' -o 'ConnectionAttempts=10' ubuntu@$NODE1_PUBLIC_IP"

# create node 2 
NAME="endpoint_node_2"

echo "Creating $KIND with parameters: -name $NAME -name $NAME -kind $KIND -key_name $KEY_NAME -security_group $SEC_GRP"
NODE2_OUTPUT=$(python3 create_node.py -name $NAME -kind $KIND -key_name $KEY_NAME -security_group $SEC_GRP)

IFS=',' read -r NODE2_PUBLIC_IP NODE2_INSTANCE_ID <<< "$NODE2_OUTPUT"

echo "New instance $KIND ($NAME) : $NODE2_INSTANCE_ID @ $NODE2_PUBLIC_IP"

echo "to connect to node 2:"
echo "ssh -i $KEY_PEM -o 'StrictHostKeyChecking=no' -o 'ConnectionAttempts=10' ubuntu@$NODE2_PUBLIC_IP"

#test connectivity
echo "test that it all worked for node 1, node status: "
curl  --retry-connrefused --retry 10 --retry-delay 60  http://$NODE1_PUBLIC_IP:5000/getStatus

echo "test that it all worked for node 2, node status: "
curl  --retry-connrefused --retry 10 --retry-delay 60  http://$NODE2_PUBLIC_IP:5000/getStatus

#set each node is other node's neighbor IP 
echo "Set node 1($NODE1_PUBLIC_IP), node 2 ip($NODE2_PUBLIC_IP)"
curl -X POST "http://$NODE1_PUBLIC_IP:5000/setOtherNodeIp?ip=$NODE2_PUBLIC_IP"

echo "Set node 2($NODE2_PUBLIC_IP), node 1 ip($NODE1_PUBLIC_IP)"
curl -X POST "http://$NODE2_PUBLIC_IP:5000/setOtherNodeIp?ip=$NODE1_PUBLIC_IP"

#Check that we set IP correctly
echo "test that it all worked for node 1, node status: "
curl  --retry-connrefused --retry 10 --retry-delay 60  http://$NODE1_PUBLIC_IP:5000/getStatus

echo "test that it all worked for node 2, node status: "
curl  --retry-connrefused --retry 10 --retry-delay 60  http://$NODE2_PUBLIC_IP:5000/getStatus

echo "Done"