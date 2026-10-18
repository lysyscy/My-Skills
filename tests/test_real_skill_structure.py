"""Connect current shipped skill entries to the existing discovery contract.

This is a CI wiring check, not a complete YAML, semantic, or host acceptance test.
"""
import shutil

from test_skill_package import PackageFixture, ROOT


class RealSkillDiscoveryChecks(PackageFixture):
    def test_shipped_skills_satisfy_discovery_contract(self):
        shutil.rmtree(self.source / 'skills')
        shutil.copytree(ROOT / 'skills', self.source / 'skills', symlinks=True)
        expected = sorted(directory.name for directory in (ROOT / 'skills').iterdir()
                          if directory.is_dir() and (directory / 'SKILL.md').is_file())
        self.assertEqual(self.package.discover(), expected)
