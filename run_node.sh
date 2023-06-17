#!/bin/bash

echo "Install: apt update"
apt update
echo "Install: python3"
apt install python3 -y
echo "Install: python3-flask"
apt install python3-flask -y
echo "Install: python3-pip"
apt install python3-pip -y
echo "Install: upgrade pip"
pip3 install --upgrade pip
echo "Install: awscli"
pip3 install awscli
echo "Install: boto3"
pip3 install boto3 
echo "Install: paramiko"
pip3 install paramiko
echo "Install: requests"
pip3 install requests
echo "Install: Done"

# Configure AWS CLI with access key ID and secret access key
aws configure set aws_access_key_id "{{AWS_ACCESS_KEY_ID}}"
aws configure set aws_secret_access_key "{{AWS_SECRET_ACCESS_KEY}}"
# Set the AWS default region (optional)
aws configure set default.region "{{AWS_REGION}}"

git clone --single-branch --branch EladBranch https://github.com/rotem-benzvi/Cloud_ex2.git

echo "made it"

# run app
cd Cloud_ex2/
FLASK_APP="app.py"
export FLASK_RUN_PORT=5000
export FLASK_RUN_HOST="0.0.0.0"
#nohup flask run --host=0.0.0.0 --port=5000 &>/dev/null &
nohup python3 app.py -name {{NAME}} -kind {{KIND}} &>/var/log/pythonlogs.txt &

echo "done"
exit