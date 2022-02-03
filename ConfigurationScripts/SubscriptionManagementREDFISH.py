#
# SubscriptionManagementREDFISH. Python script using Redfish API to either get event service properties, get event
# subscriptions, create / delete subscriptions or submit test event.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _author_ = Grant Curell <grant_curell@dell.com>
# _version_ = 2.0
#
# Copyright (c) 2022, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import argparse
import json
import logging
import re
import sys
import time
import warnings
from pprint import pprint
from pprint import pformat

import requests

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API to either get event service properties,"
                                 " get event subscriptions, create / delete subscriptions or submit test event.")
parser.add_argument('--ip-address', '-ip', help='iDRAC IP address', required=False, dest='idrac_ip')
parser.add_argument('--idrac-user', '-u', help='iDRAC username', required=False, dest='idrac_username')
parser.add_argument('--idrac-password', '-p', help='iDRAC password', required=False, dest='idrac_password')
parser.add_argument('--script-examples', action="store_true", help='Prints script examples')
parser.add_argument('--get-event-properties', '-e', action="store_true", help='Get event service properties',
                    required=False, dest='get_event_properties')
parser.add_argument('--get-subscriptions', '-s', help='Retrieve a list of current subscriptions. Pass in argument'
                    ' \'detailed\' for a more verbose description of subscriptions.', required=False,
                    choices=['detailed', 'simple'], dest='get_subscriptions')
parser.add_argument('--create-subscription', '-c', action="store_true", help='Create a new subscription. This must be '
                    'accompanied by the arguments -D, -V and -E.', required=False, dest='create_subscription')
parser.add_argument('--test-event', '-t', action="store_true", help='Submit test event. You must also use arguments '
                    '-D, -E and -M to submit a test event', required=False, dest='test_event')
parser.add_argument('--destination-url', '-D', help='Pass in destination HTTPS URI path for either create '
                    'subscription or send test event', required=False, dest='destination_url')
parser.add_argument('--format-type', '-V', help='Pass in Event Format Type for creating a subscription. Supported'
                    ' values are \"Event\", \"MetricReport\" or \"None\"', required=False, dest='format_type')
parser.add_argument('--event-type', '-E', help='The EventType value for either create subscription or send test '
                    'event. Supported values are StatusChange, ResourceUpdated, ResourceAdded, ResourceRemoved, '
                    'Alert, MetricReport.', required=False, dest='event_type')
parser.add_argument('--subscription-type', '-b', help='Controls the type of subscription created. \'See Telemetry '
                    'Streaming with iDRAC9 — What you Need to Get Started\' for detailed information. The default '
                    'option is to create an HTTP POST subscription. You can also set up a RedFish client with HTTP '
                    'Server Sent Events (SSE). Options are POST and SSE. When using the type SSE, this will open a '
                    'connection to the server and then print the output to console', choices=['POST', 'SSE'],
                    default='POST', dest='subscription_type')
parser.add_argument('--message-id', '-M', help='Pass in MessageID for sending test event. Example: TMP0118',
                    required=False, dest='message_type')
parser.add_argument('--delete', help='Pass in complete service subscription URI to delete. Execute -s argument if '
                    'needed to get subscription URIs', required=False)
args = vars(parser.parse_args())


