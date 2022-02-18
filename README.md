# iDRAC-Telemetry-Scripting  

- [iDRAC-Telemetry-Scripting](#idrac-telemetry-scripting)
  - [Telemetry Overview](#telemetry-overview)
  - [Available Scripts](#available-scripts)
  - [iDRAC with Lifecycle Controller Overview](#idrac-with-lifecycle-controller-overview)
  - [Learning more about iDRAC and Telemetry](#learning-more-about-idrac-and-telemetry)
  - [iDRAC Telemetry Scripting Library](#idrac-telemetry-scripting-library)
  - [Support](#support)
  
Python scripting for Dell EMC PowerEdge iDRAC Telemetry  
  
Sample scripts written in Python that illustrate using the integrated Dell Remote Access Controller (iDRAC) REST API with Redfish to manage Dell EMC PowerEdge servers and configure Telemetry reports.  
Additionally, the library contains sample scripts for processing iDRAC Telemetry reports.   
  
## Telemetry Overview  

This feature requires the iDRAC datacenter license which is available for trial [here](https://www.dell.com/support/kbdoc/en-us/000176472/idrac-cmc-openmanage-enterprise-openmanage-integration-with-microsoft-windows-admin-center-openmanage-integration-with-servicenow-and-dpat-trial-licenses).
iDRAC telemetry allows you to stream telemetry data from your servers to a centralized log/metrics servers. Currently telemetry supports stats from the following devices:

- NICs
- Fiber channel
- FPGAs
- GPUs
- NVMe
- Fans
- Power supplies
- Thermal
- Memory
- CPUs
- Sensors
- Storage
- General host performance
- Serial logs
- CPU registers

## Available Scripts

- AddRedfishSubscription.py: Adds a POST subscription to the iDRAC
- DeleteRedfishSubscription:  deletes a subscription from iDRAC
- EnableOrDisableAllTelemetryReports: Enables or disables all telemetry reports on the iDRAC. You can later filter which reports are or aren't sent for a given subscription.
- ExportTelemetryConfigurationUsingScpREDFISH.py - Exports a telemetry configuration using a server configuration profile
- ImportTelemetryConfigurationUsingScpREDFISH.py - Imports a telemetry configuration using a server configuration profile
- ManageTelemetryConnections.py - Provides a comprehensive script for managing various connections to telemetry. This includes the following functionality:
  - Listing POST subscriptions on a target server
  - Deleting POST subscriptions on a target server
  - Sending POST test events to a target device
  - Adding POST subscriptions to a target device
  - Run an SSE client and dump the output to console
  
## iDRAC with Lifecycle Controller Overview  
  
The Integrated Dell Remote Access Controller (iDRAC) is designed to enhance the productivity of server administrators and improve the overall availability of PowerEdge servers. iDRAC alerts administrators to server problems, enabling remote server management, and reducing the need for an administrator to physically visit the server.  
iDRAC with Lifecycle Controller allows administrators to deploy, update, monitor and manage Dell servers from any location without the use of agents in a one-to-one or one-to-many method. This out-of-band management allows configuration changes and firmware updates to be managed from Dell EMC, appropriate third-party consoles, and custom scripting directly to iDRAC with Lifecycle Controller using supported industry-standard API’s.  
To support the Redfish standard, the iDRAC with Lifecycle Controller includes support for the iDRAC REST API in addition to support for the IPMI, SNMP, and WS-Man standard APIs. The iDRAC REST API builds upon the Redfish standard to provide a RESTful interface for Dell EMC value-add operations including:  
  
- Information on all iDRAC with Lifecycle Controller out-of-band services—web server, SNMP, virtual media, SSH, Telnet, IPMI, and KVM  
- Expanded storage subsystem reporting covering controllers, enclosures, and drives  
- For the PowerEdge FX2 modular server, detailed chassis information covering power supplies, temperatures, and fans  
- With the iDRAC Service Module (iSM) installed under the server OS, the API provides detailed inventory and status reporting for host network interfaces including such details as IP address, subnet mask, and gateway for the Host OS.  
  
## Learning more about iDRAC and Telemetry  
  
For complete information concerning iDRAC with Lifecycle Controller, see the documents at http://www.dell.com/idracmanuals .  
  
For an overview of the Telemetry and Redfish implementation for iDRAC with Lifecycle Controller, see these Dell EMC white papers:  
  
Implementation of the DMTF Redfish API on Dell EMC PowerEdge Servers http://en.community.dell.com/techcenter/extras/m/white_papers/20442330  
  
RESTful Server Configuration with iDRAC REST API http://en.community.dell.com/techcenter/extras/m/white_papers/20443207  
  
For details on the DMTF Redfish standard, visit https://www.dmtf.org/standards/redfish

idrac Telemetry API Documentation: https://developer.dell.com/apis/2978/versions/5.xx/docs/Tasks/3Telemetry.md
  
  
## iDRAC Telemetry Scripting Library  

This GitHub library contains example Python scripts that illustrate the usage of the iDRAC REST API with Redfish to perform the following actions:  
  
Telemetry configurations operations  

- Export Telemetry Configurations
- Import Telemetry Configurations 
- Enable/Disable All Telemetry 

  
## Support  

Please note this code is provided as-is and currently not supported by Dell EMC.

To provide feedback or ask for help please post an issue at https://github.com/dell/iDRAC-Telemetry-Scripting/issues
