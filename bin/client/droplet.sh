#!/bin/sh
name=$1
flags=

[ -n "$name" ] || { echo NAME is required; exit 1; }

echo
echo SSH Keys:
doctl compute ssh-key ls --no-header
read -p "Choose an SSH Key: " sshkey
[ -z "$sshkey" ] || flags="--ssh-keys $sshkey"
echo

doctl compute image ls -o json | \
    jq -r '.[]|select(.type=="custom")|(.id|tostring)+" "+.name+"\t"+(.regions|tostring)'
echo 129211873 ubuntu-22-04-x64
image=
while [ -z "$image" ]
do
    read -p "Choose an image: " image
done
echo

size=s-2vcpu-4gb
echo Sizes:
cat <<EOF
s-1vcpu-1gb
s-3vcpu-1gb
s-2vcpu-4gb
s-4vcpu-8gb
s-8vcpu-16gb
s-2vcpu-2gb
EOF
while [ -z "$_size" ]
do
    read -p "Choose a Size ($size): " _size
    [ -z "$_size" ] || size=$_size
done

region=
if [ -z "$region" ]
then
    region=sfo2
    echo
    echo Regions:
    doctl compute region ls --no-header
    read -p "Choose a Region ($region): " _region
    [ -z "$_region" ] || region=$_region
fi

echo
set -x
doctl compute droplet create \
    $flags \
    --region $region \
    --image $image \
    --size $size \
    --no-header \
    $name
