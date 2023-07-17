import threading

import boto3

from spot_optimizer_functions import *


def thread_method(function, function_args, lock, results_list):
    function_result = function(**function_args)
    with lock:
        results_list.extend(function_result)


def thread_method_no_lock(function, function_args, results_list):
    function_result = function(**function_args)
    results_list.extend(function_result)


def get_pricelist_regional(profile_name='default',
                           region_name=None,
                           vcpu_min=None,
                           vcpu_max=None,
                           ram_min=None,
                           ram_max=None):
    # Calculate desired parameters if not set
    if vcpu_min is None:
        vcpu_min = 0
    if vcpu_max is None:
        vcpu_max = vcpu_min * 3
    if ram_min is None:
        ram_min = 0
    if ram_max is None:
        ram_max = ram_min * 3
    # Initialize regional lock
    lock_regional = threading.Lock()
    # Initialize the AWS session
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    # Get list of available instances in the region, that matched the provided requirements
    instances_list = get_matched_instances(session=session,
                                           vcpu_min=vcpu_min,
                                           vcpu_max=vcpu_max,
                                           ram_min=ram_min,
                                           ram_max=ram_max)
    # Initialize regional price list
    instances_prices_regional = []
    # Create a thread and get prices for the matched on-demand  instances
    thread_on_demand = threading.Thread(target=thread_method,
                                        args=(get_ec2_on_demand_prices, {'session': session,
                                                                         'region_code': region,
                                                                         'instance_types': instances_list},
                                              lock_regional,
                                              instances_prices_regional))
    thread_on_demand.start()
    # Create a thread and get prices for the matched spot instances
    thread_spot = threading.Thread(target=thread_method,
                                   args=(get_spot_prices, {'session': session,
                                                           'instances_types': instances_list},
                                         lock_regional,
                                         instances_prices_regional))
    thread_spot.start()
    # Initialise descriptions list
    instances_description = []
    # Create a thread and get descriptions for the matched instances
    thread_descriptions = threading.Thread(target=thread_method_no_lock,
                                           args=(get_instances_descriptions, {'session': session,
                                                                              'instance_types': instances_list},
                                                 instances_description))
    thread_descriptions.start()
    # Wait for the created threads finish
    thread_on_demand.join()
    thread_spot.join()
    thread_descriptions.join()
    # Add instances descriptions to the instances price-list
    pricelist_add_descriptions(instances_pricelist=instances_prices_regional,
                               instances_descriptions=instances_description,
                               region=region)

    return instances_prices_regional


if __name__ == "__main__":
    # Set the required parameters
    desired_vcpu = 2
    desired_ram = 16
    # List of desired regions
    desired_regions = ['us-west-2', 'eu-west-1', 'ap-southeast-1']
    # Global price list of the instances, which matches the requirements
    instances_prices = []
    # Iterate over each region
    for region in desired_regions:
        # Retrieve and add regional price list to the global list
        instances_prices.extend(get_pricelist_regional(profile_name='spot_optimizer',
                                                       region_name=region,
                                                       vcpu_min=desired_vcpu,
                                                       ram_min=desired_ram))

    # Sort instances by price
    sorted_prices_list = sorted(instances_prices, key=lambda x: x['Price'], reverse=False)

    # Print 5 cheapest instances that matched the provided requirements
    print("Top 5 cheapest instances that matched the provided requirements:")
    for instance_price in sorted_prices_list[:5]:
        print(
            f"Price: {instance_price['Price']}/{round(float(instance_price['Price']) * 24 * 30, 2)} "
            f"(-{instance_price['Discount']}%), Instance: {instance_price['InstanceType']}, "
            f"Type: {instance_price['Type']}, Region: {instance_price['Region']}, AZ: {instance_price['AZ']}, "
            f"Ram(GiB): {round(instance_price['Description']['MemoryInfo']['SizeInMiB'] / 1024, 3)}, "
            f"CPU: {instance_price['Description']['VCpuInfo']['DefaultVCpus']} x "
            f"{instance_price['Description']['ProcessorInfo']}")
