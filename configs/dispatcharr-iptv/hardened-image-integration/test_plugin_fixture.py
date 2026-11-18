"""Execute pinned upstream AppConfig with synthetic Django; no network/app DB."""
import ast
import hashlib
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

HERE=Path(__file__).resolve().parent

class PluginFixture(unittest.TestCase):
    def config(self):
        source=(HERE/'fixtures/plugin-apps-upstream.py').read_text()
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), '27b3b52fad5c8ca2aaf1912ac4165b1b5c58ac438cb489ce1d6182c55ef32679')
        signal=Mock()
        modules={name:types.ModuleType(name) for name in ['django','django.apps','django.db','django.db.models','django.db.models.signals','apps.plugins.loader','dispatcharr.app_initialization']}
        modules['django.apps'].AppConfig=object
        modules['django.db.models.signals'].post_migrate=signal
        modules['apps.plugins.loader'].PluginManager=Mock()
        modules['dispatcharr.app_initialization'].should_skip_initialization=lambda:False
        scope={'__name__':'apps.plugins.apps','__package__':'apps.plugins'}
        with patch.dict(sys.modules,modules):exec(compile(source,'pinned-plugin-apps.py','exec'),scope)
        instance=scope['PluginsConfig']()
        instance._setup_repo_refresh_schedule=Mock()
        instance._enqueue_startup_refresh=Mock()
        return instance,modules,signal

    def test_supported_optout_prevents_only_plugin_startup_wiring(self):
        obj,modules,signal=self.config()
        with patch.dict(sys.modules,modules),patch.dict(os.environ,{'DISPATCHARR_SKIP_PLUGIN_AUTODISCOVERY':'1'}):obj.ready()
        obj._enqueue_startup_refresh.assert_not_called()
        obj._setup_repo_refresh_schedule.assert_not_called()
        signal.connect.assert_not_called()
        modules['apps.plugins.loader'].PluginManager.get.assert_not_called()

    def test_without_optout_the_startup_path_is_reproduced(self):
        obj,modules,signal=self.config()
        with patch.dict(sys.modules,modules),patch.dict(os.environ,{'DISPATCHARR_SKIP_PLUGIN_AUTODISCOVERY':''}),patch.object(sys,'argv',['runtime_test.py']):obj.ready()
        obj._enqueue_startup_refresh.assert_called_once()
        obj._setup_repo_refresh_schedule.assert_called_once()
        signal.connect.assert_called_once()

    def test_fixture_sets_optout_before_any_django_bootstrap(self):
        tree=ast.parse((HERE/'runtime_test.py').read_text())
        bootstrap=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bootstrap')
        updates=[n for n in ast.walk(bootstrap) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='update' and n.args and isinstance(n.args[0],ast.Dict)]
        values={ast.literal_eval(k):v for n in updates for k,v in zip(n.args[0].keys,n.args[0].values)}
        self.assertEqual(ast.literal_eval(values['DISPATCHARR_SKIP_PLUGIN_AUTODISCOVERY']),'1')
        source=(HERE/'runtime_test.py').read_text()
        self.assertIn('app.conf.task_always_eager=False',source)
        self.assertIn("queues=['celery','default','dvr']",source)
        self.assertIn('plugin_task_registration_lost',source)
        self.assertIn('unrelated_plugin_schedule_present',source)

if __name__=='__main__':unittest.main()
