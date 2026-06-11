import json
import os
import warnings

import requests
from urllib3.exceptions import InsecureRequestWarning

TOKEN = os.environ.get('ADMIN_TOKEN')
OWNER_REPO = os.getenv('GITHUB_REPOSITORY')
ORG = OWNER_REPO.split('/')[0]
REPO = OWNER_REPO.split('/')[1]

warnings.simplefilter('ignore', InsecureRequestWarning)

print(f'This GitHub Action is running in the repository {OWNER_REPO}')

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28"
}


def get_default_branch():
    d_url = f'https://va.ghe.com/api/v3/repos/{ORG}/{REPO}'

    d_response = requests.get(d_url, headers=HEADERS, verify=False)
    d_response.raise_for_status()
    return d_response.json()['default_branch']


def general_settings(branch):
    g_url = f'https://va.ghe.com/api/v3/repos/{ORG}/{REPO}'

    update_data = {
        'default_branch': branch,
        'has_wiki': True,
        'has_issues': False,
        'allow_forking': False,
        'has_discussions': False,
        'has_projects': False,

        'allow_merge_commits': True,
        'allow_squash_merge': False,
        'allow_rebase_merge': False,

        'allow_update_branch': True,
        'allow_auto_merge': False,
        'delete_branch_on_merge': False,
    }

    g_response = requests.patch(g_url, json=update_data, headers=HEADERS, verify=False)

    if g_response.status_code == 200:
        print('General repository settings updated successfully.')
    else:
        print(f'Failed to update settings: {g_response.status_code}')
        print(g_response.json())


def branch_protection_settings(branch):
    b_url = f'https://va.ghe.com/api/v3/repos/{ORG}/{REPO}/branches/{branch}/protection'

    # Define the protection settings
    protection_settings = {
        "enforce_admins": False,
        "required_pull_request_reviews": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "require_last_push_approval": True,
            "bypass_pull_request_allowances": {}
        },
        "restrictions": {
            "users": [],
            "teams": []
        },

        "required_status_checks": {
            "strict": True,
            "contexts": [
                # List of required status checks here
            ]

        },
        "required_conversation_resolution": True,
        "restricts_bypassing_pull_request_requirements": False,
        "restrict_pushes": True,
        "block_creations": True,
        "allow_force_pushes": False,
        "allow_deletions": False
    }

    b_response = requests.put(b_url, json=protection_settings, headers=HEADERS, verify=False)

    if b_response.status_code == 200:
        print(f'{branch} branch protection rule created successfully.')
    else:
        print(f'Failed to create branch protection rule: {b_response.status_code}')
        print(b_response.json())


def get_branch_protection_rule_id(branch):
    query = '''
    {
      repository(owner: "%s", name: "%s") {
        branchProtectionRules(first: 10) {
          nodes {
            id
            pattern
          }
        }
      }
    }
    ''' % (ORG, REPO)

    response = requests.post(
        'https://va.ghe.com/api/graphql',
        json={'query': query},
        headers=HEADERS,
        verify=False
    )

    if response.status_code == 200:
        data = response.json()
        branch_nodes = data['data']['repository']['branchProtectionRules']['nodes']

        # Check if default_branch (master, main, default) are equal to the already named branch protection pattern
        for node in branch_nodes:
            if node['pattern'] == branch:
                return node['id']
    else:
        raise Exception(f'Query failed with status code {response.status_code} {response.text}')


def update_branch_protection_rule(r_id, pattern_name):
    mutation = '''
    mutation {
      updateBranchProtectionRule(input: {
        branchProtectionRuleId: "BRANCH_PROTECTION_RULE_ID", 
        pattern: "%s"
      }) {
        branchProtectionRule {
          id
          pattern
        }
      }
    }
    ''' % pattern_name

    mutation_with_id = mutation.replace("BRANCH_PROTECTION_RULE_ID", r_id)

    response = requests.post(
        'https://va.ghe.com/api/graphql',
        json={'query': mutation_with_id},
        headers=HEADERS,
        verify=False
    )

    if response.status_code == 200:
        print(f'{pattern_name} branch protection rule updated successfully.')
    else:
        raise Exception(f'Mutation failed with status code {response.status_code} {response.text}')


def get_all_repository_rulesets():
    url = f'https://va.ghe.com/api/v3/repos/{ORG}/{REPO}/rulesets'

    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        print('Repository Rulesets found successfully.')
        return [item['name'] for item in response.json()]

    else:
        print(f'Failed to get rulesets: {response.status_code}')
        print(response.text)
        return []


def create_ruleset():
    ruleset_payload = {
        "owner": ORG,
        "repo": REPO,
        "name": 'cm-primary-ruleset',
        "target": 'branch',
        "enforcement": 'active',
        # "bypass_actors": [
        #     {
        #         "actor_id": 234,
        #         "actor_type": 'Team',
        #         "bypass_mode": 'always'
        #     }
        # ],
        "conditions": {
            "ref_name": {
                "include": [
                    '~DEFAULT_BRANCH',
                    'refs/heads/integ*',

                ],
                "exclude": [
                ]
            }
        },
        "rules": [
            {
                "type": 'pull_request',
                "parameters": {
                    "dismiss_stale_reviews_on_push": True,
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_approving_review_count": 1,
                    "required_review_thread_resolution": True,
                    "allowed_merge_methods": ["merge"]
                },
            },
            {
                "type": 'non_fast_forward',
            },
        ],
    }

    # Serialize the ruleset_payload dictionary to a JSON formatted string
    ruleset_payload_json = json.dumps(ruleset_payload)

    url = f'https://va.ghe.com/api/v3/repos/{ORG}/{REPO}/rulesets'

    response = requests.post(url, headers=HEADERS, data=ruleset_payload_json)

    if response.status_code == 201:
        print("Ruleset created successfully.")
        # print(response.json())
    else:
        print(f"Failed to create ruleset: {response.status_code}")
        print(response.text)


if __name__ == "__main__":

    # Set general settings
    default_branch = get_default_branch()
    general_settings(default_branch)

    # Create master/main/default branch protection rules with asterisk
    branch_protection_settings(default_branch)
    rule_id = get_branch_protection_rule_id(default_branch)
    p_name = f'{default_branch}*'
    update_branch_protection_rule(rule_id, p_name)

    # Create integration branch protection rules
    branch_protection_settings(default_branch)
    rule_id = get_branch_protection_rule_id(default_branch)
    update_branch_protection_rule(rule_id, 'refs/heads/integ*')

    # Create Ruleset
    rulesets = get_all_repository_rulesets()
    if 'cm-primary-ruleset' not in rulesets:
        create_ruleset()
    else:
        print('Repository Ruleset already created.')
