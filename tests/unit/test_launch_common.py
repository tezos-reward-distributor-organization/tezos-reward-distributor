import argparse
import pytest
import io
import sys

from src.launch_common import print_banner


def test_print_banner():
    capturedOutput = io.StringIO()
    sys.stdout = capturedOutput
    print_banner("test", "test script")
    sys.stdout = sys.__stdout__
    assert (
        "TRD Organization: Copyright 2021, see contributors.csv"
        in capturedOutput.getvalue()
    )
    assert "huseyinabanox@gmail.com" in capturedOutput.getvalue()
    assert (
        "Tezos Reward Distributor (TRD)test script is Starting"
        in capturedOutput.getvalue()
    )
