import boto3
import subprocess
import json

# Set the required parameters
desired_vcpu = 2
desired_ram = 4
desired_regions = ['us-west-2', 'eu-west-1', 'ap-southeast-1']  # List of desired regions

# Initialize the AWS Client
ec2_client = boto3.client('ec2')

# Dictionary to store the best configuration for each region
best_instance_by_region = {}

# Iterate over each region
for region in desired_regions:
    # Get information about Spot prices
    response = ec2_client.describe_spot_price_history(
        InstanceTypes=['*'],  # Get pricing for all available instance types
        ProductDescriptions=['Linux/UNIX'],  # Specify operating system
        MaxResults=1000,  # Increase the maximum number of results if necessary
        AvailabilityZone=region + 'a'  # Select an Availability Zone in a Region
    )

    # Find the best configuration in your current region
    best_price = None
    best_instance_type = None
    for price in response['SpotPriceHistory']:
        instance_type = price['InstanceType']
        vcpu = int(price['CpuCoreCount'])
        ram = float(price['Memory'])
        if vcpu >= desired_vcpu and ram >= desired_ram:
            if best_price is None or float(price['SpotPrice']) < best_price:
                best_price = float(price['SpotPrice'])
                best_instance_type = instance_type

    if best_instance_type is not None:
        best_instance_by_region[region] = best_instance_type

# Output of the best configurations for each region
for region, instance_type in best_instance_by_region.items():
    print(f"Best instance type in region {region}: {instance_type}")

# Create a Terraform file using the best configurations
tf_config = {
    'variable': {
        'aws_region': {
            'default': desired_regions[0]  # Use the first default region
        },
        'instance_type': {
            'default': best_instance_by_region[desired_regions[0]]  # Use the first best default configuration
        }
    },
    'provider': {
        'aws': {
            'region': '${var.aws_region}'
        }
    },
    'resource': {
        'aws_instance': {
            'example': {
                'instance_type': '${var.instance_type}',
                # Add other required settings
            }
        }
    }
}

with open('spot_instance.tf.json', 'w') as tf_file:
    tf_file.write(json.dumps(tf_config, indent=4))

# Start Terraform
subprocess.run(['terraform', 'init'])
subprocess.run(['terraform', 'apply'])