def validate_telemetry_support(idrac_ip: str, idrac_username: str, idrac_password: str):
    """
    Ensures that the targeted server supports telemetry before we take action

    :param idrac_ip: IP address of the target iDRAC
    :param idrac_username: Username of the target iDRAC
    :param idrac_password: Password of the target iDRAC
    """

    url = 'https://{}/redfish/v1/TelemetryService'.format(idrac_ip)
    headers = {'content-type': 'application/json'}
    response = requests.get(url, headers=headers, verify=False, auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        logging.error("Script can not be executed because the Datacenter license is not installed, telemetry is not"
                      " activated or iDRAC firmware does not support Telemetry.")
        logging.error(pformat(json.loads(response.text).get("error", {}).get("@Message.ExtendedInfo", [{}])[0].get("Message", "")))
        sys.exit(0)


def get_event_service_properties(idrac_ip: str, idrac_username: str, idrac_password: str):
    """
    Prints the results from EventService. This is useful for determining the various options available on the host.
    Example output:

    {'@odata.context': '/redfish/v1/$metadata#EventService.EventService',
     '@odata.id': '/redfish/v1/EventService',
     '@odata.type': '#EventService.v1_5_0.EventService',
     'Actions': {'#EventService.SubmitTestEvent': {'EventType@Redfish.AllowableValues': ['Alert'],
                                                   'target': '/redfish/v1/EventService/Actions/EventService.SubmitTestEvent'}},
     'DeliveryRetryAttempts': 3,
     'DeliveryRetryIntervalSeconds': 5,
     'Description': 'Event Service represents the properties for the service',
     'EventFormatTypes': ['Event', 'MetricReport'],
     'EventFormatTypes@odata.count': 2,
     'EventTypesForSubscription': ['Alert', 'MetricReport', 'Other'],
     'EventTypesForSubscription@odata.count': 3,
     'Id': 'EventService',
     'Name': 'Event Service',
     'SMTP': {'Authentication': 'None',
              'ConnectionProtocol': 'StartTLS',
              'FromAddress': '',
              'Password': None,
              'Port': 25,
              'ServerAddress': '0.0.0.0',
              'Username': ''},
     'SSEFilterPropertiesSupported': {'EventFormatType': True,
                                      'EventType': True,
                                      'MessageId': True,
                                      'MetricReportDefinition': True,
                                      'OriginResource': True,
                                      'RegistryPrefix': False,
                                      'ResourceType': True,
                                      'SubordinateResources': False},
     'ServerSentEventUri': '/redfish/v1/SSE',
     'ServiceEnabled': True,
     'Status': {'Health': 'OK', 'HealthRollup': 'OK', 'State': 'Enabled'},
     'Subscriptions': {'@odata.id': '/redfish/v1/EventService/Subscriptions'}}

    :param idrac_ip: IP address of the target iDRAC
    :param idrac_username: Username of the target iDRAC
    :param idrac_password: Password of the target iDRAC
    """
    response = requests.get('https://%s/redfish/v1/EventService' % idrac_ip, verify=False,
                            auth=(idrac_username, idrac_password))
    logging.info("GET command output for EventService URI\n")
    pprint(response.json())


def get_event_service_subscriptions(idrac_ip: str, idrac_username: str, idrac_password: str, subscription_detail: str):
    """
    Prints a list of subscriptions from a target iDRAC

    :param idrac_ip: IP address of the target iDRAC
    :param idrac_username: Username of the target iDRAC
    :param idrac_password: Password of the target iDRAC
    :param subscription_detail: This should be either simple or detailed. This determines the level of subscription
                                detail to print for the user. Passed as the argument to --get-subscriptions
    """

    response = requests.get('https://%s/redfish/v1/EventService/Subscriptions' % idrac_ip, verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()
    if not data["Members"]:
        logging.info("No subscriptions found for iDRAC %s" % idrac_ip)
        sys.exit(0)
    else:
        logging.info("Subscriptions found for iDRAC ip %s" % idrac_ip)
    for subscription in data["Members"]:
        print(subscription['@odata.id'])
        if subscription_detail == "detailed":
            response = requests.get('https://%s%s' % (idrac_ip, subscription['@odata.id']), verify=False,
                                    auth=(idrac_username, idrac_password))
            logging.info("Detailed information for subscription %s\n" % subscription['@odata.id'])
            # TODO - This is missing a guard for a failed request
            pprint(response.json())


def delete_subscriptions(idrac_ip: str, idrac_username: str, idrac_password: str, subscription_uri: str):
    """
    Deletes a subscription from a target iDRAC

    :param idrac_ip: IP address of the target iDRAC
    :param idrac_username: Username of the target iDRAC
    :param idrac_password: Password of the target iDRAC
    :param subscription_uri: The URI of the subscription you want to delete. Has format
                             /redfish/v1/EventService/Subscriptions/c1a71140-ba1d-11e9-842f-d094662a05e6
    """
    url = "https://%s%s" % (idrac_ip, subscription_uri)
    headers = {'content-type': 'application/json'}
    response = requests.delete(url, headers=headers, verify=False, auth=(idrac_username, idrac_password))
    if response.__dict__["status_code"] == 200:
        logging.info("DELETE command succeeded in deleting subscription %s" % args["delete"])
    else:
        logging.error("FAIL - DELETE command failed and returned status code %s, error is %s" %
                      (response.__dict__["status_code"], response.__dict__["_content"]))
        sys.exit(0)


def scp_set_idrac_attribute(idrac_ip: str, idrac_username: str, idrac_password: str):
    """
    This function is used in the event that a server does not support the PATCH command for iDRAC. In this case, we
    must instead use a server configuration profile (SCP) to update the configuration.

    :param idrac_ip: IP address of the target iDRAC
    :param idrac_username: Username of the target iDRAC
    :param idrac_password: Password of the target iDRAC
    """

    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration' % idrac_ip
    payload = {
        "ImportBuffer": "<SystemConfiguration><Component FQDD=\"iDRAC.Embedded.1\"><Attribute Name=\"IPMILan.1#AlertEnable\">Enabled</Attribute></Component></SystemConfiguration>",
        "ShareParameters": {"Target": "All"}}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,
                             auth=(idrac_username, idrac_password))
    d = str(response.__dict__)
    try:
        z = re.search("JID_.+?,", d).group()
    except:
        logging.error("\n- FAIL: detailed error message: {0}".format(response.__dict__['_content']))
        sys.exit(0)

    job_id = re.sub("[,']", "", z)
    if response.status_code != 202:
        logging.info("FAIL, status code not 202\n, code is: %s" % response.status_code)
        sys.exit(0)
    else:
        logging.info("%s successfully created for ImportSystemConfiguration method\n" % job_id)

    response_output = response.__dict__
    job_id = response_output["headers"]["Location"]
    job_id = re.search("JID_.+", job_id).group()

    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id),
                           auth=(idrac_username, idrac_password), verify=False)
        status_code = req.status_code
        data = req.json()
        message_string = data[u"Messages"]
        final_message_string = str(message_string)
        if status_code == 202 or status_code == 200:
            pass
            time.sleep(1)
        else:
            logging.error("Query job ID command failed, error code is: %s" % status_code)
            sys.exit(0)
        if "failed" in final_message_string or "completed with errors" in final_message_string or\
                "Not one" in final_message_string:
            logging.error("FAIL. Detailed job message is: %s" % data[u"Messages"])
            sys.exit(0)
        elif "Successfully imported" in final_message_string or "completed with errors" in final_message_string or\
                "Successfully imported" in final_message_string:
            logging.info("Job ID = " + data[u"Id"])
            logging.info("Name = " + data[u"Name"])
            try:
                logging.info("Message = \n" + message_string[0][u"Message"])
            except:
                logging.info("Message = %s\n" % message_string[len(message_string) - 1][u"Message"])
            break
        elif "No changes" in final_message_string:
            logging.info("Job ID = " + data[u"Id"])
            logging.info("Name = " + data[u"Name"])
            try:
                logging.info("Message = " + message_string[0][u"Message"])
            except:
                logging.info("Message = %s" % message_string[len(message_string) - 1][u"Message"])
                sys.exit(0)
            break
        else:
            logging.info("Job not marked completed, current status is: %s" % data[u"TaskState"])
            logging.info("Message: %s\n" % message_string[0][u"Message"])
            time.sleep(1)
            continue


