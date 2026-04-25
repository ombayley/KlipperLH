#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: **Add Desc**.
"""
from src.core.config_models import MoonrakerConfig

def build():
    path = r"C:\Users\OllyBayley\Documents\Repos\personal\KlipperLH\src\device_config\default.yaml"
    config = MoonrakerConfig.from_yaml(path)
    print(config)

if __name__ == "__main__":
    build()