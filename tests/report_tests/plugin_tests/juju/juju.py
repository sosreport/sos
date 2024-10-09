# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest


class JujuAgentConfScrubbedTest(StageTwoReportTest):
    """Ensure that agent conf is picked up and properly scrubbed

    :avocado: tags=stagetwo,scrub
    """

    sos_cmd = '-o juju'
    ubuntu_only = True
    files = [('agent.conf', '/var/lib/juju/agents/machine-0/agent.conf')]

    def test_unit_agent_conf_collected(self):
        self.assertFileCollected('/var/lib/juju/agents/machine-0/agent.conf')

    def test_unit_agent_conf_scrubbed(self):
        # Ensure that we scrubbed all passwords/secrets and the certificates
        check_text_scrub = [
            'cR97RRZheQgiLDrnkGxp8mlE',
            '111512798b7abbd4c2884e4de83d7989',
            'FaIBoxLXcbn6RghOnbZBh0r7v8a8PTdQWJ9fG5ey6OJLjTSd/Fk8',
            'MIIEEjCCAnqgAwIBAgIUXRUjAHgO+z8hifta518W/MvxZ9gwDQYJKoZIhvcNAQEL',
            'MIIEfjCCAuagAwIBAgIVANVl9irudWew6MVfGuzX85+5nW/OMA0GCSqGSIb3DQEB',
            'MIIEEjCCAnqgAwIBAgIUXRUjAHgO+z8hifta518W/MvxZ9gwDQYJKoZIhvcNAQEL',
            'MIIG/AIBADANBgkqhkiG9w0BAQEFAASCBuYwggbiAgEAAoIBgQC86bxFnYDYFssg',
            'MIIG/gIBADANBgkqhkiG9w0BAQEFAASCBugwggbkAgEAAoIBgQCfDj2vFQlsDlV4',
            'MIIEowIBAAKCAQEAsQmlk3a4OBmBNSy43bl66+rX+5sTsu+2yO93E/iGuzmGqX0t',
            'EB+ZKAkbUOMtPnhcFnZImnvxy658IPxGxr1ZoigInbnRr13h5/g=',
            'BjEUrba1VcDLW3fJQOxTH7R7wzM1bbu2p8R2ZnfUAWNXjr+mHuMc3mCnkEFL/X+/',
            'EB+ZKAkbUOMtPnhcFnZImnvxy658IPxGxr1ZoigInbnRr13h5/g=',
            'MK5DNKHKNIynw+tXbuJ2pQ==',
            'gGizOraTiFeIuvHMD3KATTLc',
            'L/x36ewmw1rsKYlFI5X/6qM6n5DIKU+IJGNj5VSYb1u3Q7TZZ1yF',
        ]
        for text in check_text_scrub:
            self.assertFileNotHasContent(
                '/var/lib/juju/agents/machine-0/agent.conf', text)
