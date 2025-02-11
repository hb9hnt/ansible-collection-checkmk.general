# Copyright: (c) 2023, Lars Getwan <lars.getwan@checkmk.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
    name: rules
    author: Lars Getwan (@lgetwan)
    version_added: "3.5.0"
    short_description: List rules
    description:
      - Returns a list of Rules
    options:
      ruleset:
        description: The ruleset name.
        required: True
      description_regex:
        description: A regex to filter for certain descriptions.
        required: False
        default: ""
      comment_regex:
        description: A regex to filter for certain comment stings.
        required: False
        default: ""
      server_url:
        description: URL of the Checkmk server.
        required: True
      site:
        description: Site name.
        required: True
      automation_user:
        description: Automation user for the REST API access.
        required: True
      automation_secret:
        description: Automation secret for the REST API access.
        required: True
      validate_certs:
        description: Whether or not to validate TLS cerificates.
        type: boolean
        required: False
        default: True
"""

EXAMPLES = """
- name: Get all rules of the ruleset host_groups
  ansible.builtin.debug:
    msg: "Rule: {{ item.extensions }}"
  loop: "{{
    lookup('checkmk.general.rules',
        ruleset='host_groups',
        server_url=server_url,
        site=site,
        automation_user=automation_user,
        automation_secret=automation_secret,
        validate_certs=False
        )
    }}"
  loop_control:
      label: "{{ item.id }}"

- name: actice_checks:http rules that match a certain description AND comment
  ansible.builtin.debug:
    msg: "Rule: {{ item.extensions }}"
  loop: "{{
    lookup('checkmk.general.rules',
        ruleset='actice_checks:http',
        description_regex='foo.*bar',
        comment_regex='xmas-edition',
        server_url=server_url,
        site=site,
        automation_user=automation_user,
        automation_secret=automation_secret,
        validate_certs=False
        )
    }}"
  loop_control:
      label: "{{ item.id }}"
"""

RETURN = """
  _list:
    description:
      - A list of all rules of a particular ruleset
    type: list
    elements: str
"""

import json
import re

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible_collections.checkmk.general.plugins.module_utils.lookup_api import (
    CheckMKLookupAPI,
)


class LookupModule(LookupBase):
    def run(self, terms, variables, **kwargs):
        regex_params = {}
        self.set_options(var_options=variables, direct=kwargs)
        ruleset = self.get_option("ruleset")
        regex_params["description"] = self.get_option("description_regex")
        regex_params["comment"] = self.get_option("comment_regex")
        server_url = self.get_option("server_url")
        site = self.get_option("site")
        user = self.get_option("automation_user")
        secret = self.get_option("automation_secret")
        validate_certs = self.get_option("validate_certs")

        site_url = server_url + "/" + site

        api = CheckMKLookupAPI(
            site_url=site_url,
            user=user,
            secret=secret,
            validate_certs=validate_certs,
        )

        parameters = {
            "ruleset_name": ruleset,
        }

        response = json.loads(api.get("/domain-types/rule/collections/all", parameters))

        if "code" in response:
            raise AnsibleError(
                "Received error for %s - %s: %s"
                % (
                    response.get("url", ""),
                    response.get("code", ""),
                    response.get("msg", ""),
                )
            )

        rule_list = response.get("value")

        for what, regex in regex_params.items():
            try:
                if regex:
                    rule_list = [
                        r
                        for r in rule_list
                        if re.search(
                            regex,
                            r.get("extensions", {}).get("properties", {}).get(what, ""),
                        )
                    ]
            except re.error as e:
                raise AnsibleError(
                    "Invalid regex for %s, pattern: %s, position: %s error: %s"
                    % (what, e.pattern, e.pos, e.msg)
                )

        return [rule_list]
