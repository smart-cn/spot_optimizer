from datetime import datetime

import boto3

# Configure desired parameters of the instance
# Set the required parameters
desired_vcpu = 2
desired_ram = 16
# List of desired regions
desired_regions = ['us-west-2', 'eu-west-1', 'ap-southeast-1']


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


def get_aws_products(session,
                     service_code,
                     filters):
    # Create empty products list
    products_list = []
    # Crate pricing client for the session using provided endpoint
    pricing_client = session.client('pricing', region_name='us-east-1')
    # Send API request and retrieve the list of products with prices by Service code
    pagination_token = ''
    while 1:
        if pagination_token == '':
            products_list_page = pricing_client.get_products(ServiceCode=service_code,
                                                             Filters=filters)
        else:
            products_list_page = pricing_client.get_products(ServiceCode=service_code,
                                                             Filters=filters,
                                                             NextToken=pagination_token)
        products_list.extend(products_list_page['PriceList'])
        if 'NextToken' in products_list_page and products_list_page['NextToken'] != '':
            pagination_token = products_list_page['NextToken']
        else:
            break  # No next page, so the full list is retrieved
    # Convert retrieved list from json format to python objects
    price_list = []
    for product in products_list:
        price_list.append(json.loads(product))

    return price_list


def get_region_name(region_code):
    endpoint_file = resource_filename('botocore', 'data/endpoints.json')
    with open(endpoint_file, 'r') as f:
        endpoint_data = json.load(f)
    e_data = endpoint_data
    region_name = e_data['partitions'][0]['regions'][region_code]['description']
    region_name = region_name.replace('Europe', 'EU')

    return region_name


def get_ec2_on_demand_prices(session,
                             region_code,
                             instance_types=None,
                             operating_system='Linux',
                             preinstalled_software='NA',
                             tenancy='Shared',
                             is_byol=False):
    filters = [{'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_region_name(region_code)},
               {'Type': 'TERM_MATCH', 'Field': 'termType', 'Value': 'OnDemand'},
               {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': tenancy},
               {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': operating_system},
               {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': preinstalled_software}]
    if is_byol:
        filters.append({'Type': 'TERM_MATCH', 'Field': 'licenseModel', 'Value': 'Bring your own license'})
    else:
        filters.append({'Type': 'TERM_MATCH', 'Field': 'licenseModel', 'Value': 'No License required'})
    if tenancy == 'Host':
        filters.append({'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'AllocatedHost'})
    else:
        filters.append({'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'})
    price_list = []
    if instance_types is None:
        price_list = get_aws_products(session=session, service_code='AmazonEC2', filters=filters)
    else:
        if type(instance_types) is str:
            filters_single_instance = filters
            filters_single_instance.append({'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_types})
            price_list.extend(get_aws_products(session=session,
                                               service_code='AmazonEC2',
                                               filters=filters_single_instance))
        else:
            for instance_type in instance_types:
                filters_single_instance = list(filters).copy()
                filters_single_instance.append({'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type})
                price_list.extend(get_aws_products(session=session,
                                                   service_code='AmazonEC2',
                                                   filters=filters_single_instance))
    instance_prices = []
    for price in price_list:
        instance_price = {}
        instance_price['instance_type'] = price['product']['attributes']['instanceType']
        instance_price['price'] = \
            list(list(price['terms']['OnDemand'].values())[0]['priceDimensions'].values())[0]['pricePerUnit']['USD']
        instance_price['raw'] = price
        instance_prices.append(instance_price)

    return instance_prices


# Dictionary to store the best configuration for each region
best_instance_by_region = {}
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
