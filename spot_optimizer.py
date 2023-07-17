import time

from spot_optimizer_functions import *

if __name__ == "__main__":
    # Set the required parameters
    desired_vcpu = 2
    desired_ram = 16
    # List of desired regions
    desired_regions = ['us-west-2', 'eu-west-1', 'ap-southeast-1']
    # Global price list of the instances, which matches the requirements
    instances_prices = []
    # Initialize thread lock
    lock = threading.Lock()
    # Create and run a separate thread for each region
    threads = []
    for region in desired_regions:
        time.sleep(0.100)
        thread = threading.Thread(target=thread_method, args=(get_pricelist_regional,
                                                              {'profile_name': 'spot_optimizer',
                                                               'region_name': region,
                                                               'vcpu_min': desired_vcpu,
                                                               'ram_min': desired_ram},
                                                              lock,
                                                              instances_prices))
        thread.start()
        threads.append(thread)
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
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
