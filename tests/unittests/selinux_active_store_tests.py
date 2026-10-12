import bz2
import io
import os
import struct
import tarfile
import tempfile
import unittest
from pathlib import Path

from sos.cleaner.archive_residual import (ReportArchiveResidualError,
                                          ReportArchiveResidualValidator)
from sos.cleaner.mapping_manifest import SoSMappingManifest
from sos.cleaner.report_residual import (ReportTreeResidualError,
                                         ReportTreeResidualValidator)
from sos.cleaner.tree import ReportTreeSanitizer
from sos.cleaner.selinux_cil import DirectCil
from sos.cleaner.selinux_store import active_store_module_path, active_store_path


class SelinuxActiveStoreTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)

    def tearDown(self):
        self.work.cleanup()

    def module(self, name='base', priority='100', extension=b'pp', direct=False):
        path = (self.root / 'var/lib/selinux/targeted/active/modules' /
                priority / name)
        path.mkdir(parents=True)
        (path / 'lang_ext').write_bytes(extension)
        (path / 'cil').write_bytes(bz2.compress(b'(type safe_t)\n'))
        if not direct:
            (path / 'hll').write_bytes(bz2.compress(b'PP\x00payload'))
        return path

    def classify(self, path, leaf):
        parent = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        fd = os.open(leaf, os.O_RDONLY, dir_fd=parent)
        try:
            observed = os.fstat(fd)
            return ReportTreeSanitizer._selinux_store_policy(
                tuple((path / leaf).relative_to(self.root).parts),
                observed, fd, parent)
        finally:
            os.close(fd)
            os.close(parent)

    def test_path_classifier_is_explicit(self):
        valid = ('var', 'lib', 'selinux', 'targeted', 'active', 'modules',
                 '100', 'base', 'hll')
        self.assertEqual(active_store_module_path(valid), 'hll')
        self.assertEqual(active_store_module_path(valid[:-1] + ('cil',)),
                         'cil')
        self.assertEqual(active_store_module_path(valid[:-1] +
                                                  ('lang_ext',)), 'lang_ext')
        for path in (
                valid[:-3] + ('000', 'base', 'hll'),
                valid[:-3] + ('100', 'base', 'other'),
                valid[:-3] + ('100', 'base', 'hll', 'extra'),
                ('var', 'lib', 'selinux', 'mls', 'active', 'modules',
                 '100', 'base', 'hll')):
            self.assertFalse(active_store_module_path(path))
        self.assertTrue(active_store_path(
            ('report', 'var', 'lib', 'selinux', 'targeted', 'active',
             'policy.kern'), 'policy.kern'))
        self.assertFalse(active_store_path(
            ('var', 'lib', 'selinux', 'targeted', 'active',
             'policy.kern.old'), 'policy.kern'))

    def test_direct_cil_path_classifier_is_explicit(self):
        valid = ('var', 'lib', 'selinux', 'targeted', 'active', 'modules',
                 '100', 'permissivedomains', 'cil')
        self.assertTrue(DirectCil.is_path(valid))
        self.assertTrue(DirectCil.is_path(('report',) + valid))
        for path in (
                valid[:-2] + ('100', 'permissivedomains', 'hll'),
                valid[:-3] + ('000', 'permissivedomains', 'cil'),
                valid[:-3] + ('100', 'permissivedomains', 'cil', 'extra'),
                ('var', 'lib', 'selinux', 'targeted', 'active',
                 'other-modules', '100', 'permissivedomains', 'cil'),
                ('var', 'lib', 'selinux', 'targeted', 'active', 'modules',
                 '100', 'permissivedomains', 'other')):
            with self.subTest(path=path):
                self.assertFalse(DirectCil.is_path(path))

    def test_paired_pp_hll_and_cil_are_classified(self):
        path = self.module()
        self.assertEqual(self.classify(path, 'hll'),
                         'selinux_module_hll_payload')
        self.assertEqual(self.classify(path, 'cil'),
                         'selinux_module_cil_cache')

    def test_language_marker_is_bounded_metadata(self):
        for extension in (b'pp', b'cil'):
            path = self.module(extension=extension,
                               direct=extension == b'cil')
            fd = os.open(path / 'lang_ext', os.O_RDONLY)
            parent = os.open(path, os.O_RDONLY)
            try:
                self.assertEqual(
                    ReportTreeSanitizer._selinux_store_policy(
                        tuple((path / 'lang_ext').relative_to(self.root).parts),
                        os.fstat(fd), fd, parent),
                    'selinux_module_language_metadata')
            finally:
                os.close(fd)
                os.close(parent)
            import shutil
            shutil.rmtree(path)

    def test_direct_cil_is_not_a_cache(self):
        path = self.module(extension=b'cil', direct=True)
        self.assertEqual(self.classify(path, 'cil'), 'selinux_direct_cil')

    def test_direct_cil_transform_is_bounded_and_retained(self):
        path = self.module(extension=b'cil', direct=True)
        self.assertTrue((path / 'cil').stat().st_nlink == 1)
        self.assertEqual(self.classify(path, 'cil'), 'selinux_direct_cil')

    def test_direct_cil_classifier_preserves_source_offset(self):
        path = self.module(extension=b'cil', direct=True)
        parent = os.open(path, os.O_RDONLY)
        fd = os.open('cil', os.O_RDONLY, dir_fd=parent)
        try:
            observed = os.fstat(fd)
            relative = tuple((path / 'cil').relative_to(self.root).parts)
            self.assertEqual(ReportTreeSanitizer._selinux_store_policy(
                relative, observed, fd, parent), 'selinux_direct_cil')
            self.assertNotEqual(os.read(fd, 1), b'')
        finally:
            os.close(fd)
            os.close(parent)

    def test_policy_header_and_metadata_classifiers(self):
        policy = self.root / 'var/lib/selinux/targeted/active'
        policy.mkdir(parents=True)
        header = (struct.pack('<2I', 0xf97cff8c, 8) + b'SE Linux' +
                  struct.pack('<4I', 31, 0, 8, 9))
        for name, data, expected in (
                ('policy.kern', header, 'selinux_binary_policy'),
                ('policy.linked', header, 'selinux_linked_policy'),
                ('modules_checksum', b'sha256:' + b'a' * 64 + b'\0',
                 'selinux_policy_store_metadata'),
                ('commit_num', struct.pack('<I', 7) + b'\0' * 28,
                 'selinux_policy_store_metadata')):
            path = policy / name
            path.write_bytes(data)
            fd = os.open(path, os.O_RDONLY)
            parent_fd = os.open(policy, os.O_RDONLY)
            try:
                self.assertEqual(
                    ReportTreeSanitizer._selinux_store_policy(
                        tuple(path.relative_to(self.root).parts),
                        os.fstat(fd), fd, parent_fd),
                    expected)
            finally:
                os.close(fd)
                os.close(parent_fd)

    def test_omission_counters_are_distinct_and_aggregate_once(self):
        sanitizer = object.__new__(ReportTreeSanitizer)
        sanitizer._summary = {
            'binary_files_omitted': 0,
            'files_processed': 0,
            'selinux_module_hll_payloads_omitted': 0,
            'selinux_module_cil_caches_omitted': 0,
            'selinux_binary_policies_omitted': 0,
            'selinux_linked_policies_omitted': 0,
            'selinux_policy_store_metadata_omitted': 0,
        }
        for category in ('selinux_module_hll_payload',
                         'selinux_module_cil_cache',
                         'selinux_binary_policy', 'selinux_linked_policy',
                         'selinux_policy_store_metadata'):
            sanitizer._omit_binary(category)
        self.assertEqual(sanitizer._summary['binary_files_omitted'], 5)
        self.assertEqual(
            sanitizer._summary['selinux_policy_store_metadata_omitted'], 1)

    def test_residual_paths_reject_tree_and_archive_reinjection(self):
        manifest = SoSMappingManifest({
            'hostnames': {}, 'domains': {}, 'ipv4': {}, 'ipv6': {},
            'mac': {}, 'emails': {}, 'usernames': {},
        })
        staged = self.root / 'staged'
        injected = staged / 'var/lib/selinux/targeted/active/modules/100/base/hll'
        injected.parent.mkdir(parents=True)
        injected.write_bytes(b'placeholder')
        with self.assertRaises(ReportTreeResidualError):
            ReportTreeResidualValidator(staged, manifest).validate()

        archive_path = self.root / 'reinjected.tar.xz'
        with tarfile.open(archive_path, 'w:xz') as archive:
            info = tarfile.TarInfo(injected.relative_to(staged).as_posix())
            info.size = len(b'placeholder')
            info.mode = 0o644
            info.mtime = 0
            archive.addfile(info, io.BytesIO(b'placeholder'))
        with self.assertRaises(ReportArchiveResidualError):
            ReportArchiveResidualValidator(archive_path, manifest).validate()


if __name__ == '__main__':
    unittest.main()
