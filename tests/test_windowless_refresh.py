"""The scheduled process must hide console children, not only Python itself."""
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

import scheduled_refresh


@unittest.skipUnless(sys.platform == 'win32', 'Windows console behavior')
class WindowlessRefreshTests(unittest.TestCase):
    def test_child_commands_receive_no_window_without_losing_options(self):
        configure = getattr(scheduled_refresh, 'configure_windowless_subprocesses', None)
        self.assertTrue(callable(configure), 'scheduled runner must hide its child commands')
        calls = []

        class RecordingPopen:
            def __init__(self, *args, **kwargs):
                calls.append((args, kwargs))

        with patch.object(subprocess, 'Popen', RecordingPopen):
            configure()
            installed = subprocess.Popen
            configure()
            self.assertIs(subprocess.Popen, installed, 'configuration must be idempotent')
            subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                             cwd=os.getcwd())
        args, options = calls[0]
        self.assertEqual(args, (['git', 'rev-parse', 'HEAD'],))
        self.assertEqual(options['creationflags'], subprocess.CREATE_NO_WINDOW |
                         subprocess.CREATE_NEW_PROCESS_GROUP)
        self.assertEqual(options['stdout'], subprocess.PIPE)
        self.assertEqual(options['cwd'], os.getcwd())

    def test_real_console_child_has_no_console_and_keeps_output(self):
        configure = getattr(scheduled_refresh, 'configure_windowless_subprocesses', None)
        self.assertTrue(callable(configure), 'scheduled runner must hide its child commands')
        # Keep the installed policy scoped to this test, as it is to the task process.
        with patch.object(subprocess, 'Popen', subprocess.Popen):
            configure()
            result = subprocess.run([sys.executable, '-c',
                'import ctypes; print(ctypes.windll.kernel32.GetConsoleWindow())'],
                capture_output=True, text=True, check=True, timeout=10)
        self.assertEqual(result.stdout.strip(), '0')


if __name__ == '__main__':
    unittest.main()
