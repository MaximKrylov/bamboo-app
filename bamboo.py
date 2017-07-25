# pylint: disable-all
import re
import requests

# ------------ Information ---------------
LOGIN = ''  # login
PASSWORD = ''  # password
PLAN = 'CLOUD-UTOIC42'  # uitests
VERSION = 'latest'  # running version
# ----------------------------------------


def get_changes(session, plan, version):
    url = 'https://www.intapp.com/bamboo/rest/api/latest/result/{}-{}?expand=changes.change.files'
    response = session.get(url.format(plan, version), headers={
        'Accept': 'application/json'
    })
    results = {}

    if response.status_code != 200:
        raise Exception(response.reason)

    changes = response.json()['changes']['change']

    for change in changes:
        author = re.search(r'<(.+)>', change['author']).group(0)

        for item in change['files']['file']:
            if '.feature' in item['name']:
                feature = item['name']
                if author in results:
                    if feature in results[author]:
                        continue
                    results[author].append(feature)
                else:
                    results[author] = [feature]

    return results


def get_jobs(session, plan):
    url = 'https://www.intapp.com/bamboo/rest/api/latest/search/jobs/{}?max-result=100'
    response = session.get(url.format(plan), headers={
        'Accept': 'application/json'
    })
    results = []

    if response.status_code != 200:
        raise Exception(response.reason)

    jobs = response.json()['searchResults']

    for job in jobs:
        results.append({
            'id': job['id'],
            'name': job['searchEntity']['jobName']
        })

    return results


def get_all_successful_tests(session, job_id, version):
    url = 'https://www.intapp.com/bamboo/rest/api/latest/result/{}-{}?expand=testResults.successfulTests.testResult'
    response = session.get(url.format(job_id, version), headers={
        'Accept': 'application/json'
    })
    results = []

    if response.status_code != 200:
        raise Exception(response.reason)

    successful_tests = response.json(
    )['testResults']['successfulTests']['testResult']

    for test in successful_tests:
        results.append({
            'feature': test['className'],
            'scenario': test['methodName']
        })

    return results


def get_all_failed_tests(session, job_id, version):
    url = 'https://www.intapp.com/bamboo/rest/api/latest/result/{}-{}?expand=testResults.failedTests.testResult'
    response = session.get(url.format(job_id, version), headers={
        'Accept': 'application/json'
    })
    results = []

    if response.status_code != 200:
        raise Exception(response.reason)

    failed_tests = response.json(
    )['testResults']['failedTests']['testResult']

    for test in failed_tests:
        results.append({
            'feature': test['className'],
            'scenario': test['methodName']
        })

    return results


def get_new_failed_tests(session, job_id, version):
    url = 'https://www.intapp.com/bamboo/rest/api/latest/result/{}-{}?expand=testResults.newFailedTests.testResult'
    response = session.get(url.format(job_id, version), headers={
        'Accept': 'application/json'
    })
    results = []

    if response.status_code != 200:
        raise Exception(response.reason)

    failed_tests = response.json(
    )['testResults']['newFailedTests']['testResult']

    for test in failed_tests:
        results.append({
            'feature': test['className'],
            'scenario': test['methodName']
        })

    return results


def get_feature_specflow_path(feature):
    return re.sub('Source/Wilco.UITest/', '', feature).replace('/', '.').replace('.feature', 'Feature')


def get_printable_test(status, job, feature, scenario):
    return status + '\t' + job + '\t' + re.sub('Wilco.UITest.Spec.', '', feature) + ' ' + scenario


SESSION = requests.Session()
SESSION.auth = (LOGIN, PASSWORD)

# ---------------------------------------------
# GETTING CHANGES
changes = get_changes(SESSION, PLAN, VERSION)
# ---------------------------------------------

jobs = get_jobs(SESSION, PLAN)

all_successful_tests = {}
all_failed_tests = {}
new_failed_tests = {}

job_index = 0

while job_index < len(jobs):
    try:
        job = jobs[job_index]

        # -------------------------------------------------------------------------------------
        # GETTING SUCCESSFUL TESTS
        all_successful_tests[job['id']] = get_all_successful_tests(SESSION, job['id'], VERSION)
        # GETTING ALL FAILED TESTS
        all_failed_tests[job['id']] = get_all_failed_tests(SESSION, job['id'], VERSION)
        # GETTING NEW FAILED TESTS
        new_failed_tests[job['id']] = get_new_failed_tests(SESSION, job['id'], VERSION)
        # -------------------------------------------------------------------------------------

        print str.format('Getting SUCC/FAIL tests from {}', job['name'])
        job_index += 1
    except:
        del jobs[job_index]

result = ''
endl = '\r\n'

for job in jobs:
    for test in all_successful_tests[job['id']]:
        result += get_printable_test('SUCCEED',
                                     job['name'], test['feature'], test['scenario']) + endl

    for test in all_failed_tests[job['id']]:
        result += get_printable_test('FAILED',
                                     job['name'], test['feature'], test['scenario']) + endl

# --------------------------------------------
results_file_name = 'all_results.txt'
results_file = open(str.format("./{}", results_file_name), "wb")
results_file.write(result.encode('UTF-8'))
print str.format('{} has been successfully created...', results_file_name)
# --------------------------------------------

result = ''

for job in jobs:
    for test in new_failed_tests[job['id']]:
        result += re.sub('Wilco.UITest.Spec.', '', test['feature']) + ' ' + test['scenario'] + endl

# --------------------------------------------
results_file_name = 'new_failures.txt'
results_file = open(str.format("./{}", results_file_name), "wb")
results_file.write(result.encode('UTF-8'))
print str.format('{} has been successfully created...', results_file_name)
# --------------------------------------------


result = ''

for author in changes:
    result += author + endl
    feature_index = 0

    while feature_index < len(changes[author]):
        author_feature = get_feature_specflow_path(
            changes[author][feature_index])
        found = False

        for job in jobs:
            for test in all_successful_tests[job['id']]:
                if author_feature == test['feature']:
                    found = True
                    result += get_printable_test(
                        'SUCCEED', job['name'], test['feature'], test['scenario']) + endl

            for test in all_failed_tests[job['id']]:
                if author_feature == test['feature']:
                    found = True
                    result += get_printable_test(
                        'FAILED', job['name'], test['feature'], test['scenario']) + endl

        if found:
            del changes[author][feature_index]
        else:
            feature_index += 1

    if len(changes[author]) > 0:
        for feature in changes[author]:
            result += 'NOT FOUND' + '\t' + feature + endl

# --------------------------------------------
results_file_name = 'last_results.txt'
results_file = open(str.format("./{}", results_file_name), "wb")
results_file.write(result.encode('UTF-8'))
print str.format('{} has been successfully created...', results_file_name)
# --------------------------------------------
