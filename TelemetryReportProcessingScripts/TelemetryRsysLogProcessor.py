#
# TelemetryRsysLogProcessor.py Python script to reconstruct the Telemetry reports from Rsyslogfiles.
#
#
#
# _author_ = Sankunny Jayaprasad <Sankunny.Jayaprasad@Dell.com>
# _version_ = 1.0
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
import glob
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from logging import handlers
from pyparsing import *

parser = argparse.ArgumentParser(description="Python script to reconstruct the Telemetry reports from Rsyslogfiles.")
parser.add_argument('-s', help='Folder path to Rsyslog files. Example \'/var/log/**/*.log\'', required=True)
parser.add_argument('-d', help='Destination folder where the JSON reports files to be saved.', default=os.getcwd(),
                    required=False)
parser.add_argument('script_examples', action="store_true",
                    help="'python TelemetryRsysLogProcessor.py -s /var/log/**/*.log -d /tmp/Rsyslogs/' to process the Rsyslogfiles "
                         "'from /var/log/**/ folder and save them under /tmp/Rsyslogs/'. The script will continue to execute and process all new messages.' "
                         "Kill the scriot to stop processing. The log files will be rotated every day.")
args = vars(parser.parse_args())

LOG_PATH = os.path.join(os.getcwd(), '{}_{}.txt'.format('MultiThreadRsyslogProcessor_log',
                                                        (datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))))
file_handler = logging.handlers.TimedRotatingFileHandler(filename=LOG_PATH, when='d', interval=1, backupCount=0,
                                                         encoding=None, delay=False, utc=False, atTime=None)
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [file_handler, stdout_handler]
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s',
                    handlers=handlers)  # set logging level to DEBUG to have complete processing logs
logger = logging.getLogger('RsysLogProcessor')

rsyslog_path = args["s"]
destination_folder = args["d"]


class TelemetryRsyslogParser(object):
    def __init__(self):
        self.__pattern = self.generate_Rsyslog_message_pattern()

    def generate_Rsyslog_message_pattern(self):
        ints = Word(nums)
        timestamp = Combine(ints + "-" + ints + "-" + ints + 'T' + ints + ":" + ints + ":" + ints + "." + ints +
                            "-" + ints + ":" + ints)
        hostname = Word(alphas + nums + "-" + ".")  # pyparsing_common.ipv4_address
        appname = Word(alphas + "-" + nums) + Suppress(":")
        context = Suppress("#") + Word(alphas) + Suppress("#") + Suppress(":") + Word(nums) + "-" + Word(
            nums) + "-" + Word(nums) + Suppress(":")
        message = Regex(".*")
        return timestamp + hostname + appname + context + message

    def parse(self, line):
        payload = {}
        try:
            parsed = self.__pattern.parseString(line)
            payload["time_stamp"] = parsed[0]
            payload["host_name"] = parsed[1]
            payload["idrac_name"] = parsed[2]
            payload["index"] = parsed[4]
            payload["chunks_count"] = parsed[6]
            payload["chunkId"] = parsed[8]
            payload["message"] = parsed[9]
        except:
            logger.exception("Unable to parse line '{}'".format(line))
        return payload

    def save_telemetry_report(self, idrac_name, report, report_index):
        try:
            telemetry_report = json.loads("".join(report))
            self.write_telemetry_report_json(idrac_name, telemetry_report, report_index)
            return True
        except Exception as e:
            logger.exception(str(e))
            return False

    def write_telemetry_report_json(self, idrac_name, report, report_index):
        id = report.get('Id', 'UnknownId')
        report_folder = os.path.join(destination_folder, idrac_name)
        report_sequence = report.get('ReportSequence', '00000')
        report_timestamp = report.get('Timestamp', '00000')
        file_name = str("_".join([id, report_sequence, report_timestamp.replace(":", "-")])) + ".json"
        if not os.path.exists(report_folder):
            os.makedirs(report_folder)
        logging.debug("Saving the Telemetry report {} for iDRAC {}".format(file_name, idrac_name))
        with open(os.path.join(report_folder, file_name), "w") as file:
            file.write(json.dumps(report))

    def monitor_Rsyslog_files(self, filename):
        file = open(filename, 'r')
        st_results = os.stat(filename)
        st_size = st_results[6]
        file_modified_time = time.time()
        file.seek(st_size)
        currently_processing_index = -1
        reports_dict = {}
        raw_report = []
        while 1:
            where = file.tell()
            line = file.readline()
            if not line:
                time.sleep(1)
                file.seek(where)
                if time.time() - file_modified_time > 60:
                    file.close()
                    file = open(filename, 'r')
            else:
                file_modified_time = time.time()
                fields = self.parse(line)
                if not fields:
                    continue  # ignore any lines not matching the pattern
                idrac_name = fields.get("idrac_name")
                current_report_index = int(fields.get('index', -1))
                time_stamp = fields.get("time_stamp")
                chunk_id = int(fields.get("chunkId", 0))
                chunks_count = int(fields.get("chunks_count", 1))
                raw_report = [] if currently_processing_index != current_report_index else raw_report
                logger.debug("Processing Time stamp {}  and Index: {}".format(time_stamp, current_report_index))
                if idrac_name not in reports_dict:
                    reports_dict.update({idrac_name: dict()})
                current_report_message = reports_dict[idrac_name].get(current_report_index, dict())
                current_report_message.update({chunk_id: fields.get("message", '')})
                reports_dict[idrac_name][current_report_index] = current_report_message
                if len(reports_dict[idrac_name][current_report_index]) == int(chunks_count):
                    for chunk_ids in sorted(reports_dict[idrac_name][current_report_index].keys()):
                        raw_report.append(reports_dict[idrac_name][current_report_index][chunk_ids])
                if raw_report and self.save_telemetry_report(idrac_name, raw_report, current_report_index):
                    logger.debug("Finished processing Index: {} of idrac {}".format(current_report_index, idrac_name))
                    del reports_dict[idrac_name][current_report_index]
                time.sleep(0.001)


if __name__ == "__main__":
    parser = TelemetryRsyslogParser()
    threads = list()
    monitoring_log_files = []
    while True:
        rsys_logs = glob.glob(rsyslog_path, recursive=True)
        idrac_rsyslogs = list(filter(lambda x: ('idrac' in str(x).lower() and str(x).endswith('.log')), rsys_logs))
        for log_file in idrac_rsyslogs:
            try:
                if log_file in monitoring_log_files:
                    continue
                logger.info(("Processing file '{}'".format(log_file)).center(100, '*'))
                x = threading.Thread(target=parser.monitor_Rsyslog_files, args=(log_file,), name=log_file)
                threads.append(x)
                x.start()
                monitoring_log_files.append(log_file)
            except Exception as e:
                if log_file in monitoring_log_files: monitoring_log_files.remove(log_file)
                logger.error("Error occurred while processing '{}'  and error is {}".format(log_file, e))
        time.sleep(2)
