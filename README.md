# Zscaler IP Range Consolidator

---

**Copyright (c) 2025 ZHERO srl, Italy**  
**Website:** [https://zhero.ai](https://zhero.ai)

This project is released under the MIT License. See the LICENSE file for full details.

---

## Overview

This tool automates the process of downloading and consolidating IP ranges required for Zscaler connectivity whitelist configurations. It retrieves IP ranges from multiple Zscaler sources, including Hub IP addresses, Cloud Enforcement Node ranges, and ZPA Allow Lists, then consolidates overlapping subnets to create an optimized list for firewall and network configurations.

### Problem Statement

Organizations using Zscaler services need to whitelist specific IP ranges in their firewalls to ensure proper connectivity for:

-   **Zscaler Client Connector (ZCC)**: Requires access to Zscaler service IPs for policy enforcement and cloud security
-   **Zscaler Private Access (ZPA)**: Needs connectivity to ZPA infrastructure for zero-trust network access
-   **Branch Connectors**: Require access to Zscaler cloud infrastructure

Manually maintaining these IP lists is challenging because:

-   IP ranges change periodically as Zscaler expands infrastructure
-   Multiple sources need to be consolidated
-   Overlapping subnets create inefficient firewall rules
-   Different Zscaler clouds (zscaler.net, zscloud.net, etc.) have different IP ranges

### Solution

This tool provides:

1. **Automated downloading** of current IP ranges from official Zscaler configuration endpoints
2. **Multi-source consolidation** combining Hub IPs, Cloud Enforcement Nodes, and ZPA Allow Lists
3. **Subnet optimization** merging overlapping IP ranges for efficient firewall rules
4. **Domain-specific configuration** supporting all Zscaler cloud environments
5. **DigiCert integration** including certificate validation IPs

## Architecture

```
┌─────────────────────┐
│   sources.yaml      │
│ (URL Configuration) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│ Zscaler Hub IPs     │     │ Cloud Enforcement   │
│ (JSON API)          │────▶│ download_ip_ranges  │
└─────────────────────┘     │      .py            │
                            │                     │
┌─────────────────────┐     │  1. Download JSONs  │
│ ZPA Allow List      │────▶│  2. Parse formats   │
│ (JSON API)          │     │  3. Extract IPs     │
└─────────────────────┘     │  4. Add DigiCert    │
                            │  5. Consolidate     │
┌─────────────────────┐     │     subnets         │
│ digicert-subnets    │────▶│                     │
│      .txt           │     └──────────┬──────────┘
└─────────────────────┘                │
                                       ▼
                            ┌─────────────────────┐
                            │ zpa_bc_subnet_      │
                            │ consolidate.txt     │
                            │ (Optimized list)    │
                            └─────────────────────┘
```

## Installation

### Prerequisites

-   Python 3.6+
-   pip (Python package installer)

### Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/zscaler-config-whitelist-subnets.git
cd zscaler-config-whitelist-subnets
```

2. Install required Python packages:

```bash
pip install requests pyyaml
```

## Usage

### Interactive Mode (Recommended)

Run the script without arguments to select your Zscaler domain interactively:

```bash
python download_ip_ranges.py
```

The script will present a menu:

```
Select Zscaler domain:
1. zscaler.net
2. zscalerbeta.net
3. zscalerone.net
4. zscalerthree.net
5. zscalertwo.net
6. zscloud.net

Enter number (1-6): 1
```

### Command Line Mode

Specify the domain directly:

```bash
python download_ip_ranges.py --domain zscaler.net
```

### Custom Output File

```bash
python download_ip_ranges.py --domain zscloud.net --output my_whitelist.txt
```

### Example Output

```
Loading sources from sources.yaml...
Using domain: zscaler.net

Downloading ZscalerHubIPAddresses from https://config.zscaler.com/api/zscaler.net/hubs/cidr/json/recommended...
Found 127 IP ranges

Downloading CloudEnforcementNodeRanges from https://config.zscaler.com/api/zscaler.net/future/json...
Found 89 IP ranges

Downloading ZPAAllowList from https://config.zscaler.com/api/private.zscaler.com/zpa/json...
Found 45 IP ranges

Reading DigiCert subnets...
Found 101 DigiCert subnets

Total IP ranges collected: 362
Unique IP ranges: 298

Consolidating overlapping networks...
Consolidated to 187 networks

Results saved to: zpa_bc_subnet_consolidate.txt
Generated on: 2025-01-15 10:30:45
```

## Configuration

### sources.yaml

The `sources.yaml` file contains URLs for all Zscaler IP range sources:

```yaml
ZscalerHubIPAddresses:
    zscaler.net: https://config.zscaler.com/api/zscaler.net/hubs/cidr/json/recommended
    zscloud.net: https://config.zscloud.net/hubs/cidr/json/recommended
    # ... other domains

CloudEnforcementNodeRanges:
    zscaler.net: https://config.zscaler.com/api/zscaler.net/future/json
    zscloud.net: https://config.zscloud.net/future/json
    # ... other domains

ZPAAllowList: https://config.zscaler.com/api/private.zscaler.com/zpa/json
```

### digicert-subnets.txt

Contains DigiCert IP addresses required for certificate validation. These are automatically included in the consolidated output.

## API Endpoints Used

The tool retrieves data from these Zscaler configuration endpoints:

1. **Hub IP Addresses**:

    - Format: `https://config.{domain}/api/{domain}/hubs/cidr/json/recommended`
    - Contains: Zscaler data center IP ranges for ZCC connectivity

2. **Cloud Enforcement Node Ranges**:

    - Format: `https://config.{domain}/api/{domain}/future/json`
    - Contains: IP ranges for cloud security enforcement

3. **ZPA Allow List**:
    - URL: `https://config.zscaler.com/api/private.zscaler.com/zpa/json`
    - Contains: IP ranges required for ZPA connectivity

## Output Format

The consolidated output file contains one subnet per line in CIDR notation:

```
8.25.203.0/24
23.4.43.0/24
52.18.93.240/32
58.220.95.0/24
64.215.22.0/24
104.129.192.0/20
136.226.0.0/16
...
```

## Performance Notes

-   Optimized for processing hundreds of IP ranges efficiently
-   Uses Python's `ipaddress` module for accurate subnet calculations
-   Deduplicates entries before consolidation
-   Memory-efficient processing suitable for large datasets

## Use Cases

### Firewall Configuration

Use the consolidated list to configure outbound firewall rules:

```bash
# Example for iptables
while read subnet; do
    iptables -A OUTPUT -d "$subnet" -j ACCEPT
done < zpa_bc_subnet_consolidate.txt
```

### Network Security Groups (Cloud)

Import into cloud provider security groups for Zscaler connectivity.

### Documentation

Generate network documentation with current Zscaler IP ranges.

## Troubleshooting

### Connection Errors

If you encounter connection errors:

1. Verify internet connectivity
2. Check if your network requires proxy configuration
3. Ensure the Zscaler configuration URLs are accessible

### Missing DigiCert Subnets

The warning "digicert-subnets.txt not found" is non-fatal. The tool will continue without DigiCert IPs.

### Large Output Files

If the consolidated list seems too large:

1. Verify you selected the correct Zscaler domain
2. Check if subnet consolidation is working (output should be smaller than input)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:

-   Open an issue on GitHub
-   Contact ZHERO support at https://zhero.ai

## Changelog

### Version 1.0.0 (2025-01-15)

-   Initial release
-   Support for all Zscaler cloud domains
-   Automated subnet consolidation
-   DigiCert subnet integration
