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


def get_instances_descriptions(session,
                               instance_types):
    # List to store instances description
    instances_description = []
    # Create API client for the provided session
    ec2_client = session.client('ec2')
    # Form the body of the API request according to the specified parameters
    filter = {
        'InstanceTypes': instance_types
    }
    # Send API request and retrieve the list of instances description for instances that match the given instance types
    #  with pagination, if required
    while 1:
        instances_description_page = ec2_client.describe_instance_types(**filter)
        instances_description.extend(instances_description_page['InstanceTypes'])
        if 'NextToken' in instances_description_page and instances_description_page['NextToken'] != '':
            filter['NextToken'] = instances_description_page['NextToken']
        else:
            break  # No next page, so the full list is retrieved
    return instances_description


def get_spot_prices(session,
                    history_start_time=None,
                    history_end_time=None,
                    instances_types=None,
                    instances_description=None):
    # Form the body of the API request according to the specified parameters
    if history_start_time is None:
        history_start_time = datetime.today()
    filter = {
        'StartTime': history_start_time
    }
    if history_end_time is not None:
        filter['EndTime'] = history_end_time
    if instances_types is not None:
        filter['InstanceTypes'] = instances_types
    if instances_description is not None:
        filter['ProductDescriptions'] = instances_description
    else:
        filter['ProductDescriptions'] = ['Linux/UNIX']
    # Create spot prices empty list
    spot_prices = []
    # Create API client for the provided session
    ec2_client = session.client('ec2')
    # Send API request and retrieve the list of the instances that match the given requirements
    #  with pagination, if required
    while 1:
        spot_prices_page = ec2_client.describe_spot_price_history(**filter)
        spot_prices.extend(spot_prices_page['SpotPriceHistory'])
        if 'NextToken' in spot_prices_page and spot_prices_page['NextToken'] != '':
            filter['NextToken'] = spot_prices_page['NextToken']
        else:
            break  # No next page, so the full list is retrieved

    return spot_prices


# Iterate over each region
for region in desired_regions:

    # Initialize the AWS session
    session = boto3.Session(profile_name='spot_optimizer', region_name=region)

    # Get spot prices for instances, which match the requirements
    instances_spot_prices = get_spot_prices(session=session,
                                            instances_types=get_matched_instances(session=session,
                                                                                  vcpu_min=desired_vcpu,
                                                                                  vcpu_max=desired_vcpu * 3,
                                                                                  ram_min=desired_ram,
                                                                                  ram_max=desired_ram * 3))
    # Find the best configuration in your current region
    best_price = None
    for price in instances_spot_prices:
        if best_price is None or float(price['SpotPrice']) < float(best_price['SpotPrice']):
            best_price = price

    if best_price is not None:
        best_price['InstanceDescription'] = get_instances_descriptions(session=session,
                                                                       instance_types=[best_price['InstanceType']])
        best_instance_by_region[region] = best_price

# Output of the best configurations for each region
for region, instance_type in best_instance_by_region.items():
    print(f"Best instance type in region {region}: {instance_type}")