def get_set_ipmi_alert_idrac_setting(idrac_ip: str, idrac_username: str, idrac_password: str):
    """
    Enables IPMI alerts for the target iDRAC

    :param idrac_ip: IP address of the target iDRAC
    :param idrac_username: Username of the target iDRAC
    :param idrac_password: Password of the target iDRAC
    """

    response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip, verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()
    while True:
        try:
            attributes_dict = data['Attributes']
        except:
            logging.warning("WARNING, iDRAC version detected does not support PATCH to set iDRAC attributes, executing "
                            "Server Configuration Profile feature set iDRAC attribute \"IPMILan.1#AlertEnable\" "
                            "locally\n")
            scp_set_idrac_attribute(idrac_ip, idrac_username, idrac_password)
            break

        logging.info("Checking current value for iDRAC attribute \"IPMILan.1.AlertEnable\"")

        if attributes_dict["IPMILan.1.AlertEnable"] == "Disabled":
            logging.info("Current value for iDRAC attribute \"IPMILan.1.AlertEnable\" is set to Disabled, "
                         "setting value to Enabled")
            payload = {"Attributes": {"IPMILan.1.AlertEnable": "Enabled"}}
            headers = {'content-type': 'application/json'}
            url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip
            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,
                                      auth=(idrac_username, idrac_password))
            status_code = response.status_code
            if status_code == 200:
                logging.info("PATCH command succeeded and set iDRAC attribute \"IPMILan.1.AlertEnable\" to enabled")
            else:
                logging.error("FAIL. PATCH command failed to set iDRAC attribute \"IPMILan.1.AlertEnable\" to enabled")
                sys.exit(0)
            response = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Attributes' % idrac_ip,
                                    verify=False, auth=(idrac_username, idrac_password))
            data = response.json()
            attributes_dict = data['Attributes']
            if attributes_dict["IPMILan.1.AlertEnable"] == "Enabled":
                logging.info("iDRAC attribute \"IPMILan.1.AlertEnable\" successfully set to Enabled")
                break
            else:
                logging.error("FAIL. iDRAC attribute \"IPMILan.1.AlertEnable\" not set to Enabled")
                sys.exit(0)
        else:
            logging.warning("Current value for iDRAC attribute \"IPMILan.1.AlertEnable\" already set to Enabled, "
                            "ignore PATCH command")
            break


