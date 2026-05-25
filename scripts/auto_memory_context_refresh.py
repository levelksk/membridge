#!/usr/bin/env python3
"""Wrapper: auto_memory.py mini_context — refreshes mini context from memory"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auto_memory import main
sys.argv = ['auto_memory.py', 'mini_context']
main()
