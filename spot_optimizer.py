from datetime import datetime

import boto3

# Set the required parameters
desired_vcpu = 2
desired_ram = 16
desired_regions = ['us-west-2', 'eu-west-1', 'ap-southeast-1']  # List of desired regions

# Dictionary to store the best configuration for each region
best_instance_by_region = {}


# Get a list of instances that match the given requirements
def get_matched_instances(session,
                          vcpu_min=0,
                          ram_min=0,
                          vcpu_max=None,
                          ram_max=None,
                          arch_types=None,
                          virt_types=None):
    # List to store names of the instances that match the given requirements
    matched_instances = []
    # Form the body of the API request according to the specified parameters
    if arch_types is None:
        arch_types = ['i386', 'x86_64', 'arm64']
    if virt_types is None:
        virt_types = ['hvm', 'paravirtual']
    instance_requirements = {
        'VCpuCount': {
            'Min': vcpu_min
        },
        'MemoryMiB': {
            'Min': ram_min * 1000
        }
    }
    if vcpu_max is not None:
        instance_requirements['VCpuCount']['Max'] = vcpu_max
    if ram_max is not None:
        instance_requirements['MemoryMiB']['Max'] = ram_max * 1000
    instance_description = {
        'ArchitectureTypes': arch_types,
        'VirtualizationTypes': virt_types,
        'InstanceRequirements': instance_requirements
    }
    # Create API client for the provided session
    ec2_client = session.client('ec2')
    # Send API request and retrieve the list of the instances that match the given requirements
    #  with pagination, if required
    while 1:
        matched_instances_page = ec2_client.get_instance_types_from_instance_requirements(**instance_description)
        matched_instances.extend(d['InstanceType'] for d in matched_instances_page['InstanceTypes'])
        if 'NextToken' in matched_instances_page and matched_instances_page['NextToken'] != '':
            instance_description['NextToken'] = matched_instances_page['NextToken']
        else:
            break  # No next page, so the full list is retrieved
    return matched_instances


# Iterate over each region
for region in desired_regions:

    # Initialize the AWS session
    session = boto3.Session(profile_name='spot_optimizer', region_name=region)

    pagination_token = ''
    ec2_client = session.client('ec2')

    # Get information about Spot prices
    instances_prices = []
    while 1:
        spot_prices = ec2_client.describe_spot_price_history(
            StartTime=datetime.today(),
            InstanceTypes=get_matched_instances(session, vcpu_min=desired_vcpu, vcpu_max=desired_vcpu * 3,
                                                ram_min=desired_ram, ram_max=desired_ram * 3),
            # Get pricing only for some instance types
            ProductDescriptions=['Linux/UNIX'],  # Specify operating system
            NextToken=pagination_token  # Token to use pagination if it will be required
        )
        instances_prices.extend(spot_prices['SpotPriceHistory'])
        pagination_token = spot_prices['NextToken']
        if pagination_token == '':
            break

    # Find the best configuration in your current region
    best_price = None
    for price in instances_prices:
        if best_price is None or float(price['SpotPrice']) < float(best_price['SpotPrice']):
            best_price = price

    if best_price is not None:
        best_price['InstanceDescription'] = ec2_client.describe_instance_types(
            InstanceTypes=[best_price['InstanceType']]
        )
        best_instance_by_region[region] = best_price

# Output of the best configurations for each region
for region, instance_type in best_instance_by_region.items():
    print(f"Best instance type in region {region}: {instance_type}")
