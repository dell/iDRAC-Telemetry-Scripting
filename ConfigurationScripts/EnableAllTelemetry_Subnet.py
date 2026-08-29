#!/usr/bin/env python3
"""
Dell iDRAC Telemetry - FAST Enable All Reports.

Optimized with parallel processing and connection pooling.
Supports iDRAC 9 and iDRAC 10.
"""

import sys
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Tuple

import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging configuration
logging.basicConfig(
    format='%(message)s',
    stream=sys.stdout,
    level=logging.INFO
)

#####################################################
# CONFIGURATION
#####################################################

USERNAME: str = "root"
PASSWORD: str = "calvin"

#####################################################
# SERVER SELECTION
#####################################################

# Option 1: Specific IPs (takes priority if not empty)
IP_LIST: List[str] = [
    # "192.168.5.1",
    # "192.168.5.2",
]

# Option 2: Subnets (scans .1 to .254)
SUBNETS: List[str] = [
    "192.168.0",
    "192.168.0",
]

#####################################################
# EXCLUDE IPs (Skip these servers)
#####################################################

EXCLUDE_IPS: List[str] = [
    # "192.168.0.1",
    # "192.168.0.2",
    # "192.168.0.5",
]

#####################################################
# PARALLEL SETTINGS
#####################################################

PARALLEL_JOBS: int = 250
REPORT_WORKERS: int = 10
TIMEOUT: int = 5

LOG_FILE: str = f"telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

#####################################################
# ALL 37 TELEMETRY REPORTS (iDRAC 9 & 10)
#####################################################

ALL_REPORTS: List[str] = [
    # CPU & Memory
    "AggregationMetrics", "CPUMemMetrics", "CPURegisters",
    "CPUSensor", "MemoryMetrics", "MemorySensor",
    # Storage
    "NVMeSMARTData", "StorageDiskSMARTData", "StorageSensor",
    # Network
    "NICSensor", "NICStatistics", "FCPortStatistics",
    "FCSensor", "SFPTransceiver", "InfiniBandStatistics",
    # Power
    "PSUMetrics", "PowerMetrics", "PowerStatistics",
    # Thermal
    "FanSensor", "ThermalMetrics", "ThermalSensor",
    # GPU
    "GPUMetrics", "GPUStatistics", "GPUSubsystemPower", "FPGASensor",
    # System
    "Sensor", "SerialLog", "SystemUsage", "x86SubsystemPower",
    # OME Integration Reports
    "OME-ISM-MetricsData", "OME-PMP-Power-B",
    "OME-SFPTransceiver-Metrics", "OME-Telemetry-FCPortStatistics",
    "OME-Telemetry-GPU-Aggregate", "OME-Telemetry-GPU-Aggregate-1",
    "OME-Telemetry-NIC-Statistics", "OME-Telemetry-SMARTData",
]

#####################################################
# EXCLUDE REPORTS (Skip these reports)
#####################################################

EXCLUDE_REPORTS: List[str] = [
    # "SerialLog",
    # "GPUMetrics",
    # "GPUStatistics",
]

#####################################################
# REPORT CATEGORIES (for display)
#####################################################

REPORT_CATEGORIES: Dict[str, List[str]] = {
    "CPU & Memory": [
        "AggregationMetrics", "CPUMemMetrics", "CPURegisters",
        "CPUSensor", "MemoryMetrics", "MemorySensor"
    ],
    "Storage": [
        "NVMeSMARTData", "StorageDiskSMARTData", "StorageSensor"
    ],
    "Network": [
        "NICSensor", "NICStatistics", "FCPortStatistics",
        "FCSensor", "SFPTransceiver", "InfiniBandStatistics"
    ],
    "Power": [
        "PSUMetrics", "PowerMetrics", "PowerStatistics"
    ],
    "Thermal": [
        "FanSensor", "ThermalMetrics", "ThermalSensor"
    ],
    "GPU": [
        "GPUMetrics", "GPUStatistics", "GPUSubsystemPower", "FPGASensor"
    ],
    "System": [
        "Sensor", "SerialLog", "SystemUsage", "x86SubsystemPower"
    ],
    "OME Integration": [
        "OME-ISM-MetricsData", "OME-PMP-Power-B",
        "OME-SFPTransceiver-Metrics", "OME-Telemetry-FCPortStatistics",
        "OME-Telemetry-GPU-Aggregate", "OME-Telemetry-GPU-Aggregate-1",
        "OME-Telemetry-NIC-Statistics", "OME-Telemetry-SMARTData"
    ]
}


