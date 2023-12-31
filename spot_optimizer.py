from spot_optimizer_functions import *

if __name__ == "__main__":
    # Set the required parameters
    desired_vcpu = 2
    desired_ram = 16
    # Set the list of the desired regions (use the empty list to use all enabled regions)
    desired_regions = []
    # Global price list of the instances, which matches the requirements
    instances_prices = get_pricelist_global(profile_name='spot_optimizer',
                                            regions=desired_regions,
                                            vcpu_min=desired_vcpu,
                                            ram_min=desired_ram,
                                            arch_types=['i386', 'x86_64', 'arm64'])
    # Sort instances by price
    sorted_prices_list = sorted(instances_prices, key=lambda x: float(x['Price']), reverse=False)
    # Print 3 cheapest instances that matched the provided requirements
    print("Top 3 cheapest on-demand instances that matched the provided requirements:")
    print_pricelist(pricelist=sorted_prices_list, only_on_demand=True, lines=3)
    # Print 5 cheapest instances that matched the provided requirements
    print("\nTop 5 cheapest instances that matched the provided requirements:")
    print_pricelist(pricelist=sorted_prices_list, lines=5)
