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


if __name__ == "__main__":
    # Configure desired parameters of the instance
    # Set the required parameters
    desired_vcpu = 2
    desired_ram = 16
    # List of desired regions
    desired_regions = ['us-west-2', 'eu-west-1', 'ap-southeast-1']
    # Global price list of the instances, which matches the requirements
    instances_prices = []
    # Iterate over each region
    for region in desired_regions:
        # Initialize regional lock
        lock_regional = threading.Lock()

        # Initialize the AWS session
        session = boto3.Session(profile_name='spot_optimizer', region_name=region)

        # Get list of available instances in the region, that matched the provided requirements
        instances_list = get_matched_instances(session=session,
                                               vcpu_min=desired_vcpu,
                                               vcpu_max=desired_vcpu * 3,
                                               ram_min=desired_ram,
                                               ram_max=desired_ram * 3)

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

        # Add regional price list to the global list
        instances_prices.extend(instances_prices_regional)

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