def create_post_subscription(idrac_ip: str, idrac_username: str, idrac_password: str, destination_url: str,
                             event_type: str, format_type: str):
    """
    Creates a subscription to the target iDRAC based on HTTP POST

    :param idrac_ip: IP address of the target iDRAC
    :param idrac_username: Username of the target iDRAC
    :param idrac_password: Password of the target iDRAC
    :param destination_url: The URL of the target endpoint to which you want the iDRAC logs to be sent
    :param event_type: The type of event for which you want to send data. Valid values include StatusChange,
                       ResourceUpdated, ResourceAdded, ResourceRemoved, Alert, and MetricReport.
    :param format_type: The format in which you want to receive the subscription data. This can be Event, MetricReport,
                        or None
    """

    url = "https://%s/redfish/v1/EventService/Subscriptions" % idrac_ip
    headers = {'content-type': 'application/json'}
    payload = {"Destination": destination_url, "EventTypes": [event_type], "Context": "root", "Protocol": "Redfish",
               "EventFormatType": format_type}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,
                             auth=(idrac_username, idrac_password))
    if response.__dict__["status_code"] == 201:
        logging.info("POST command succeeded, status code 201 returned, subscription successfully set for EventService")
    else:
        logging.error("FAIL. POST command failed, status code %s returned, error is %s" %
                      (response.__dict__["status_code"], response.__dict__["_content"]))
        sys.exit(0)


def create_sse_subscription(idrac_ip: str, idrac_username: str, idrac_password: str):
    """
    Creates an SSE connection to a target. This code is mostly meant as a simple demonstration of how to create a
    simple SSE client. It will print all output to console. Currently, it will grab all reports and I have not added
    the ability to filter to a specific report.

    :param idrac_ip: IP address of the target iDRAC
    :param idrac_username: Username of the target iDRAC
    :param idrac_password: Password of the target iDRAC
    """
    logging.info("Starting SSE client...")
    messages = SSEClient("https://%s/redfish/v1/SSE?$filter=EventFormatType eq MetricReport" % idrac_ip,
                         headers={'content-type': 'application/json'},
                         verify=False,
                         auth=(idrac_username, idrac_password))
    for sse_event in messages:
        pprint(sse_event.data)


