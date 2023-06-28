import boto3
from datetime import datetime
from datetime import timedelta

# Set the required parameters
desired_vcpu = 2
desired_ram = 16
desired_regions = ['us-west-2', 'eu-west-1', 'ap-southeast-1']  # List of desired regions

# Dictionary to store the best configuration for each region
best_instance_by_region = {}

# Iterate over each region
for region in desired_regions:
    pagination_token = ''

    # Initialize the AWS Client
    session = boto3.Session(profile_name='spot_optimizer', region_name=region)
    ec2_client = session.client('ec2')

    # Get a list of instances that match the given requirements
    matched_instances = []
    while 1:
        if pagination_token == '':
            matched_instances_page = ec2_client.get_instance_types_from_instance_requirements(
                ArchitectureTypes=['i386', 'x86_64', 'arm64'],
                VirtualizationTypes=['hvm', 'paravirtual'],
                InstanceRequirements={
                    'VCpuCount': {
                        'Min': desired_vcpu,
                        'Max': desired_vcpu * 3
                    },
                    'MemoryMiB': {
                        'Min': desired_ram * 1000,
                        'Max': desired_ram * 1000 * 3
                    }
                }
            )
        else:
            matched_instances_page = ec2_client.get_instance_types_from_instance_requirements(
                ArchitectureTypes=['i386', 'x86_64', 'arm64'],
                VirtualizationTypes=['hvm', 'paravirtual'],
                InstanceRequirements={
                    'VCpuCount': {
                        'Min': desired_vcpu,
                        'Max': desired_vcpu * 3
                    },
                    'MemoryMiB': {
                        'Min': desired_ram * 1000,
                        'Max': desired_ram * 1000 * 3
                    }
                },
                NextToken=pagination_token # Token to use pagination if it will be required
            )
        matched_instances.extend(d['InstanceType'] for d in matched_instances_page['InstanceTypes'])
        if 'NextToken' in matched_instances_page:
            pagination_token = matched_instances_page['NextToken']
        else:
            pagination_token = ''
            break

    # Get information about Spot prices
    instances_prices = []
    while 1:
        spot_prices = ec2_client.describe_spot_price_history(
            StartTime=datetime.today() - timedelta(days=1),
            EndTime=datetime.today(),
            InstanceTypes=matched_instances,  # Get pricing only for some instance types
            ProductDescriptions=['Linux/UNIX'],  # Specify operating system
            NextToken=pagination_token  # Token to use pagination if it will be required
        )
        instances_prices.extend(spot_prices['SpotPriceHistory'])
        pagination_token = spot_prices['NextToken']
        if pagination_token == '':
            break

    # Find the best configuration in your current region
    best_price = None
    best_instance_type = None
    for price in instances_prices:
        instance_type = price['InstanceType']
        if best_price is None or float(price['SpotPrice']) < best_price:
            best_price = float(price['SpotPrice'])
            best_instance_type = instance_type

    if best_instance_type is not None:
        best_instance_by_region[region] = best_instance_type

# Output of the best configurations for each region
for region, instance_type in best_instance_by_region.items():
    print(f"Best instance type in region {region}: {instance_type}")