def get_report_definitions(
    ip_address: str,
    user: str,
    password: str,
    session: requests.Session
) -> Optional[List[str]]:
    """
    Fetch available report definitions from iDRAC.

    Args:
        ip_address: iDRAC IP address
        user: Username for authentication
        password: Password for authentication
        session: Requests session object

    Returns:
        List of report names or None if failed
    """
    url = f"https://{ip_address}/redfish/v1/TelemetryService/MetricReportDefinitions"
    try:
        response = session.get(
            url,
            auth=(user, password),
            verify=False,
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            reports = [
                member['@odata.id'].split('/')[-1]
                for member in data.get('Members', [])
            ]
            return reports
    except (requests.exceptions.RequestException, ValueError, KeyError):
        pass
    return None


def enable_report(
    session: requests.Session,
    url: str,
    user: str,
    password: str
) -> bool:
    """
    Enable a single telemetry report.

    Args:
        session: Requests session object
        url: Report URL to enable
        user: Username for authentication
        password: Password for authentication

    Returns:
        True if successful, False otherwise
    """
    try:
        data = {
            "MetricReportDefinitionEnabled": True,
            "Status": {"State": "Enabled"}
        }
        response = session.patch(
            url,
            json=data,
            auth=(user, password),
            verify=False,
            timeout=TIMEOUT
        )
        return response.status_code in [200, 202, 204]
    except requests.exceptions.RequestException:
        return False


def create_fail_result(ip_address: str, message: str) -> Dict[str, Any]:
    """
    Create a failure result dictionary.

    Args:
        ip_address: Server IP address
        message: Failure message

    Returns:
        Dictionary with failure details
    """
    return {
        'ip': ip_address,
        'status': 'FAIL',
        'message': message,
        'enabled': [],
        'skipped': [],
        'failed': []
    }


def enable_reports_parallel(
    session: requests.Session,
    base_url: str,
    reports_to_enable: List[str],
    user: str,
    password: str
) -> Tuple[List[str], List[str]]:
    """
    Enable multiple reports in parallel.

    Args:
        session: Requests session object
        base_url: Base telemetry URL
        reports_to_enable: List of report names to enable
        user: Username for authentication
        password: Password for authentication

    Returns:
        Tuple of (enabled_reports, failed_reports)
    """
    enabled_reports: List[str] = []
    failed_reports: List[str] = []

    report_urls = {
        report: f"{base_url}/MetricReportDefinitions/{report}"
        for report in reports_to_enable
    }

    with ThreadPoolExecutor(max_workers=REPORT_WORKERS) as executor:
        future_to_report = {
            executor.submit(enable_report, session, url, user, password): report
            for report, url in report_urls.items()
        }
        for future in as_completed(future_to_report):
            report_name = future_to_report[future]
            if future.result():
                enabled_reports.append(report_name)
            else:
                failed_reports.append(report_name)

    return enabled_reports, failed_reports


def configure_server(server_info: Dict[str, str]) -> Dict[str, Any]:
    """
    Configure telemetry for a single server.

    Args:
        server_info: Dictionary containing ip, username, password

    Returns:
        Dictionary with ip, status, message, and report details
    """
    ip_address = server_info['ip']
    user = server_info['username']
    password = server_info['password']

    session = requests.Session()
    session.verify = False

    try:
        base_url = f"https://{ip_address}/redfish/v1/TelemetryService"

        # Step 1: Enable Telemetry Service
        response = session.patch(
            base_url,
            json={"ServiceEnabled": True},
            auth=(user, password),
            timeout=TIMEOUT
        )

        if response.status_code not in [200, 202, 204]:
            return create_fail_result(
                ip_address, f"Service HTTP {response.status_code}"
            )

        # Step 2: Get available reports dynamically
        available_reports = get_report_definitions(
            ip_address, user, password, session
        )
        if not available_reports:
            return create_fail_result(ip_address, "Cannot get reports")

        # Step 3: Filter out excluded reports
        reports_to_enable = [
            r for r in available_reports if r not in EXCLUDE_REPORTS
        ]
        skipped_reports = [
            r for r in available_reports if r in EXCLUDE_REPORTS
        ]

        # Step 4: Enable reports in parallel
        enabled_reports, failed_reports = enable_reports_parallel(
            session, base_url, reports_to_enable, user, password
        )

        return {
            'ip': ip_address,
            'status': 'OK',
            'message': (
                f"{len(enabled_reports)}/{len(available_reports)} "
                f"(skipped: {len(skipped_reports)})"
            ),
            'enabled': enabled_reports,
            'skipped': skipped_reports,
            'failed': failed_reports
        }

    except requests.exceptions.ConnectTimeout:
        return create_fail_result(ip_address, "Timeout")
    except requests.exceptions.ConnectionError:
        return create_fail_result(ip_address, "No connection")
    except requests.exceptions.RequestException as err:
        return create_fail_result(ip_address, str(err)[:30])
    finally:
        session.close()


def generate_servers() -> List[Dict[str, str]]:
    """
    Generate server list from subnets or IP list.

    Returns:
        List of server dictionaries with ip, username, password
    """
    servers: List[Dict[str, str]] = []

    if IP_LIST:
        for ip_address in IP_LIST:
            if ip_address not in EXCLUDE_IPS:
                servers.append({
                    'ip': ip_address,
                    'username': USERNAME,
                    'password': PASSWORD
                })
    else:
        for subnet in SUBNETS:
            for i in range(1, 255):
                ip_address = f"{subnet}.{i}"
                if ip_address not in EXCLUDE_IPS:
                    servers.append({
                        'ip': ip_address,
                        'username': USERNAME,
                        'password': PASSWORD
                    })

    return servers


def print_report_list() -> None:
    """Print all available telemetry reports."""
    print("=" * 46)
    print("ALL TELEMETRY REPORTS (37 Total)")
    print("=" * 46)

    for category, reports in REPORT_CATEGORIES.items():
        print(f"\n  {category}:")
        for report in reports:
            status = "[SKIP]" if report in EXCLUDE_REPORTS else "[OK]  "
            print(f"    {status} {report}")

    print()
    print(f"  Total Reports:     {len(ALL_REPORTS)}")
    print(f"  Excluded Reports:  {len(EXCLUDE_REPORTS)}")
    print(f"  Reports to Enable: {len(ALL_REPORTS) - len(EXCLUDE_REPORTS)}")
    print("=" * 46)


def print_ip_list() -> None:
    """Print IP configuration."""
    print("=" * 46)
    print("SERVER CONFIGURATION")
    print("=" * 46)

    if IP_LIST:
        print(f"\n  Mode: IP List ({len(IP_LIST)} configured)")
        print()
        for ip_addr in IP_LIST:
            status = "[SKIP]" if ip_addr in EXCLUDE_IPS else "[OK]  "
            print(f"    {status} {ip_addr}")
    else:
        print("\n  Mode: Subnets")
        print()
        for subnet in SUBNETS:
            print(f"    [OK]   {subnet}.1 - {subnet}.254")

    if EXCLUDE_IPS:
        print()
        print(f"  Excluded IPs ({len(EXCLUDE_IPS)}):")
        for ip_addr in EXCLUDE_IPS:
            print(f"    [SKIP] {ip_addr}")

    # Calculate total
    if IP_LIST:
        total = len([ip for ip in IP_LIST if ip not in EXCLUDE_IPS])
    else:
        total = sum(254 for _ in SUBNETS) - len(EXCLUDE_IPS)

    print()
    print(f"  Total to Process:  {total}")
    print(f"  Total Excluded:    {len(EXCLUDE_IPS)}")
    print("=" * 46)


def write_log_header(log_file, server_count: int) -> None:
    """
    Write log file header.

    Args:
        log_file: File handle to write to
        server_count: Total number of servers
    """
    log_file.write("=" * 60 + "\n")
    log_file.write("Dell iDRAC Telemetry - Enable Report Log\n")
    log_file.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write("=" * 60 + "\n")
    log_file.write(f"Total Servers: {server_count}\n")
    log_file.write(f"Excluded IPs: {len(EXCLUDE_IPS)}\n")
    log_file.write(f"Excluded Reports: {len(EXCLUDE_REPORTS)}\n")
    log_file.write("=" * 60 + "\n\n")


def write_log_success(log_file, result: Dict[str, Any]) -> None:
    """
    Write successful result to log file.

    Args:
        log_file: File handle to write to
        result: Result dictionary
    """
    log_file.write(f"\n{'=' * 50}\n")
    log_file.write(f"Server: {result['ip']}\n")
    log_file.write("Status: OK\n")
    log_file.write(
        f"Enabled ({len(result['enabled'])}): "
        f"{', '.join(result['enabled'])}\n"
    )
    if result['skipped']:
        log_file.write(
            f"Skipped ({len(result['skipped'])}): "
            f"{', '.join(result['skipped'])}\n"
        )
    if result['failed']:
        log_file.write(
            f"Failed ({len(result['failed'])}): "
            f"{', '.join(result['failed'])}\n"
        )


def run_parallel(servers: List[Dict[str, str]]) -> Tuple[int, int, int]:
    """
    Run telemetry configuration in parallel.

    Args:
        servers: List of server dictionaries

    Returns:
        Tuple of (success_count, fail_count, duration)
    """
    success_count = 0
    fail_count = 0
    start_time = time.time()

    with open(LOG_FILE, 'w', encoding='utf-8') as log:
        write_log_header(log, len(servers))

        with ThreadPoolExecutor(max_workers=PARALLEL_JOBS) as executor:
            futures = {
                executor.submit(configure_server, server): server
                for server in servers
            }

            for future in as_completed(futures):
                result = future.result()

                if result['status'] == 'OK':
                    output = f"[OK] {result['ip']}: {result['message']}"
                    success_count += 1
                    write_log_success(log, result)
                else:
                    output = f"[FAIL] {result['ip']}: {result['message']}"
                    fail_count += 1
                    log.write(f"\n[FAIL] {result['ip']}: {result['message']}\n")

                print(output)
                sys.stdout.flush()

    duration = int(time.time() - start_time)
    return success_count, fail_count, duration


def print_summary(
    server_count: int,
    success_count: int,
    fail_count: int,
    duration: int
) -> None:
    """
    Print execution summary.

    Args:
        server_count: Total servers processed
        success_count: Successful count
        fail_count: Failed count
        duration: Duration in seconds
    """
    print()
    print("=" * 46)
    print("SUMMARY")
    print("=" * 46)
    print(f"Total Servers:    {server_count}")
    print(f"Successful:       {success_count}")
    print(f"Failed:           {fail_count}")
    print(f"Excluded IPs:     {len(EXCLUDE_IPS)}")
    reports_enabled = len(ALL_REPORTS) - len(EXCLUDE_REPORTS)
    print(f"Reports Config:   {reports_enabled}/{len(ALL_REPORTS)}")
    print(f"Excluded Reports: {len(EXCLUDE_REPORTS)}")
    print(f"Duration:         {duration} seconds")
    print(f"Log File:         {LOG_FILE}")
    print("=" * 46)


def main() -> None:
    """Main function to run telemetry configuration."""
    print()
    print("=" * 46)
    print("Dell iDRAC Telemetry - FAST Enable")
    print("=" * 46)
    print(f"Username:        {USERNAME}")
    print(f"Parallel Jobs:   {PARALLEL_JOBS}")
    print(f"Report Workers:  {REPORT_WORKERS}")
    print(f"Timeout:         {TIMEOUT} sec")
    print("=" * 46)
    print()

    # Print IP configuration
    print_ip_list()
    print()

    # Print report list with exclusions
    print_report_list()
    print()

    # Generate servers
    servers = generate_servers()

    if not servers:
        print("ERROR: No servers to process!")
        print("       Configure IP_LIST or SUBNETS")
        sys.exit(1)

    print(f"Total Servers to Process: {len(servers)}")
    print()

    print("Enabling Telemetry...")
    print("=" * 46)

    success_count, fail_count, duration = run_parallel(servers)

    print_summary(len(servers), success_count, fail_count, duration)


if __name__ == "__main__":
    main()