def submit_test_event(idrac_ip: str, idrac_username: str, idrac_password: str, destination_url: str,
                      event_type: str, message_id: str):
    """
    Create and send a test event

    :param idrac_ip: IP address of the target iDRAC
    :param idrac_username: Username of the target iDRAC
    :param idrac_password: Password of the target iDRAC
    :param destination_url: The URL of the target endpoint to which you want the iDRAC logs to be sent
    :param event_type: The type of event for which you want to send data. Valid values include StatusChange,
                       ResourceUpdated, ResourceAdded, ResourceRemoved, Alert, and MetricReport.
    :param message_id: ID of the test message
    """
    payload = {"Destination": destination_url, "EventTypes": event_type, "Context": "Root", "Protocol": "Redfish",
               "MessageId": message_id}
    url = "https://%s/redfish/v1/EventService/Actions/EventService.SubmitTestEvent" % idrac_ip
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,
                             auth=(idrac_username, idrac_password))
    if response.__dict__["status_code"] == 201:
        logging.info("POST command succeeded, status code 201 returned, event type \"%s\" successfully sent to " 
                     "destination \"%s\"" % (event_type, destination_url))
    else:
        logging.error("FAIL. POST command failed, status code %s returned, error is %s" %
                      (response.__dict__["status_code"], response.__dict__["_content"]))
        sys.exit(0)


def print_examples():
    """
    Print program examples and exit
    """
    print(
        '\'SubscriptionManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin --get-subscriptions simple\' - Get current subscription URIs and details.\n'
        '\'SubscriptionManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin --create-subscription --destination-url https://192.168.0.130 --event-type Alert --format-type MetricReport\' - Create a MetricReport, POST-based, subscription for alert events which will use 192.168.0.130 Redfish event listener.\n'
        '\'SubscriptionManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin --delete /redfish/v1/EventService/Subscriptions/c1a71140-ba1d-11e9-842f-d094662a05e6\' - Delete a subscription\n'
        '\'SubscriptionManagementREDFISH.py -ip 192.168.0.120 -u root -p calvin --create-subscription --subscription-type SSE\' - Create an SSE client and log received events to console.')
    sys.exit(0)


if not args["script_examples"]:
    if not args["idrac_ip"] or not args["idrac_username"] or not args["idrac_password"]:
        logging.error("When not using the --script-examples argument -ip, -u, and -p are required arguments.")
        sys.exit(0)
    else:
        validate_telemetry_support(args["idrac_ip"], args["idrac_username"], args["idrac_password"])

if args["subscription_type"] == 'SSE':
    try:
        from sseclient import SSEClient
    except ModuleNotFoundError:
        print("To use the SSE functionality you need the library sseclient. Install it with `pip install sseclient`")
        sys.exit(0)


if __name__ == "__main__":

    if args["script_examples"]:
        print_examples()
    elif args["get_event_properties"]:
        get_event_service_properties(args["idrac_ip"], args["idrac_username"], args["idrac_password"])
    elif args["get_subscriptions"]:
        get_event_service_subscriptions(args["idrac_ip"], args["idrac_username"], args["idrac_password"],
                                        args["get_subscriptions"])
    elif args["create_subscription"] and args["destination_url"] and args["event_type"] and args["format_type"] \
            and args["subscription_type"] == 'POST':
        get_set_ipmi_alert_idrac_setting(args["idrac_ip"], args["idrac_username"], args["idrac_password"])
        create_post_subscription(args["idrac_ip"], args["idrac_username"], args["idrac_password"],
                                 args["destination_url"], args["event_type"], args["format_type"])
    elif args["create_subscription"] and args["destination_url"] and args["subscription_type"] == 'SSE':
        if args["format_type"] and args["format_type"] != "MetricReport":
            logging.error("The format type when using SSE can only be MetricReport.")
            sys.exit(0)
        create_sse_subscription(args["idrac_ip"], args["idrac_username"], args["idrac_password"])
    elif args["test_event"] and args["destination_url"] and args["event_type"] and args["message_type"]:
        submit_test_event(args["idrac_ip"], args["idrac_username"], args["idrac_password"],
                          args["destination_url"], args["event_type"], args["message_id"])
    elif args["delete"]:
        delete_subscriptions(args["idrac_ip"], args["idrac_username"], args["idrac_password"], args["delete"])
    else:
        print_examples()
