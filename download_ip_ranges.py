#!/usr/bin/env python3
import json
import yaml
import requests
import argparse
import sys
import os
from pathlib import Path
import ipaddress
from datetime import datetime


def load_sources():
    """Load sources from sources.yaml file."""
    with open("sources.yaml", "r") as f:
        return yaml.safe_load(f)


def download_json(url):
    """Download JSON from a URL."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error downloading from {url}: {e}")
        return None


def parse_zscaler_hub_ips(data):
    """Parse ZscalerHubIPAddresses format JSON."""
    ips = []
    if data and "hubPrefixes" in data:
        for ip in data["hubPrefixes"]:
            # Filter out IPv6 addresses
            if ":" not in ip:
                ips.append(ip)
    return ips


def parse_cloud_enforcement_nodes(data):
    """Parse CloudEnforcementNodeRanges format JSON."""
    ips = []
    if data and "prefixes" in data:
        for ip in data["prefixes"]:
            # Filter out IPv6 addresses
            if ":" not in ip:
                ips.append(ip)
    return ips


def parse_zpa_allowlist(data):
    """Parse ZPAAllowList format JSON."""
    ips = []
    if data and "content" in data:
        for item in data["content"]:
            if "IPs" in item:
                for ip in item["IPs"]:
                    # Filter out IPv6 addresses
                    if ":" not in ip:
                        ips.append(ip)
    return ips


def read_digicert_subnets():
    """Read DigiCert subnets from text file."""
    subnets = []
    try:
        with open("digicert-subnets.txt", "r") as f:
            for line in f:
                subnet = line.strip()
                if subnet and ":" not in subnet:  # Skip IPv6
                    subnets.append(subnet)
    except FileNotFoundError:
        print("Warning: digicert-subnets.txt not found")
    return subnets


def consolidate_networks(ip_list):
    """Consolidate overlapping IPv4 networks."""
    # Convert strings to IPv4Network objects
    networks = []
    for ip_str in ip_list:
        try:
            # Handle single IPs by adding /32
            if "/" not in ip_str:
                ip_str += "/32"
            network = ipaddress.IPv4Network(ip_str.strip(), strict=False)
            networks.append(network)
        except (ipaddress.AddressValueError, ValueError) as e:
            print(f"Error parsing address: {ip_str}: {e}")
            continue
    
    # Sort networks by network address
    networks.sort(key=lambda x: x.network_address)
    
    # Consolidate networks
    consolidated = []
    if not networks:
        return consolidated
    
    current = networks[0]
    for next_net in networks[1:]:
        # Check if networks overlap or are adjacent
        if current.supernet_of(next_net):
            # current already contains next_net
            continue
        elif next_net.supernet_of(current):
            # next_net contains current
            current = next_net
        elif (current.network_address <= next_net.broadcast_address and 
              next_net.network_address <= current.broadcast_address):
            # Networks overlap, merge them
            # Find the minimal supernet that covers both
            first_ip = min(current.network_address, next_net.network_address)
            last_ip = max(current.broadcast_address, next_net.broadcast_address)
            
            # Calculate the appropriate prefix length
            try:
                supernet_list = list(ipaddress.summarize_address_range(first_ip, last_ip))
                if len(supernet_list) == 1:
                    current = supernet_list[0]
                else:
                    # Can't merge into single subnet, keep separate
                    consolidated.append(current)
                    current = next_net
            except:
                consolidated.append(current)
                current = next_net
        else:
            # No overlap, add current and move to next
            consolidated.append(current)
            current = next_net
    
    # Add the last network
    consolidated.append(current)
    
    return consolidated


def select_domain(sources):
    """Present domain selection menu to user."""
    domains = set()
    
    # Collect all unique domains
    for source_type in ["ZscalerHubIPAddresses", "CloudEnforcementNodeRanges"]:
        if source_type in sources:
            domains.update(sources[source_type].keys())
    
    domains = sorted(list(domains))
    
    print("\nSelect Zscaler domain:")
    for i, domain in enumerate(domains, 1):
        print(f"{i}. {domain}")
    
    while True:
        try:
            choice = input("\nEnter number (1-{}): ".format(len(domains)))
            idx = int(choice) - 1
            if 0 <= idx < len(domains):
                return domains[idx]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def main():
    parser = argparse.ArgumentParser(
        description="Download and consolidate Zscaler IP ranges"
    )
    parser.add_argument(
        "--domain",
        help="Zscaler domain (e.g., zscaler.net). If not specified, will prompt."
    )
    parser.add_argument(
        "--output",
        default="zpa_bc_subnet_consolidate.txt",
        help="Output file name (default: zpa_bc_subnet_consolidate.txt)"
    )
    
    args = parser.parse_args()
    
    # Load sources
    print("Loading sources from sources.yaml...")
    sources = load_sources()
    
    # Select domain
    if args.domain:
        domain = args.domain
    else:
        domain = select_domain(sources)
    
    print(f"\nUsing domain: {domain}")
    
    all_ips = []
    
    # Download ZscalerHubIPAddresses
    if "ZscalerHubIPAddresses" in sources and domain in sources["ZscalerHubIPAddresses"]:
        url = sources["ZscalerHubIPAddresses"][domain]
        print(f"\nDownloading ZscalerHubIPAddresses from {url}...")
        data = download_json(url)
        if data:
            ips = parse_zscaler_hub_ips(data)
            print(f"Found {len(ips)} IP ranges")
            all_ips.extend(ips)
    
    # Download CloudEnforcementNodeRanges
    if "CloudEnforcementNodeRanges" in sources and domain in sources["CloudEnforcementNodeRanges"]:
        url = sources["CloudEnforcementNodeRanges"][domain]
        print(f"\nDownloading CloudEnforcementNodeRanges from {url}...")
        data = download_json(url)
        if data:
            ips = parse_cloud_enforcement_nodes(data)
            print(f"Found {len(ips)} IP ranges")
            all_ips.extend(ips)
    
    # Download ZPAAllowList (domain-independent)
    if "ZPAAllowList" in sources:
        url = sources["ZPAAllowList"]
        print(f"\nDownloading ZPAAllowList from {url}...")
        data = download_json(url)
        if data:
            ips = parse_zpa_allowlist(data)
            print(f"Found {len(ips)} IP ranges")
            all_ips.extend(ips)
    
    # Add DigiCert subnets
    print("\nReading DigiCert subnets...")
    digicert_ips = read_digicert_subnets()
    print(f"Found {len(digicert_ips)} DigiCert subnets")
    all_ips.extend(digicert_ips)
    
    # Remove duplicates
    print(f"\nTotal IP ranges collected: {len(all_ips)}")
    all_ips = list(set(all_ips))
    print(f"Unique IP ranges: {len(all_ips)}")
    
    # Consolidate networks
    print("\nConsolidating overlapping networks...")
    consolidated = consolidate_networks(all_ips)
    print(f"Consolidated to {len(consolidated)} networks")
    
    # Write output
    with open(args.output, "w") as f:
        for network in consolidated:
            f.write(f"{network}\n")
    
    print(f"\nResults saved to: {args.output}")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()