import boto3

# Set the required parameters
desired_vcpu = 2
desired_ram = 16
desired_regions = ['us-west-2', 'eu-west-1', 'ap-southeast-1']  # List of desired regions

# Dictionary to store the best configuration for each region
best_instance_by_region = {}

# Iterate over each region
for region in desired_regions:
    # Initialize the AWS Client
    session = boto3.Session(profile_name='spot_optimizer', region_name=region)
    ec2_client = session.client('ec2')

    # Get information about Spot prices
    response = ec2_client.describe_spot_price_history(
        InstanceTypes=[],  # Get pricing only for some instance types
        ProductDescriptions=['Linux/UNIX'],  # Specify operating system
        MaxResults=10,  # Increase the maximum number of results if necessary
        AvailabilityZone=region + 'a'  # Select an Availability Zone in a Region
    )

    # Find the best configuration in your current region
    best_price = None
    best_instance_type = None
    for price in response['SpotPriceHistory']:
        instance_type = price['InstanceType']
        instance_info = ec2_client.describe_instance_types(InstanceTypes=[instance_type])
        vcpu = int(instance_info['InstanceTypes'][0]['VCpuInfo']['DefaultVCpus'])
        ram = int(instance_info['InstanceTypes'][0]['MemoryInfo']['SizeInMiB']) * 1024
        if vcpu >= desired_vcpu and ram >= desired_ram:
            if best_price is None or float(price['SpotPrice']) < best_price:
                best_price = float(price['SpotPrice'])
                best_instance_type = instance_type

    if best_instance_type is not None:
        best_instance_by_region[region] = best_instance_type

# Output of the best configurations for each region
for region, instance_type in best_instance_by_region.items():
    print(f"Best instance type in region {region}: {instance_type}")
