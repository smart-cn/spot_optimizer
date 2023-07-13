import boto3

from spot_optimizer_functions import *

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
        # Initialize the AWS session
        session = boto3.Session(profile_name='spot_optimizer', region_name=region)
        # Get list of available instances in the region, that matched the provided requirements
        instances_list = get_matched_instances(session=session,
                                               vcpu_min=desired_vcpu,
                                               vcpu_max=desired_vcpu * 3,
                                               ram_min=desired_ram,
                                               ram_max=desired_ram * 3)

        # Get descriptions for the matched instances
        instances_description = get_instances_descriptions(session=session, instance_types=instances_list)

        # Get prices for on-demand matched instances
        instances_prices_on_demand = []
        for dictionary in get_ec2_on_demand_prices(session=session,
                                                   region_code=region,
                                                   instance_types=instances_list):
            tmp_dict = dictionary.copy()
            tmp_dict["Type"] = "On-demand"
            tmp_dict["Region"] = region
            tmp_dict["Description"] = [d for d in instances_description if
                                       d['InstanceType'] == tmp_dict['InstanceType']][0]
            tmp_dict["Discount"] = 0
            instances_prices_on_demand.append(tmp_dict)
        # Append on-demand prices to the global price list
        instances_prices.extend(instances_prices_on_demand)
        # Get spot prices for matched instances
        instances_prices_spot = []
        for dictionary in get_spot_prices(session=session,
                                          instances_types=instances_list):
            tmp_dict = dictionary.copy()
            tmp_dict["Type"] = "Spot"
            tmp_dict["Region"] = region
            tmp_dict["Description"] = [d for d in instances_description if
                                       d['InstanceType'] == tmp_dict['InstanceType']][0]
            if 'on-demand' in tmp_dict['Description']['SupportedUsageClasses']:
                tmp_dict["Discount"] = round(((float(
                    [d for d in instances_prices_on_demand if d['InstanceType'] == tmp_dict['InstanceType']][0][
                        'Price']) - float(tmp_dict['Price'])) / float(
                    [d for d in instances_prices_on_demand if d['InstanceType'] == tmp_dict['InstanceType']][0][
                        'Price'])) * 100)
            else:
                tmp_dict["Discount"] = 0
            instances_prices_on_demand.append(tmp_dict)
        # Append spot prices to the global price list
        instances_prices.extend(instances_prices_on_demand)
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
