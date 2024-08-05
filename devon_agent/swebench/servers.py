import boto3
import time


LAUNCH_TEMPLATE_ID = "lt-043cba034fa204660"
LAUNCH_TEMPLATE_VERSION = "2"

# Initialize a session using Amazon EC2
session = boto3.Session()

# Initialize the EC2 client
ec2_client = session.client('ec2')

# Launch an EC2 instance using a launch template
def launch_instance_from_template(launch_template_id, launch_template_version, instances):
    try:
        response = ec2_client.run_instances(
            LaunchTemplate={
                'LaunchTemplateId': launch_template_id,
                'Version': launch_template_version
            },
            MaxCount=instances,
            MinCount=instances
        )
        instance_ids = [instance['InstanceId'] for instance in response['Instances']]
        print("Successfully launched EC2 instance with ID:", instance_ids)
        return instance_ids
    except Exception as e:
        print("Error launching instance:", e)
        return None

# Get the public IP address of the launched instance
def get_instance_public_ip(instance_id):
    try:
        # Wait for the instance to be in the running state 
        ec2_client.get_waiter('instance_running').wait(InstanceIds=[instance_id])

        # wait for instance to pass status checks
        # ec2_client.get_waiter('instance_status_ok').wait(InstanceIds=[instance_id])

        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        print("Public IP address of the instance:", public_ip)
        return public_ip
    except Exception as e:
        print("Error getting public IP address:", e)
        return None


def spin_up(number_of_instances):
    instance_ids = launch_instance_from_template(LAUNCH_TEMPLATE_ID, LAUNCH_TEMPLATE_VERSION, number_of_instances)
    if instance_ids:
        # Allow some time for the instance to be assigned a public IP address
        time.sleep(20)  # Adjust this as necessary
        return instance_ids,[get_instance_public_ip(instance_id) for instance_id in instance_ids]
    return [],[]

def spin_down(instance_ids):
    ec2_client.terminate_instances(InstanceIds=instance_ids)
    print("Successfully terminated EC2 instance with ID:", instance_ids)


if __name__ == "__main__":
    ids,ips = spin_up(1)
    print(ips)
    spin_down(ids)