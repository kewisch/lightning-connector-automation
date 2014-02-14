# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This class is taken from here, with a few modifications:
#   https://github.com/mozilla/mozmill-automation/blob/master/mozmill_automation/reports.py

from datetime import datetime
import os
import xml.dom.minidom

from mozmill.report import Report

class JUnitReport(Report):

    def __init__(self, report, testrun):
        Report.__init__(self, report)

        self.testrun = testrun

    def get_report(self, results):
        """ Generate JUnit XML report. """
        report = Report.get_report(self, results)

        report_type = str(self.testrun.report_type)
        time_start = datetime.strptime(report['time_start'], self.date_format)
        time_end = datetime.strptime(report['time_end'], self.date_format)

        doc = xml.dom.minidom.Document()
        testsuite_element = doc.createElement('testsuite')
        testsuite_element.setAttribute('name', report_type)
        testsuite_element.setAttribute('errors', "0")
        testsuite_element.setAttribute('failures', str(report['tests_failed']))
        testsuite_element.setAttribute('skips', str(report['tests_skipped']))
        testsuite_element.setAttribute('tests', str(len(report['results'])))
        testsuite_element.setAttribute('time', str((time_end - time_start).seconds))

        for result in report['results']:
            filename = result['filename']
            root_path = 'tests/%s' % report_type

            # replace backslashes with forward slashes
            filename = filename.replace('\\', '/')

            # strip temporary and common path elements, and strip trailing forward slash
            class_name = filename.partition(root_path)[2].lstrip('/')

            # strip the file extension
            class_name = os.path.splitext(class_name)[0]

            # replace periods with underscore to avoid them being interpreted as package seperators
            class_name = class_name.replace('.', '_')

            # replace path separators with periods to give implied package hierarchy
            class_name = class_name.replace('/', '.')

            testcase_element = doc.createElement('testcase')
            testcase_element.setAttribute('classname', str(class_name))
            testcase_element.setAttribute('name', str(result['name']).rpartition('::')[2])

            time = '0'
            if 'time_start' in result and 'time_end' in result:
                time = str((result['time_end'] - result['time_start']) / 1000)
            testcase_element.setAttribute("time", time)

            if 'skipped' in result and result['skipped']:
                skipped_element = doc.createElement('skipped')
                skipped_element.setAttribute('message', str(result['skipped_reason']))
                skipped_element.appendChild(doc.createTextNode(str(result['skipped_reason'])))
                testcase_element.appendChild(skipped_element)
            elif result['failed']:
                # If result['fails'] is not a list, make it a list of one
                result_failures = result['fails']
                if not isinstance(result_failures, list):
                    result_failures = [result_failures]

                failures = []
                for failure in result_failures:
                    # If the failure is a dict then return the appropriate exception/failure item or return an empty dict
                    failure_data = isinstance(failure, dict) and (
                        'exception' in failure and failure['exception'] or
                        'fail' in failure and failure['fail']) or {}
                    message = failure_data.get('message', 'Unknown failure.')
                    stack = failure_data.get('stack', 'Stack unavailable.')
                    failures.append({'message': message, 'stack': stack})

                if len(failures) == 1:
                    (message, body) = failures[0].values()
                else:
                    message = '%d failures' % len(failures)
                    body = '\n\n'.join(['Message: %s\nStack: %s' % (failure['message'], failure['stack']) for failure in failures])
                failed_element = doc.createElement("failure")
                failed_element.setAttribute('message', unicode(message).encode('ascii', 'xmlcharrefreplace'))
                failed_element.appendChild(doc.createTextNode(unicode(body).encode('ascii', 'xmlcharrefreplace')))
                testcase_element.appendChild(failed_element)
            testsuite_element.appendChild(testcase_element)

        doc.appendChild(testsuite_element)
        return doc.toxml(encoding='utf-8')

    def send_report(self, results, filename):
        """ Write JUnit report to file. """
        try:
            f = file(filename, 'w')
        except Exception, e:
            print "Printing results to '%s' failed (%s)." % (filename, e)
            return
        print >> f, results
        return
