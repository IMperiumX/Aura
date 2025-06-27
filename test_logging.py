#!/usr/bin/env python
"""
Test script to verify AsyncBufferedHandler and application.log creation
"""
import logging
import os
import time

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()


def test_logging():
    print("Testing AURA logging configuration...")

    # Get the performance logger
    logger = logging.getLogger("aura.performance")
    print(
        f"Logger configured with handlers: {[type(h).__name__ for h in logger.handlers]}"
    )
    print(f"Logger effective level: {logger.getEffectiveLevel()}")

    # Test different log levels
    print("Sending test logs...")
    logger.debug("Debug message from aura.performance")
    logger.info("Info message from aura.performance - should create application.log")
    logger.warning("Warning message from aura.performance")
    logger.error("Error message from aura.performance")

    # Check handlers
    for i, handler in enumerate(logger.handlers):
        print(f"Handler {i}: {type(handler).__name__}")
        if hasattr(handler, "target_handler"):
            print(f"  Target handler: {type(handler.target_handler).__name__}")
        if hasattr(handler, "flush"):
            print(f"  Flushing handler {i}...")
            handler.flush()

    print("Waiting 6 seconds for async processing...")
    time.sleep(6)

    # Check if application.log was created
    log_file = "logs/application.log"
    if os.path.exists(log_file):
        print(f"✅ SUCCESS: {log_file} exists!")
        # Show file size
        size = os.path.getsize(log_file)
        print(f"   File size: {size} bytes")

        # Show last few lines
        with open(log_file, "r") as f:
            lines = f.readlines()
            print(f"   Total lines: {len(lines)}")
            if lines:
                print("   Last few lines:")
                for line in lines[-3:]:
                    print(f"     {line.strip()}")
    else:
        print(f"❌ FAILURE: {log_file} does not exist")
        print("   Available log files:")
        if os.path.exists("logs"):
            for file in os.listdir("logs"):
                print(f"     - {file}")


if __name__ == "__main__":
    test_logging()
