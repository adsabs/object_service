#!/usr/bin/env python
"""
Find and run the unit tests
"""

import unittest
import sys

if __name__ == '__main__':
    
    exit_failure = False

    for suite_name in ['unittests']:
        suite = unittest.TestLoader().discover(suite_name)
        results = unittest.TextTestRunner(verbosity=3).run(suite)
        
        if results.errors or results.failures:
            exit_failure = True

    if exit_failure:
        sys.exit(1)
